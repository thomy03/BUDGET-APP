#!/usr/bin/env python3
"""
ML Inference API pour Budget Famille Phase 2
API temps réel (<500ms) pour toutes les fonctionnalités ML
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import hashlib
import time
import logging
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import sqlite3
import pandas as pd

# Imports des modules ML
from ml_rule_engine import TransactionRuleEngine, RuleResult
from ml_anomaly_detector import TransactionAnomalyDetector, AnomalyResult, DuplicateGroup
from ml_budget_predictor import BudgetIntelligenceSystem, BudgetPrediction, BudgetAlert, SmartRecommendation
from ml_feature_engineering import TransactionFeatureExtractor

logger = logging.getLogger(__name__)

# === PYDANTIC MODELS ===

class TransactionInput(BaseModel):
    label: str = Field(..., description="Label de la transaction")
    amount: float = Field(..., description="Montant de la transaction")
    account_label: str = Field(default="", description="Nom du compte")
    date_op: Optional[str] = Field(default=None, description="Date de la transaction (YYYY-MM-DD)")
    category: Optional[str] = Field(default="", description="Catégorie actuelle (si connue)")

class CategoryPrediction(BaseModel):
    category: str
    confidence: float
    explanation: str
    rule_id: Optional[str] = None
    fallback_used: bool = False

class AnomalyDetectionResult(BaseModel):
    is_anomaly: bool
    anomalies: List[Dict]
    risk_score: float
    explanation: str

class BudgetAnalysisRequest(BaseModel):
    current_date: str  # YYYY-MM-DD
    current_spending: Dict[str, float]  # category -> amount

class BudgetAnalysisResponse(BaseModel):
    predictions: List[Dict]
    alerts: List[Dict] 
    recommendations: List[Dict]
    summary: Dict

class BatchCategorizeRequest(BaseModel):
    transactions: List[TransactionInput]
    use_cache: bool = True

# === ML MODELS MANAGER ===

class MLModelsManager:
    """Gestionnaire centralisé des modèles ML avec cache et optimisations"""
    
    def __init__(self, db_path: str = "budget.db"):
        self.db_path = db_path
        self.redis_client = None
        
        # Modèles ML
        self.rule_engine = None
        self.anomaly_detector = None
        self.budget_system = None
        self.feature_extractor = None
        
        # Cache et métriques
        self.cache_stats = {'hits': 0, 'misses': 0}
        self.performance_metrics = []
        
        # État des modèles
        self.models_loaded = False
        self.last_training_time = None
    
    async def initialize(self, redis_url: str = "redis://localhost:6379"):
        """Initialise les modèles et la connexion Redis"""
        try:
            # Connexion Redis pour le cache
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis unavailable, using memory cache: {e}")
            self.redis_client = None
        
        # Chargement des modèles
        await self.load_models()
    
    async def load_models(self):
        """Charge et entraîne tous les modèles ML"""
        start_time = time.time()
        
        try:
            # Chargement des données d'entraînement
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query('SELECT * FROM transactions', conn)
            conn.close()
            
            if len(df) == 0:
                logger.warning("No training data available")
                return
            
            # 1. Rule Engine (rapide, pas d'entraînement nécessaire)
            self.rule_engine = TransactionRuleEngine()
            
            # 2. Feature Extractor
            self.feature_extractor = TransactionFeatureExtractor()
            
            # 3. Anomaly Detector (entraînement sur historique)
            self.anomaly_detector = TransactionAnomalyDetector()
            if len(df) >= 50:  # Minimum pour entraînement fiable
                self.anomaly_detector.fit(df)
            
            # 4. Budget Intelligence System
            self.budget_system = BudgetIntelligenceSystem()
            if len(df) >= 30:  # Minimum pour prédictions
                # Configuration budgets par défaut basée sur les données
                default_budgets = self._calculate_default_budgets(df)
                self.budget_system.fit(df, default_budgets)
            
            self.models_loaded = True
            self.last_training_time = datetime.now()
            
            training_time = time.time() - start_time
            logger.info(f"Models loaded successfully in {training_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self.models_loaded = False
    
    def _calculate_default_budgets(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcule les budgets par défaut basés sur l'historique"""
        expenses_df = df[df['is_expense'] == 1]
        
        # Calcul des budgets mensuels par catégorie (moyenne + 15%)
        monthly_spending = expenses_df.groupby(['month', 'category'])['amount'].sum().abs()
        avg_monthly = monthly_spending.groupby('category').mean()
        
        default_budgets = {}
        for category, avg_amount in avg_monthly.items():
            if pd.notna(category) and category != '':
                default_budgets[category] = avg_amount * 1.15  # +15% marge
        
        return default_budgets
    
    async def get_cache_key(self, data: dict) -> str:
        """Génère une clé de cache basée sur les données"""
        # Hash stable des données importantes
        cache_data = {k: v for k, v in data.items() if k in ['label', 'amount', 'account_label']}
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    async def get_from_cache(self, cache_key: str) -> Optional[dict]:
        """Récupère une valeur du cache"""
        if not self.redis_client:
            return None
        
        try:
            cached_value = await self.redis_client.get(cache_key)
            if cached_value:
                self.cache_stats['hits'] += 1
                return json.loads(cached_value)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        self.cache_stats['misses'] += 1
        return None
    
    async def set_cache(self, cache_key: str, value: dict, ttl: int = 3600):
        """Sauvegarde une valeur en cache"""
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(cache_key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

# Instance globale du gestionnaire
ml_manager = MLModelsManager()

# === API ENDPOINTS ===

app = FastAPI(
    title="Budget Famille ML API",
    description="API d'inférence ML pour catégorisation et intelligence budgétaire",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    await ml_manager.initialize()

@app.get("/health")
async def health_check():
    """Check de santé de l'API"""
    return {
        "status": "healthy",
        "models_loaded": ml_manager.models_loaded,
        "last_training": ml_manager.last_training_time.isoformat() if ml_manager.last_training_time else None,
        "cache_stats": ml_manager.cache_stats
    }

@app.post("/ml/categorize", response_model=CategoryPrediction)
async def categorize_transaction(transaction: TransactionInput):
    """
    Catégorise une transaction en temps réel (<500ms)
    Utilise Rule Engine + ML avec cache intelligent
    """
    start_time = time.time()
    
    if not ml_manager.models_loaded:
        raise HTTPException(status_code=503, detail="ML models not ready")
    
    # Vérification du cache
    cache_key = f"categorize:{await ml_manager.get_cache_key(transaction.dict())}"
    cached_result = await ml_manager.get_from_cache(cache_key)
    
    if cached_result:
        cached_result['processing_time_ms'] = (time.time() - start_time) * 1000
        return CategoryPrediction(**cached_result)
    
    try:
        # 1. Rule Engine (priorité haute, très rapide)
        rule_result = ml_manager.rule_engine.categorize(
            transaction.label, 
            transaction.amount, 
            transaction.account_label
        )
        
        if rule_result and rule_result.confidence > 0.85:
            # Confiance élevée, on utilise la règle
            result = CategoryPrediction(
                category=rule_result.category,
                confidence=rule_result.confidence,
                explanation=rule_result.explanation,
                rule_id=rule_result.rule_id,
                fallback_used=False
            )
        else:
            # Fallback: catégorie par défaut avec explication
            fallback_category = "Non catégorisé"
            confidence = 0.5
            explanation = "Aucune règle correspondante trouvée"
            
            # Amélioration du fallback basée sur des patterns simples
            label_upper = transaction.label.upper()
            if any(word in label_upper for word in ['CARTE', 'CB*']):
                if any(word in label_upper for word in ['TOTAL', 'SHELL', 'ESSO']):
                    fallback_category = "Carburant"
                    confidence = 0.7
                    explanation = "Détection pattern station-service"
                elif any(word in label_upper for word in ['LECLERC', 'CARREFOUR', 'MONOPRIX']):
                    fallback_category = "Alimentation" 
                    confidence = 0.7
                    explanation = "Détection pattern grande surface"
            
            result = CategoryPrediction(
                category=fallback_category,
                confidence=confidence,
                explanation=explanation,
                rule_id=rule_result.rule_id if rule_result else None,
                fallback_used=True
            )
        
        # Mise en cache
        processing_time = (time.time() - start_time) * 1000
        cache_value = result.dict()
        cache_value['processing_time_ms'] = processing_time
        
        await ml_manager.set_cache(cache_key, cache_value)
        
        # Log de performance
        if processing_time > 200:  # Log si > 200ms
            logger.warning(f"Slow categorization: {processing_time:.1f}ms for '{transaction.label[:30]}...'")
        
        return result
        
    except Exception as e:
        logger.error(f"Categorization error: {e}")
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")

@app.post("/ml/categorize/batch")
async def categorize_batch(request: BatchCategorizeRequest):
    """
    Catégorisation en batch avec optimisations
    """
    start_time = time.time()
    
    if not ml_manager.models_loaded:
        raise HTTPException(status_code=503, detail="ML models not ready")
    
    results = []
    cache_hits = 0
    
    try:
        for transaction in request.transactions:
            # Cache check si demandé
            if request.use_cache:
                cache_key = f"categorize:{await ml_manager.get_cache_key(transaction.dict())}"
                cached = await ml_manager.get_from_cache(cache_key)
                if cached:
                    results.append(CategoryPrediction(**cached))
                    cache_hits += 1
                    continue
            
            # Catégorisation via l'endpoint principal (réutilise la logique)
            result = await categorize_transaction(transaction)
            results.append(result)
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "results": results,
            "processing_time_ms": processing_time,
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hits / len(request.transactions) if request.transactions else 0
        }
        
    except Exception as e:
        logger.error(f"Batch categorization error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch categorization failed: {str(e)}")

@app.post("/ml/anomaly/detect", response_model=AnomalyDetectionResult) 
async def detect_anomalies(transaction: TransactionInput):
    """
    Détecte les anomalies pour une transaction
    """
    start_time = time.time()
    
    if not ml_manager.models_loaded or not ml_manager.anomaly_detector:
        raise HTTPException(status_code=503, detail="Anomaly detection not available")
    
    try:
        # Conversion en format dict pour le détecteur
        tx_dict = {
            'id': f'api_{int(time.time())}',
            'label': transaction.label,
            'amount': transaction.amount,
            'account_label': transaction.account_label,
            'date_op': transaction.date_op or datetime.now().strftime('%Y-%m-%d'),
            'category': transaction.category
        }
        
        # Détection d'anomalies
        anomalies = ml_manager.anomaly_detector.analyze_transaction(tx_dict)
        
        # Calcul du score de risque global
        risk_score = 0.0
        if anomalies:
            risk_score = min(1.0, sum(a.severity * a.confidence for a in anomalies) / len(anomalies))
        
        # Génération de l'explication
        if not anomalies:
            explanation = "Transaction normale, aucune anomalie détectée"
        else:
            explanation = f"Détecté {len(anomalies)} anomalie(s): " + "; ".join(a.explanation for a in anomalies[:2])
        
        processing_time = (time.time() - start_time) * 1000
        
        return AnomalyDetectionResult(
            is_anomaly=len(anomalies) > 0,
            anomalies=[{
                'type': a.anomaly_type,
                'severity': a.severity,
                'explanation': a.explanation,
                'confidence': a.confidence
            } for a in anomalies],
            risk_score=risk_score,
            explanation=explanation
        )
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")

@app.post("/ml/budget/analyze", response_model=BudgetAnalysisResponse)
async def analyze_budget(request: BudgetAnalysisRequest):
    """
    Analyse budgétaire complète avec prédictions et recommandations
    """
    start_time = time.time()
    
    if not ml_manager.models_loaded or not ml_manager.budget_system:
        raise HTTPException(status_code=503, detail="Budget intelligence not available")
    
    try:
        current_date = datetime.fromisoformat(request.current_date)
        
        # 1. Prédictions de fin de mois
        predictions = ml_manager.budget_system.predict_month_end(
            current_date, 
            request.current_spending
        )
        
        # 2. Génération d'alertes
        alerts = ml_manager.budget_system.generate_alerts(
            current_date, 
            request.current_spending
        )
        
        # 3. Recommandations intelligentes
        recommendations = ml_manager.budget_system.generate_smart_recommendations(
            request.current_spending
        )
        
        # 4. Résumé global
        total_current = sum(request.current_spending.values())
        total_predicted = sum(p.predicted_month_end for p in predictions)
        high_risk_alerts = sum(1 for a in alerts if a.severity == 'high')
        
        summary = {
            'total_spent_current': total_current,
            'total_predicted_month_end': total_predicted,
            'categories_analyzed': len(predictions),
            'alerts_count': len(alerts),
            'high_risk_alerts': high_risk_alerts,
            'recommendations_count': len(recommendations),
            'analysis_date': request.current_date
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return BudgetAnalysisResponse(
            predictions=[{
                'category': p.category,
                'current_spent': p.current_spent,
                'predicted_month_end': p.predicted_month_end,
                'monthly_average': p.monthly_average,
                'trend_direction': p.trend_direction,
                'confidence': p.confidence,
                'recommendation': p.recommendation
            } for p in predictions],
            
            alerts=[{
                'alert_type': a.alert_type,
                'category': a.category,
                'severity': a.severity,
                'message': a.message,
                'current_amount': a.current_amount,
                'predicted_amount': a.predicted_amount,
                'threshold': a.threshold,
                'days_remaining': a.days_remaining
            } for a in alerts],
            
            recommendations=[{
                'recommendation_type': r.recommendation_type,
                'category': r.category,
                'current_budget': r.current_budget,
                'suggested_budget': r.suggested_budget,
                'reasoning': r.reasoning,
                'impact_estimate': r.impact_estimate,
                'confidence': r.confidence
            } for r in recommendations],
            
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Budget analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Budget analysis failed: {str(e)}")

@app.get("/ml/stats")
async def get_ml_stats():
    """Statistiques et métriques du système ML"""
    return {
        "models_status": {
            "rule_engine_loaded": ml_manager.rule_engine is not None,
            "anomaly_detector_loaded": ml_manager.anomaly_detector is not None,
            "budget_system_loaded": ml_manager.budget_system is not None,
            "feature_extractor_loaded": ml_manager.feature_extractor is not None
        },
        "cache_statistics": ml_manager.cache_stats,
        "cache_hit_rate": (
            ml_manager.cache_stats['hits'] / 
            (ml_manager.cache_stats['hits'] + ml_manager.cache_stats['misses'])
        ) if (ml_manager.cache_stats['hits'] + ml_manager.cache_stats['misses']) > 0 else 0,
        "last_training": ml_manager.last_training_time.isoformat() if ml_manager.last_training_time else None
    }

@app.post("/ml/retrain")
async def retrain_models(background_tasks: BackgroundTasks):
    """Relance l'entraînement des modèles en arrière-plan"""
    background_tasks.add_task(ml_manager.load_models)
    return {"message": "Model retraining initiated in background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ml_inference_api:app",
        host="0.0.0.0",
        port=8001,  # Port différent du backend principal
        reload=True
    )