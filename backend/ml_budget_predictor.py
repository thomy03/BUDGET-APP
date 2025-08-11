#!/usr/bin/env python3
"""
ML Budget Intelligence System pour Budget Famille
Suggestions de budget intelligent et alertes prédictives fin de mois
"""

import numpy as np
import pandas as pd
import sqlite3
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

@dataclass
class BudgetPrediction:
    category: str
    current_spent: float
    predicted_month_end: float
    monthly_average: float
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    confidence: float
    recommendation: str

@dataclass
class BudgetAlert:
    alert_type: str  # 'overspend_risk', 'unusual_spike', 'category_trend'
    category: str
    severity: str    # 'low', 'medium', 'high'
    message: str
    current_amount: float
    predicted_amount: float
    threshold: float
    days_remaining: int

@dataclass
class SmartRecommendation:
    recommendation_type: str  # 'budget_increase', 'spending_optimization', 'savings_opportunity'
    category: str
    current_budget: float
    suggested_budget: float
    reasoning: str
    impact_estimate: str
    confidence: float

class BudgetIntelligenceSystem:
    """
    Système d'intelligence budgétaire avec:
    - Prédictions de fin de mois par catégorie
    - Détection de trends et anomalies de dépenses
    - Recommandations personnalisées d'optimisation
    - Alertes prédictives intelligentes
    """
    
    def __init__(self):
        self.category_models = {}  # Modèles de prédiction par catégorie
        self.historical_data = None
        self.monthly_budgets = {}  # Budgets configurés par catégorie
        
        # Paramètres configurables
        self.config = {
            'min_historical_months': 3,     # Minimum de mois pour prédiction fiable
            'trend_sensitivity': 0.15,      # Seuil pour détecter une tendance (15%)
            'overspend_threshold': 1.1,     # Seuil d'alerte dépassement (110%)
            'savings_opportunity_threshold': 0.8,  # Seuil opportunité d'économies (80%)
            'confidence_threshold': 0.7,    # Confiance minimale pour recommandations
        }
    
    def fit(self, transactions_df: pd.DataFrame, budgets_config: Dict = None):
        """
        Entraîne le système sur l'historique des transactions
        """
        logger.info(f"Training budget intelligence on {len(transactions_df)} transactions")
        
        # Préparation des données historiques
        self.historical_data = self._prepare_historical_data(transactions_df)
        
        if budgets_config:
            self.monthly_budgets = budgets_config
        
        # Entraînement des modèles par catégorie
        self._train_category_models()
        
        logger.info(f"Trained models for {len(self.category_models)} categories")
    
    def _prepare_historical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prépare les données historiques agrégées par mois/catégorie"""
        df['date_op'] = pd.to_datetime(df['date_op'])
        df['year_month'] = df['date_op'].dt.to_period('M')
        
        # Agrégation par mois/catégorie (seulement les dépenses)
        expenses_df = df[df['is_expense'] == 1].copy()
        
        monthly_summary = expenses_df.groupby(['year_month', 'category']).agg({
            'amount': ['sum', 'count', 'mean'],
            'date_op': ['min', 'max']
        }).reset_index()
        
        # Aplatir les colonnes multi-niveau
        monthly_summary.columns = ['year_month', 'category', 'total_spent', 'transaction_count', 
                                 'avg_transaction', 'month_start', 'month_end']
        
        # Convertir les montants en positif
        monthly_summary['total_spent'] = monthly_summary['total_spent'].abs()
        
        # Ajouter des features temporelles
        monthly_summary['month_numeric'] = monthly_summary['year_month'].dt.month
        monthly_summary['is_holiday_month'] = monthly_summary['month_numeric'].isin([7, 8, 12]).astype(int)
        
        return monthly_summary
    
    def _train_category_models(self):
        """Entraîne les modèles de prédiction par catégorie"""
        categories = self.historical_data['category'].unique()
        
        for category in categories:
            if pd.isna(category) or category == '':
                continue
                
            category_data = self.historical_data[
                self.historical_data['category'] == category
            ].copy()
            
            if len(category_data) < self.config['min_historical_months']:
                logger.debug(f"Insufficient data for category {category}: {len(category_data)} months")
                continue
            
            # Préparation des features
            category_data['month_index'] = range(len(category_data))
            category_data.sort_values('year_month', inplace=True)
            
            # Features pour le modèle
            X = category_data[['month_index', 'month_numeric', 'is_holiday_month', 'transaction_count']].values
            y = category_data['total_spent'].values
            
            # Modèle avec features polynomiales pour capturer les tendances
            poly_features = PolynomialFeatures(degree=2, interaction_only=True)
            X_poly = poly_features.fit_transform(X)
            
            model = LinearRegression()
            model.fit(X_poly, y)
            
            # Calcul des métriques de performance
            predictions = model.predict(X_poly)
            mse = np.mean((y - predictions) ** 2)
            r2_score = model.score(X_poly, y)
            
            self.category_models[category] = {
                'model': model,
                'poly_features': poly_features,
                'monthly_average': np.mean(y),
                'monthly_std': np.std(y),
                'trend': self._calculate_trend(y),
                'mse': mse,
                'r2_score': r2_score,
                'data_points': len(y),
                'last_values': y[-3:].tolist() if len(y) >= 3 else y.tolist()
            }
        
        logger.info(f"Successfully trained {len(self.category_models)} category models")
    
    def _calculate_trend(self, values: np.ndarray) -> str:
        """Calcule la tendance (croissante/décroissante/stable)"""
        if len(values) < 2:
            return 'stable'
        
        # Régression linéaire simple pour détecter la tendance
        x = np.arange(len(values))
        coefficients = np.polyfit(x, values, 1)
        slope = coefficients[0]
        
        # Calcul du pourcentage de changement
        avg_value = np.mean(values)
        slope_percentage = (slope / avg_value) if avg_value != 0 else 0
        
        if abs(slope_percentage) < self.config['trend_sensitivity']:
            return 'stable'
        elif slope_percentage > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def predict_month_end(self, current_date: datetime, 
                         current_spending: Dict[str, float]) -> List[BudgetPrediction]:
        """
        Prédit les dépenses de fin de mois pour chaque catégorie
        """
        predictions = []
        
        # Calcul des jours restants dans le mois
        last_day_of_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        days_remaining = (last_day_of_month - current_date).days
        days_in_month = last_day_of_month.day
        progress_ratio = (days_in_month - days_remaining) / days_in_month
        
        for category, current_spent in current_spending.items():
            if category not in self.category_models:
                # Extrapolation simple pour catégories sans modèle
                if progress_ratio > 0:
                    predicted_total = current_spent / progress_ratio
                else:
                    predicted_total = current_spent
                
                predictions.append(BudgetPrediction(
                    category=category,
                    current_spent=current_spent,
                    predicted_month_end=predicted_total,
                    monthly_average=current_spent,
                    trend_direction='unknown',
                    confidence=0.5,
                    recommendation=f"Données insuffisantes pour {category}"
                ))
                continue
            
            model_info = self.category_models[category]
            monthly_avg = model_info['monthly_average']
            
            # Prédiction basée sur le modèle + extrapolation du spending actuel
            model_prediction = self._get_model_prediction(category, current_date)
            
            # Combinaison: 70% extrapolation linéaire + 30% modèle historique
            if progress_ratio > 0:
                linear_prediction = current_spent / progress_ratio
            else:
                linear_prediction = monthly_avg
            
            combined_prediction = 0.7 * linear_prediction + 0.3 * model_prediction
            
            # Calcul de la confiance basée sur la performance du modèle
            confidence = min(0.95, 0.5 + model_info['r2_score'] * 0.4)
            if progress_ratio < 0.3:  # Début de mois, moins fiable
                confidence *= 0.8
            
            # Génération de la recommandation
            recommendation = self._generate_category_recommendation(
                category, current_spent, combined_prediction, monthly_avg, 
                model_info['trend'], progress_ratio
            )
            
            predictions.append(BudgetPrediction(
                category=category,
                current_spent=current_spent,
                predicted_month_end=combined_prediction,
                monthly_average=monthly_avg,
                trend_direction=model_info['trend'],
                confidence=confidence,
                recommendation=recommendation
            ))
        
        return sorted(predictions, key=lambda x: x.predicted_month_end, reverse=True)
    
    def _get_model_prediction(self, category: str, target_date: datetime) -> float:
        """Obtient la prédiction du modèle ML pour une catégorie"""
        if category not in self.category_models:
            return 0.0
        
        model_info = self.category_models[category]
        model = model_info['model']
        poly_features = model_info['poly_features']
        
        # Préparation des features pour la prédiction
        month_index = len(model_info['last_values'])  # Index du prochain mois
        month_numeric = target_date.month
        is_holiday_month = 1 if month_numeric in [7, 8, 12] else 0
        avg_transaction_count = 10  # Valeur par défaut
        
        X_new = np.array([[month_index, month_numeric, is_holiday_month, avg_transaction_count]])
        X_new_poly = poly_features.transform(X_new)
        
        prediction = model.predict(X_new_poly)[0]
        return max(0, prediction)  # Pas de dépenses négatives
    
    def _generate_category_recommendation(self, category: str, current_spent: float, 
                                        predicted_total: float, monthly_avg: float,
                                        trend: str, progress_ratio: float) -> str:
        """Génère une recommandation personnalisée pour une catégorie"""
        
        # Template de base selon la tendance
        if predicted_total > monthly_avg * 1.2:
            base_msg = f"Attention: dépassement prévu de {((predicted_total/monthly_avg-1)*100):.0f}% vs moyenne"
        elif predicted_total < monthly_avg * 0.8:
            base_msg = f"Économies possibles: {((1-predicted_total/monthly_avg)*100):.0f}% sous la moyenne"
        else:
            base_msg = "Dépenses dans la normale"
        
        # Ajustement selon la tendance
        if trend == 'increasing':
            trend_msg = " (tendance croissante détectée)"
        elif trend == 'decreasing':
            trend_msg = " (tendance décroissante)"
        else:
            trend_msg = ""
        
        # Conseil actionnable
        if progress_ratio < 0.5 and predicted_total > monthly_avg * 1.15:
            action_msg = " - Surveiller les prochaines dépenses"
        elif progress_ratio > 0.7 and current_spent < monthly_avg * 0.7:
            action_msg = " - Marge disponible pour cette catégorie"
        else:
            action_msg = ""
        
        return base_msg + trend_msg + action_msg
    
    def generate_alerts(self, current_date: datetime, 
                       current_spending: Dict[str, float]) -> List[BudgetAlert]:
        """
        Génère les alertes de dépassement et anomalies
        """
        alerts = []
        predictions = self.predict_month_end(current_date, current_spending)
        
        # Calcul des jours restants
        last_day = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        days_remaining = (last_day - current_date).days
        
        for prediction in predictions:
            category = prediction.category
            current = prediction.current_spent
            predicted = prediction.predicted_month_end
            avg = prediction.monthly_average
            
            # Alerte dépassement budgétaire
            budget_limit = self.monthly_budgets.get(category, avg * 1.1)  # 110% de la moyenne par défaut
            
            if predicted > budget_limit:
                severity = 'high' if predicted > budget_limit * 1.2 else 'medium'
                alerts.append(BudgetAlert(
                    alert_type='overspend_risk',
                    category=category,
                    severity=severity,
                    message=f"Risque de dépassement: {predicted:.0f}€ prévu vs budget {budget_limit:.0f}€",
                    current_amount=current,
                    predicted_amount=predicted,
                    threshold=budget_limit,
                    days_remaining=days_remaining
                ))
            
            # Alerte pic inhabituel
            if current > avg * 1.5 and days_remaining > 10:
                alerts.append(BudgetAlert(
                    alert_type='unusual_spike',
                    category=category,
                    severity='medium',
                    message=f"Pic de dépenses inhabituel: {current:.0f}€ vs moyenne {avg:.0f}€",
                    current_amount=current,
                    predicted_amount=predicted,
                    threshold=avg * 1.2,
                    days_remaining=days_remaining
                ))
            
            # Alerte tendance préoccupante
            if prediction.trend_direction == 'increasing' and predicted > avg * 1.3:
                alerts.append(BudgetAlert(
                    alert_type='category_trend',
                    category=category,
                    severity='low',
                    message=f"Tendance croissante confirmée: +{((predicted/avg-1)*100):.0f}% vs moyenne",
                    current_amount=current,
                    predicted_amount=predicted,
                    threshold=avg,
                    days_remaining=days_remaining
                ))
        
        # Tri par sévérité
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        alerts.sort(key=lambda x: severity_order.get(x.severity, 0), reverse=True)
        
        return alerts
    
    def generate_smart_recommendations(self, current_spending: Dict[str, float]) -> List[SmartRecommendation]:
        """
        Génère des recommandations intelligentes d'optimisation budgétaire
        """
        recommendations = []
        
        for category, current_spent in current_spending.items():
            if category not in self.category_models:
                continue
            
            model_info = self.category_models[category]
            monthly_avg = model_info['monthly_average']
            trend = model_info['trend']
            
            current_budget = self.monthly_budgets.get(category, monthly_avg * 1.1)
            
            # Recommandation d'augmentation de budget
            if trend == 'increasing' and monthly_avg > current_budget * 0.9:
                suggested_budget = monthly_avg * 1.15
                recommendations.append(SmartRecommendation(
                    recommendation_type='budget_increase',
                    category=category,
                    current_budget=current_budget,
                    suggested_budget=suggested_budget,
                    reasoning=f"Tendance croissante détectée (+{((monthly_avg/current_budget-1)*100):.0f}%)",
                    impact_estimate=f"+{suggested_budget-current_budget:.0f}€/mois",
                    confidence=model_info['r2_score']
                ))
            
            # Opportunité d'économies
            elif current_spent < monthly_avg * 0.8 and trend != 'increasing':
                potential_savings = current_budget - monthly_avg * 0.9
                recommendations.append(SmartRecommendation(
                    recommendation_type='savings_opportunity',
                    category=category,
                    current_budget=current_budget,
                    suggested_budget=monthly_avg * 0.9,
                    reasoning=f"Sous-consommation récurrente (-{((1-current_spent/monthly_avg)*100):.0f}%)",
                    impact_estimate=f"-{potential_savings:.0f}€/mois",
                    confidence=0.8
                ))
            
            # Optimisation de dépenses
            elif current_spent > monthly_avg * 1.2:
                recommendations.append(SmartRecommendation(
                    recommendation_type='spending_optimization',
                    category=category,
                    current_budget=current_budget,
                    suggested_budget=current_budget,
                    reasoning=f"Dépassement fréquent: réviser les habitudes de {category.lower()}",
                    impact_estimate="Potentiel d'économie significatif",
                    confidence=0.7
                ))
        
        # Garder seulement les recommandations avec confiance suffisante
        recommendations = [r for r in recommendations if r.confidence >= self.config['confidence_threshold']]
        
        return sorted(recommendations, key=lambda x: x.confidence, reverse=True)

def main():
    """Test du système d'intelligence budgétaire"""
    try:
        # Chargement des données
        conn = sqlite3.connect('budget.db')
        df = pd.read_sql_query('SELECT * FROM transactions', conn)
        conn.close()
        
        print("=== TEST BUDGET INTELLIGENCE SYSTEM ===")
        print(f"Loaded {len(df)} transactions")
        
        # Création et entraînement du système
        budget_system = BudgetIntelligenceSystem()
        
        # Configuration budgets exemple
        budgets_config = {
            'Alimentation': 400,
            'Restaurants, bars, discothèques…': 200,
            'Carburant': 150,
            'Livres, CD/DVD, bijoux, jouets…': 300
        }
        
        budget_system.fit(df, budgets_config)
        
        print(f"Trained models for {len(budget_system.category_models)} categories")
        
        # Simulation des dépenses actuelles (mi-mois)
        current_date = datetime(2025, 8, 15)
        current_spending = {
            'Alimentation': 180,
            'Restaurants, bars, discothèques…': 120,
            'Carburant': 65,
            'Livres, CD/DVD, bijoux, jouets…': 240
        }
        
        print("\\n--- Prédictions de fin de mois ---")
        predictions = budget_system.predict_month_end(current_date, current_spending)
        
        for pred in predictions[:5]:
            print(f"{pred.category}:")
            print(f"  Actuel: {pred.current_spent:.0f}€ -> Prévu: {pred.predicted_month_end:.0f}€")
            print(f"  Tendance: {pred.trend_direction} (confiance: {pred.confidence:.2f})")
            print(f"  Conseil: {pred.recommendation}")
            print()
        
        print("--- Alertes ---")
        alerts = budget_system.generate_alerts(current_date, current_spending)
        
        for alert in alerts:
            print(f"[{alert.severity.upper()}] {alert.category}: {alert.message}")
        
        print("\\n--- Recommandations intelligentes ---")
        recommendations = budget_system.generate_smart_recommendations(current_spending)
        
        for rec in recommendations:
            print(f"{rec.recommendation_type.upper()}: {rec.category}")
            print(f"  Budget: {rec.current_budget:.0f}€ -> {rec.suggested_budget:.0f}€")
            print(f"  Raison: {rec.reasoning}")
            print(f"  Impact: {rec.impact_estimate}")
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    main()