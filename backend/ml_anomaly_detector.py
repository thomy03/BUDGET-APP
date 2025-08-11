#!/usr/bin/env python3
"""
ML Anomaly Detection System pour Budget Famille
Détection d'anomalies et de doublons dans les transactions
"""

import numpy as np
import pandas as pd
import sqlite3
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import logging
from fuzzywuzzy import fuzz
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class AnomalyResult:
    transaction_id: str
    anomaly_type: str  # 'amount', 'frequency', 'merchant', 'duplicate'
    severity: float    # 0.0 to 1.0
    explanation: str
    reference_data: Dict
    confidence: float

@dataclass
class DuplicateGroup:
    transactions: List[Dict]
    similarity_score: float
    duplicate_type: str  # 'exact', 'fuzzy', 'temporal'
    explanation: str

class TransactionAnomalyDetector:
    """
    Détecteur d'anomalies avec approche multi-méthodes
    - Isolation Forest pour montants inhabituels
    - Analyse temporelle pour fréquences anormales  
    - Fuzzy matching pour détection de doublons
    - Règles métier pour nouveaux marchands
    """
    
    def __init__(self, contamination_rate: float = 0.05):
        self.contamination_rate = contamination_rate  # Max 5% false positives
        self.isolation_forest = None
        self.scaler = StandardScaler()
        
        # Historique pour détection d'anomalies contextuelles
        self.merchant_profiles = {}
        self.category_profiles = {}
        self.user_spending_patterns = {}
        
        # Seuils configurables
        self.thresholds = {
            'amount_zscore': 2.5,      # Z-score pour montants inhabituels
            'frequency_threshold': 3.0,  # Fréquence inhabituelle (x fois normale)
            'duplicate_similarity': 85,   # % similarité fuzzy pour doublons
            'duplicate_time_window': 3,   # Jours pour chercher des doublons
            'new_merchant_amount': 100,   # Montant seuil nouveau marchand
        }
    
    def fit(self, transactions_df: pd.DataFrame):
        """
        Entraîne les modèles sur l'historique des transactions
        """
        logger.info(f"Training anomaly detector on {len(transactions_df)} transactions")
        
        # Préparation des features pour Isolation Forest
        features_df = self._prepare_features(transactions_df)
        
        # Entraînement Isolation Forest
        self.isolation_forest = IsolationForest(
            contamination=self.contamination_rate,
            random_state=42,
            n_estimators=100
        )
        
        feature_matrix = self.scaler.fit_transform(features_df)
        self.isolation_forest.fit(feature_matrix)
        
        # Construction des profils historiques
        self._build_merchant_profiles(transactions_df)
        self._build_category_profiles(transactions_df)
        self._build_user_patterns(transactions_df)
        
        logger.info("Anomaly detector training completed")
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prépare les features pour l'Isolation Forest"""
        features = pd.DataFrame()
        
        # Features basiques
        features['amount_abs'] = np.abs(df['amount'])
        features['amount_log'] = np.log1p(features['amount_abs'])
        
        # Features temporelles
        df['date_op'] = pd.to_datetime(df['date_op'])
        features['day_of_week'] = df['date_op'].dt.dayofweek
        features['day_of_month'] = df['date_op'].dt.day
        features['hour'] = df['date_op'].dt.hour
        features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
        
        # Features textuelles (longueur, complexité)
        features['label_length'] = df['label'].str.len()
        features['label_word_count'] = df['label'].str.split().str.len()
        features['label_digit_count'] = df['label'].str.count(r'\\d')
        
        # Features par compte
        features['is_joint_account'] = df['account_label'].str.contains('joint', case=False, na=False).astype(int)
        
        # One-hot encoding pour les top catégories
        top_categories = df['category'].value_counts().head(10).index
        for cat in top_categories:
            features[f'category_{cat}'] = (df['category'] == cat).astype(int)
        
        return features.fillna(0)
    
    def _build_merchant_profiles(self, df: pd.DataFrame):
        """Construit les profils des marchands fréquents"""
        for _, row in df.iterrows():
            merchant = self._extract_merchant(row['label'])
            if not merchant:
                continue
                
            if merchant not in self.merchant_profiles:
                self.merchant_profiles[merchant] = {
                    'amounts': [],
                    'frequencies': [],
                    'categories': set(),
                    'first_seen': row['date_op'],
                    'transaction_count': 0
                }
            
            profile = self.merchant_profiles[merchant]
            profile['amounts'].append(abs(row['amount']))
            profile['categories'].add(row.get('category', 'Unknown'))
            profile['transaction_count'] += 1
        
        # Calcul des statistiques
        for merchant, profile in self.merchant_profiles.items():
            amounts = np.array(profile['amounts'])
            profile['amount_mean'] = np.mean(amounts)
            profile['amount_std'] = np.std(amounts)
            profile['amount_median'] = np.median(amounts)
            profile['amount_q75'] = np.percentile(amounts, 75)
            profile['amount_q95'] = np.percentile(amounts, 95)
        
        logger.info(f"Built profiles for {len(self.merchant_profiles)} merchants")
    
    def _build_category_profiles(self, df: pd.DataFrame):
        """Construit les profils par catégorie"""
        for category in df['category'].dropna().unique():
            category_txs = df[df['category'] == category]
            amounts = np.abs(category_txs['amount'])
            
            self.category_profiles[category] = {
                'amount_mean': amounts.mean(),
                'amount_std': amounts.std(),
                'amount_median': amounts.median(),
                'amount_q75': amounts.quantile(0.75),
                'amount_q95': amounts.quantile(0.95),
                'transaction_count': len(category_txs)
            }
    
    def _build_user_patterns(self, df: pd.DataFrame):
        """Analyse les patterns généraux de l'utilisateur"""
        amounts = np.abs(df['amount'])
        
        self.user_spending_patterns = {
            'daily_average': amounts.mean(),
            'daily_std': amounts.std(),
            'monthly_budget': amounts.sum() / max(1, len(df['month'].unique())),
            'frequent_amounts': amounts.round().value_counts().head(10).to_dict(),
            'spending_by_day': df.groupby(df['date_op'].dt.dayofweek)['amount'].sum().to_dict()
        }
    
    def _extract_merchant(self, label: str) -> str:
        """Extrait le nom du marchand du label"""
        if not label:
            return ""
        
        label_upper = str(label).upper()
        
        # Pattern pour paiements carte
        if 'CARTE' in label_upper and 'CB*' in label_upper:
            match = re.search(r'CARTE\\s+\\d{2}/\\d{2}/\\d{2,4}\\s+([^C]+?)\\s+CB', label_upper)
            if match:
                return match.group(1).strip()
        
        # Pattern pour virements
        elif 'VIR' in label_upper:
            match = re.search(r'VIR(?:EMENT)?\\s+(.+)', label_upper)
            if match:
                return match.group(1).strip()[:20]
        
        # Fallback: premiers mots significatifs
        words = re.findall(r'\\b[A-Z]{2,}\\b', label_upper)
        if words:
            return ' '.join(words[:2])
        
        return ""
    
    def detect_amount_anomalies(self, transaction: Dict) -> List[AnomalyResult]:
        """Détecte les anomalies de montant"""
        anomalies = []
        amount = abs(transaction['amount'])
        merchant = self._extract_merchant(transaction['label'])
        category = transaction.get('category', '')
        
        # 1. Anomalie vs profil marchand
        if merchant and merchant in self.merchant_profiles:
            profile = self.merchant_profiles[merchant]
            if profile['amount_std'] > 0:
                z_score = (amount - profile['amount_mean']) / profile['amount_std']
                
                if abs(z_score) > self.thresholds['amount_zscore']:
                    severity = min(1.0, abs(z_score) / 5.0)
                    anomalies.append(AnomalyResult(
                        transaction_id=str(transaction.get('id', 'unknown')),
                        anomaly_type='amount',
                        severity=severity,
                        explanation=f"Montant inhabituel pour {merchant}: {amount}€ vs moyenne {profile['amount_mean']:.2f}€",
                        reference_data={'merchant_mean': profile['amount_mean'], 'z_score': z_score},
                        confidence=min(0.95, 0.6 + severity * 0.3)
                    ))
        
        # 2. Anomalie vs profil catégorie
        if category and category in self.category_profiles:
            profile = self.category_profiles[category]
            if profile['amount_std'] > 0:
                z_score = (amount - profile['amount_mean']) / profile['amount_std']
                
                if abs(z_score) > self.thresholds['amount_zscore']:
                    severity = min(1.0, abs(z_score) / 4.0)
                    anomalies.append(AnomalyResult(
                        transaction_id=str(transaction.get('id', 'unknown')),
                        anomaly_type='amount',
                        severity=severity,
                        explanation=f"Montant inhabituel pour catégorie {category}: {amount}€ vs moyenne {profile['amount_mean']:.2f}€",
                        reference_data={'category_mean': profile['amount_mean'], 'z_score': z_score},
                        confidence=min(0.90, 0.5 + severity * 0.4)
                    ))
        
        # 3. Nouveau marchand avec montant élevé
        if merchant and merchant not in self.merchant_profiles and amount > self.thresholds['new_merchant_amount']:
            anomalies.append(AnomalyResult(
                transaction_id=str(transaction.get('id', 'unknown')),
                anomaly_type='merchant',
                severity=min(1.0, amount / 500.0),
                explanation=f"Nouveau marchand avec montant élevé: {merchant} ({amount}€)",
                reference_data={'new_merchant': merchant, 'amount': amount},
                confidence=0.75
            ))
        
        return anomalies
    
    def detect_duplicates(self, transactions: List[Dict]) -> List[DuplicateGroup]:
        """Détecte les doublons potentiels"""
        duplicates = []
        
        # Tri par date pour optimiser la recherche
        sorted_txs = sorted(transactions, key=lambda x: x.get('date_op', ''))
        
        for i, tx1 in enumerate(sorted_txs):
            potential_duplicates = [tx1]
            
            # Recherche dans une fenêtre temporelle
            for j in range(i + 1, len(sorted_txs)):
                tx2 = sorted_txs[j]
                
                # Vérification de la fenêtre temporelle
                date1 = pd.to_datetime(tx1.get('date_op', ''))
                date2 = pd.to_datetime(tx2.get('date_op', ''))
                
                if (date2 - date1).days > self.thresholds['duplicate_time_window']:
                    break
                
                # Test de similarité
                similarity = self._calculate_similarity(tx1, tx2)
                
                if similarity > self.thresholds['duplicate_similarity']:
                    potential_duplicates.append(tx2)
            
            # Si on a trouvé des doublons potentiels
            if len(potential_duplicates) > 1:
                similarity_score = self._group_similarity_score(potential_duplicates)
                duplicate_type = self._classify_duplicate_type(potential_duplicates)
                
                duplicates.append(DuplicateGroup(
                    transactions=potential_duplicates,
                    similarity_score=similarity_score,
                    duplicate_type=duplicate_type,
                    explanation=self._explain_duplicate_group(potential_duplicates)
                ))
        
        # Dédoublonnage des groupes (éviter les overlaps)
        return self._deduplicate_groups(duplicates)
    
    def _calculate_similarity(self, tx1: Dict, tx2: Dict) -> float:
        """Calcule la similarité entre deux transactions"""
        scores = []
        
        # Similarité des montants (tolérance 1%)
        amount1, amount2 = abs(tx1.get('amount', 0)), abs(tx2.get('amount', 0))
        if amount1 > 0 and amount2 > 0:
            amount_similarity = 100 * (1 - abs(amount1 - amount2) / max(amount1, amount2))
            scores.append(amount_similarity * 0.4)  # Poids 40%
        
        # Similarité des labels
        label1, label2 = str(tx1.get('label', '')), str(tx2.get('label', ''))
        label_similarity = fuzz.ratio(label1, label2)
        scores.append(label_similarity * 0.5)  # Poids 50%
        
        # Similarité des comptes
        account1, account2 = tx1.get('account_label', ''), tx2.get('account_label', '')
        account_similarity = 100 if account1 == account2 else 50
        scores.append(account_similarity * 0.1)  # Poids 10%
        
        return sum(scores) / len(scores) if scores else 0
    
    def _classify_duplicate_type(self, transactions: List[Dict]) -> str:
        """Classifie le type de doublon"""
        if len(transactions) < 2:
            return 'single'
        
        # Vérification montants exacts
        amounts = [tx.get('amount', 0) for tx in transactions]
        if len(set(amounts)) == 1:
            # Vérification labels exacts
            labels = [tx.get('label', '') for tx in transactions]
            if len(set(labels)) == 1:
                return 'exact'
            else:
                return 'fuzzy'
        
        return 'temporal'
    
    def _group_similarity_score(self, transactions: List[Dict]) -> float:
        """Calcule le score de similarité d'un groupe"""
        if len(transactions) < 2:
            return 0.0
        
        total_similarity = 0
        comparisons = 0
        
        for i in range(len(transactions)):
            for j in range(i + 1, len(transactions)):
                total_similarity += self._calculate_similarity(transactions[i], transactions[j])
                comparisons += 1
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def _explain_duplicate_group(self, transactions: List[Dict]) -> str:
        """Génère une explication pour un groupe de doublons"""
        if len(transactions) < 2:
            return "Transaction unique"
        
        amounts = [abs(tx.get('amount', 0)) for tx in transactions]
        dates = [tx.get('date_op', '') for tx in transactions]
        
        if len(set(amounts)) == 1:
            return f"{len(transactions)} transactions identiques de {amounts[0]}€ entre {min(dates)} et {max(dates)}"
        else:
            return f"{len(transactions)} transactions similaires (montants: {min(amounts):.2f}€-{max(amounts):.2f}€)"
    
    def _deduplicate_groups(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """Élimine les groupes de doublons qui se chevauchent"""
        # Simple déduplication basée sur les IDs de transactions
        seen_tx_ids = set()
        deduplicated = []
        
        # Trier par score de similarité (plus élevé en premier)
        sorted_groups = sorted(groups, key=lambda g: g.similarity_score, reverse=True)
        
        for group in sorted_groups:
            group_tx_ids = {str(tx.get('id', f"tx_{hash(str(tx))}")) for tx in group.transactions}
            
            # Si aucune transaction de ce groupe n'a déjà été vue
            if not group_tx_ids.intersection(seen_tx_ids):
                deduplicated.append(group)
                seen_tx_ids.update(group_tx_ids)
        
        return deduplicated
    
    def analyze_transaction(self, transaction: Dict, 
                          historical_transactions: List[Dict] = None) -> List[AnomalyResult]:
        """
        Analyse complète d'une transaction pour détecter les anomalies
        """
        anomalies = []
        
        # 1. Détection des anomalies de montant
        amount_anomalies = self.detect_amount_anomalies(transaction)
        anomalies.extend(amount_anomalies)
        
        # 2. Détection via Isolation Forest (si modèle entraîné)
        if self.isolation_forest is not None:
            try:
                features_df = self._prepare_features(pd.DataFrame([transaction]))
                feature_vector = self.scaler.transform(features_df)
                
                anomaly_score = self.isolation_forest.decision_function(feature_vector)[0]
                is_anomaly = self.isolation_forest.predict(feature_vector)[0] == -1
                
                if is_anomaly:
                    severity = min(1.0, abs(anomaly_score) / 2.0)
                    anomalies.append(AnomalyResult(
                        transaction_id=str(transaction.get('id', 'unknown')),
                        anomaly_type='statistical',
                        severity=severity,
                        explanation=f"Transaction statistiquement anormale (score: {anomaly_score:.3f})",
                        reference_data={'isolation_score': anomaly_score},
                        confidence=0.70 + severity * 0.2
                    ))
            
            except Exception as e:
                logger.warning(f"Isolation Forest analysis failed: {e}")
        
        # 3. Détection de doublons (si données historiques fournies)
        if historical_transactions:
            recent_transactions = [transaction] + historical_transactions[-50:]  # Dernières 50
            duplicate_groups = self.detect_duplicates(recent_transactions)
            
            for group in duplicate_groups:
                # Vérifier si notre transaction est dans un groupe de doublons
                tx_in_group = any(
                    str(tx.get('id', '')) == str(transaction.get('id', ''))
                    for tx in group.transactions
                )
                
                if tx_in_group and len(group.transactions) > 1:
                    anomalies.append(AnomalyResult(
                        transaction_id=str(transaction.get('id', 'unknown')),
                        anomaly_type='duplicate',
                        severity=group.similarity_score / 100.0,
                        explanation=f"Doublon potentiel: {group.explanation}",
                        reference_data={'duplicate_group_size': len(group.transactions)},
                        confidence=group.similarity_score / 100.0
                    ))
        
        return anomalies
    
    def batch_analyze(self, transactions: List[Dict]) -> Tuple[List[AnomalyResult], List[DuplicateGroup]]:
        """Analyse un batch de transactions"""
        all_anomalies = []
        
        # Analyse individuelle de chaque transaction
        for transaction in transactions:
            anomalies = self.analyze_transaction(transaction, transactions)
            all_anomalies.extend(anomalies)
        
        # Détection globale des doublons
        duplicate_groups = self.detect_duplicates(transactions)
        
        return all_anomalies, duplicate_groups

def main():
    """Test du détecteur d'anomalies"""
    import sqlite3
    
    try:
        # Chargement des données
        conn = sqlite3.connect('budget.db')
        df = pd.read_sql_query('SELECT * FROM transactions', conn)
        conn.close()
        
        print("=== TEST ANOMALY DETECTOR ===")
        print(f"Loaded {len(df)} transactions")
        
        # Création et entraînement du détecteur
        detector = TransactionAnomalyDetector()
        detector.fit(df)
        
        print(f"Built profiles for {len(detector.merchant_profiles)} merchants")
        print(f"Built profiles for {len(detector.category_profiles)} categories")
        
        # Test sur quelques transactions
        transactions = df.to_dict('records')[:20]
        
        print("\\n--- Analyse d'anomalies ---")
        anomalies, duplicates = detector.batch_analyze(transactions)
        
        print(f"Found {len(anomalies)} anomalies:")
        for anomaly in anomalies[:5]:  # Top 5
            print(f"  - {anomaly.anomaly_type}: {anomaly.explanation} (severity: {anomaly.severity:.2f})")
        
        print(f"\\nFound {len(duplicates)} duplicate groups:")
        for group in duplicates[:3]:  # Top 3
            print(f"  - {group.duplicate_type}: {group.explanation} (similarity: {group.similarity_score:.1f}%)")
        
        # Test sur transaction spécifique avec montant élevé
        print("\\n--- Test transaction suspecte ---")
        suspicious_tx = {
            'id': 'test_1',
            'label': 'NOUVEAU MARCHAND INCONNU',
            'amount': -500.00,
            'date_op': '2025-08-10',
            'category': 'Non catégorisé',
            'account_label': 'Test Account'
        }
        
        suspicious_anomalies = detector.analyze_transaction(suspicious_tx, transactions)
        print(f"Suspicious transaction anomalies: {len(suspicious_anomalies)}")
        for anomaly in suspicious_anomalies:
            print(f"  - {anomaly.anomaly_type}: {anomaly.explanation}")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    main()