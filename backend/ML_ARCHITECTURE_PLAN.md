# Plan Technique ML - Budget Famille Phase 2
## Architecture Intelligence Artificielle

**Date**: 10/08/2025  
**Version**: 1.0  
**Objectif**: Déploiement de fonctionnalités IA pour categorisation automatique et détection intelligente

---

## 1. ANALYSE DE L'ÉTAT ACTUEL

### 1.1 Diagnostic des Données
- **Volume**: 263 transactions analysées
- **Période**: 2024-2026 (données de test)
- **Qualité des labels**: 221 labels uniques sur 263 transactions (84% de diversité)
- **PROBLÈME CRITIQUE**: Seulement 0.8% des transactions sont taguées (2/263)
- **Catégories manquantes**: 17.9% (47 transactions)

### 1.2 Patterns Identifiés
**Méthodes de paiement détectées**:
- CARTE: 104 occurrences (39.5%)
- Virements (VIR): 20 occurrences
- Prélèvements (PRLV): 14 occurrences

**Marchands fréquents**:
- TOTAL: 14 occurrences
- AMAZON: 15 occurrences  
- LECLERC: 12 occurrences
- TEMU: 16 occurrences

### 1.3 Défis Techniques Identifiés
1. **Données d'entraînement insuffisantes** (tags < 1%)
2. **Hétérogénéité des formats** de labels bancaires
3. **Catégorisation incomplète** (17.9% manquantes)
4. **Performance cible agressive**: >85% précision, <500ms

---

## 2. ARCHITECTURE ML PROPOSÉE

### 2.1 Pipeline de Catégorisation Automatique

#### Architecture Hybride: Règles + ML
```
Input Transaction
       ↓
[1] Rule-Based Engine ────────── Fallback Rules
       ↓ (if no match)              ↑
[2] Feature Engineering           ↓
       ↓                    [4] Confidence < 0.85
[3] ML Classification Model       ↓
       ↓                    Manual Review
[4] Confidence Scoring           Queue
       ↓ (if > 0.85)
   Auto-Tag Applied
```

#### 2.1.1 Rule-Based Engine (Phase 2a)
**Objectif**: Couvrir 70% des cas avec des règles métier

**Règles prioritaires**:
```python
MERCHANT_RULES = {
    'TOTAL|SHELL|ESSO': 'Carburant',
    'AMAZON|AMZN': 'Livres, CD/DVD, bijoux, jouets…',
    'LECLERC|MONOPRIX|CARREFOUR': 'Alimentation',
    'DELIVEROO|UBER EATS': 'Restaurants, bars, discothèques…',
    'PHARMACIE|PHIE': 'Pharmacie et laboratoire',
    'VIR.*SALAIRE|SALAIRE': 'Revenus',
    'PRLV.*EDF|ENEDIS': 'Énergie'
}

AMOUNT_RULES = {
    'amount > 1000 AND merchant LIKE "%SALAIRE%"': 'Revenus',
    'amount < 0 AND amount > -5 AND "PARKING|FLOW"': 'Parking',
    'amount < -50 AND "HOTEL|CAMPING"': 'Hébergement'
}
```

#### 2.1.2 ML Classification Model (Phase 2b)
**Architecture**: Lightweight Random Forest + TF-IDF

**Features Engineering**:
1. **Textual Features** (TF-IDF sur labels nettoyés)
   - N-grams: (1,2) 
   - Max features: 200
   - Min_df: 2, Max_df: 0.8

2. **Numerical Features**
   - amount_abs, amount_log, amount_rounded
   - day_of_week, month, is_weekend
   - label_length, word_count

3. **Categorical Features**  
   - payment_method (CARD/TRANSFER/DIRECT_DEBIT)
   - merchant_name (extrait via regex)
   - account_type (joint/individual)

**Model Selection**:
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('features', FeatureUnion([
        ('tfidf', TfidfVectorizer(max_features=200, ngram_range=(1,2))),
        ('numerical', StandardScaler()),
        ('categorical', OneHotEncoder(handle_unknown='ignore'))
    ])),
    ('classifier', RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42
    ))
])
```

### 2.2 Détection d'Anomalies et Doublons

#### 2.2.1 Détection de Doublons
**Algorithme**: Fuzzy String Matching + Time Window

```python
def detect_duplicates(transactions):
    duplicates = []
    for t1 in transactions:
        for t2 in transactions:
            if (
                abs(t1.amount - t2.amount) < 0.01 AND
                fuzz.ratio(t1.label, t2.label) > 85 AND
                abs((t1.date - t2.date).days) <= 3
            ):
                duplicates.append((t1, t2))
    return duplicates
```

#### 2.2.2 Détection d'Anomalies
**Méthode**: Isolation Forest + Statistical Outliers

**Features pour anomalies**:
- Montant par rapport à l'historique du marchand
- Fréquence d'achat inhabituelle
- Nouveau marchand jamais vu
- Montant inhabituel pour la catégorie

```python
from sklearn.ensemble import IsolationForest

anomaly_detector = IsolationForest(
    contamination=0.05,  # 5% max false positives
    random_state=42
)
```

### 2.3 Suggestions de Budget Intelligent

#### Architecture Prédictive
**Modèle**: Linear Regression + Historical Patterns

**Fonctionnalités**:
1. **Prédiction mensuelle** par catégorie basée sur:
   - Moyenne mobile 3-6 mois
   - Tendances saisonnières
   - Événements récurrents

2. **Recommandations personnalisées**:
   - "Votre budget courses augmente de 15% vs mois dernier"
   - "Provision vacances: +2% recommandé pour atteindre objectif"

### 2.4 Alertes Prédictives Fin de Mois

**Logique**: Extrapolation linéaire + règles métier

```python
def predict_month_end(current_expenses, days_remaining):
    daily_avg = current_expenses / (30 - days_remaining)
    predicted_total = current_expenses + (daily_avg * days_remaining)
    
    # Ajustement week-end / jours féries
    weekend_factor = count_weekends(days_remaining) * 0.8
    return predicted_total * weekend_factor
```

---

## 3. API D'INFÉRENCE TEMPS RÉEL

### 3.1 Architecture API
**Framework**: FastAPI avec cache Redis

```python
@app.post("/ml/categorize")
async def categorize_transaction(transaction: TransactionSchema):
    # Cache check
    cache_key = f"category:{hash(transaction.label + str(transaction.amount))}"
    cached = await redis_client.get(cache_key)
    
    if cached:
        return cached
    
    # Rule engine (< 50ms)
    rule_result = rule_engine.match(transaction)
    if rule_result.confidence > 0.9:
        await redis_client.setex(cache_key, 3600, rule_result)
        return rule_result
    
    # ML prediction (< 300ms)
    ml_result = ml_model.predict(transaction)
    result = combine_predictions(rule_result, ml_result)
    
    await redis_client.setex(cache_key, 3600, result)
    return result
```

### 3.2 Performance Targets
- **Latence cible**: < 500ms (95e percentile)
- **Throughput**: 100 req/s
- **Cache hit rate**: > 80%

**Optimisations**:
1. **Model caching**: Modèle chargé en mémoire
2. **Feature caching**: Pre-calcul des features TF-IDF communes
3. **Batch processing**: Groupement des predictions similaires

---

## 4. MÉTRIQUES DE PERFORMANCE

### 4.1 Métriques Business
- **Precision globale**: > 85% (objectif roadmap)
- **Recall par catégorie**: > 80% pour top 10 catégories
- **Coverage automatique**: > 90% des transactions auto-taguées
- **False positive rate**: < 5% pour détection anomalies

### 4.2 Métriques Techniques  
- **Latence API**: P95 < 500ms, P99 < 1000ms
- **Availability**: 99.9% SLA
- **Model freshness**: Re-entraînement hebdomadaire
- **Feature drift detection**: Alerte si >10% décalage

### 4.3 A/B Testing Framework
**Configuration**:
- 20% traffic sur nouveau modèle ML
- 80% sur règles + ancien modèle
- Métriques tracking automatique
- Rollback automatique si precision < 80%

---

## 5. PLAN D'IMPLÉMENTATION

### Phase 2a: Fondations (2 semaines)
**Semaine 1-2**:
- [ ] **Rule Engine** avec 50 règles prioritaires
- [ ] **Feature Engineering pipeline** optimisé  
- [ ] **API endpoints** pour inférence temps réel
- [ ] **Métriques monitoring** dashboards

**Delivrables**:
- Coverage: 70% transactions auto-catégorisées  
- Precision rules: > 90%
- API latence: < 300ms

### Phase 2b: ML Pipeline (3 semaines)
**Semaine 3-4**:
- [ ] **ML Model training** avec données augmentées
- [ ] **Model evaluation** framework 
- [ ] **A/B testing** infrastructure

**Semaine 5**:
- [ ] **Anomaly detection** système
- [ ] **Duplicate detection** pipeline
- [ ] **Integration tests** complets

**Delivrables**:
- Precision globale: > 85%
- False positive anomalies: < 5%
- Coverage totale: > 90%

### Phase 2c: Intelligence Avancée (2 semaines)
**Semaine 6-7**:
- [ ] **Budget predictions** algorithmes
- [ ] **Alertes prédictives** engine
- [ ] **Model monitoring** automatique

**Delivrables**:
- Prédictions mensuelles fonctionnelles
- Alertes en temps réel 
- Monitoring production complet

---

## 6. RISQUES ET MITIGATION

### 6.1 Risques Techniques
**Risque**: Données d'entraînement insuffisantes (0.8% taguées)
**Mitigation**: 
- Bootstrap avec règles métier (Phase 2a)
- Data augmentation via règles
- Active learning pour enrichir progressivement

**Risque**: Dérive des modèles bancaires
**Mitigation**:
- Monitoring des patterns de labels
- Re-entraînement automatique hebdomadaire
- Fallback rules robustes

### 6.2 Risques Métier  
**Risque**: Performance < 85% precision
**Mitigation**:
- Architecture hybride Rules + ML
- A/B testing progressif
- Rollback automatique configuré

**Risque**: Latence > 500ms
**Mitigation**:
- Cache multi-niveaux
- Model optimization (quantization)
- Timeout graceful degradation

---

## 7. INFRASTRUCTURE ET DÉPLOIEMENT

### 7.1 Architecture Technique
```
Frontend (Next.js) 
       ↓
API Gateway (FastAPI)
       ↓
ML Service (Python) ← Redis Cache
       ↓
Model Store (S3/Local) + Database (SQLite/PostgreSQL)
```

### 7.2 Deployment Strategy
**Environment stages**:
1. **Local Dev**: SQLite + modèles locaux
2. **Staging**: PostgreSQL + Redis + monitoring
3. **Production**: Container orchestration + monitoring complet

**Feature Flags**:
```python
ML_FEATURES = {
    'auto_categorization': True,
    'anomaly_detection': False,  # Rollout progressif
    'budget_predictions': False,
    'advanced_alerts': False
}
```

---

## 8. NEXT STEPS IMMÉDIATS

### Actions Prioritaires (Semaine 1)
1. **Créer 100 règles métier** basées sur l'analyse des données
2. **Implémenter Rule Engine** avec tests unitaires
3. **Optimiser Feature Engineering** pipeline existant
4. **Créer API inference** endpoints
5. **Setup monitoring** infrastructure

### Préparation Phase 2b
1. **Data Collection Strategy**: Encourager utilisateurs à taguer
2. **Model Training Pipeline**: Automatisation complète  
3. **Evaluation Framework**: Métriques business + techniques

---

## CONCLUSION

Cette architecture ML hybride (Règles + ML) permet d'atteindre les objectifs Phase 2:
- ✅ **Precision > 85%** via combinaison intelligente  
- ✅ **Latence < 500ms** via optimisations multicouches
- ✅ **Robustesse** grâce aux fallback rules
- ✅ **Scalabilité** avec infrastructure containerisée

Le déploiement progressif (2a → 2b → 2c) minimise les risques tout en maximisant la valeur business livrée rapidement.