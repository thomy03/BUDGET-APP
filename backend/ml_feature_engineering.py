#!/usr/bin/env python3
"""
Feature Engineering pour le système ML d'auto-tagging
Extraction et création de features à partir des labels de transactions
"""

import re
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Set
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import LabelEncoder, StandardScaler
import logging
from collections import Counter
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionFeatureExtractor:
    def __init__(self):
        self.tfidf_vectorizer = None
        self.label_encoder = None
        self.scaler = StandardScaler()
        self.merchant_patterns = {}
        self.category_mapping = {}
        
    def clean_text(self, text: str) -> str:
        """Nettoie et normalise le texte des labels"""
        if pd.isna(text) or text == '':
            return ''
        
        # Conversion en majuscules
        text = str(text).upper()
        
        # Suppression des patterns de dates spécifiques
        text = re.sub(r'\d{2}/\d{2}/\d{2,4}', ' DATE ', text)
        
        # Suppression des codes CB
        text = re.sub(r'CB\*\d+', ' CARTE ', text)
        
        # Suppression des numéros de référence longs
        text = re.sub(r'\b\d{6,}\b', ' NUM ', text)
        
        # Suppression des caractères spéciaux sauf espaces et lettres
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Suppression des espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_merchant_name(self, label: str) -> str:
        """Extrait le nom du marchand depuis le label"""
        if pd.isna(label) or label == '':
            return ''
        
        label_upper = str(label).upper()
        
        # Pattern pour les paiements carte
        if 'CARTE' in label_upper and 'CB*' in label_upper:
            # Format: CARTE DD/MM/YY MERCHANT_NAME CB*XXXX
            match = re.search(r'CARTE\s+\d{2}/\d{2}/\d{2,4}\s+([^C]+?)\s+CB', label_upper)
            if match:
                merchant = match.group(1).strip()
                # Nettoyage du nom du marchand
                merchant = re.sub(r'\s+', ' ', merchant)
                return merchant
        
        # Pattern pour les virements
        elif 'VIR' in label_upper:
            # Extraction après VIR ou VIREMENT
            match = re.search(r'VIR(?:EMENT)?\s+(.+)', label_upper)
            if match:
                return match.group(1).strip()[:30]  # Limiter la longueur
        
        # Pattern pour les prélèvements
        elif 'PRLV' in label_upper:
            match = re.search(r'PRLV\s+(.+)', label_upper)
            if match:
                return match.group(1).strip()[:30]
        
        # Fallback: premier mot significatif
        words = self.clean_text(label).split()
        if words:
            return words[0]
        
        return ''
    
    def extract_payment_method(self, label: str) -> str:
        """Détermine la méthode de paiement"""
        if pd.isna(label) or label == '':
            return 'UNKNOWN'
        
        label_upper = str(label).upper()
        
        if 'CARTE' in label_upper or 'CB*' in label_upper:
            return 'CARD'
        elif 'VIR' in label_upper or 'VIREMENT' in label_upper:
            return 'TRANSFER'
        elif 'PRLV' in label_upper or 'PRELEVEMENT' in label_upper:
            return 'DIRECT_DEBIT'
        elif 'CHQ' in label_upper or 'CHEQUE' in label_upper:
            return 'CHECK'
        elif 'RETRAIT' in label_upper:
            return 'WITHDRAWAL'
        else:
            return 'OTHER'
    
    def extract_ngrams(self, text: str, n: int = 2) -> List[str]:
        """Extrait les n-grammes du texte"""
        words = self.clean_text(text).split()
        if len(words) < n:
            return words
        
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        
        return ngrams
    
    def create_numerical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée des features numériques à partir des données"""
        features_df = df.copy()
        
        # Features basées sur le montant
        features_df['amount_abs'] = np.abs(features_df['amount'])
        features_df['amount_log'] = np.log1p(features_df['amount_abs'])
        features_df['amount_rounded'] = np.round(features_df['amount_abs'] / 10) * 10
        
        # Features temporelles
        features_df['date_op'] = pd.to_datetime(features_df['date_op'])
        features_df['day_of_week'] = features_df['date_op'].dt.dayofweek
        features_df['day_of_month'] = features_df['date_op'].dt.day
        features_df['month'] = features_df['date_op'].dt.month
        features_df['is_weekend'] = (features_df['day_of_week'] >= 5).astype(int)
        
        # Features sur les labels
        features_df['label_length'] = features_df['label'].str.len()
        features_df['label_word_count'] = features_df['label'].str.split().str.len()
        features_df['label_has_numbers'] = features_df['label'].str.contains(r'\\d').astype(int)
        
        return features_df
    
    def create_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée des features catégorielles"""
        features_df = df.copy()
        
        # Extraction des features métier
        features_df['merchant_name'] = features_df['label'].apply(self.extract_merchant_name)
        features_df['payment_method'] = features_df['label'].apply(self.extract_payment_method)
        
        # Features basées sur les comptes
        features_df['is_joint_account'] = features_df['account_label'].str.contains('joint', case=False).astype(int)
        
        return features_df
    
    def create_text_features(self, df: pd.DataFrame, max_features: int = 100) -> Tuple[np.ndarray, List[str]]:
        """Crée des features TF-IDF à partir des labels"""
        # Préparation du texte
        clean_labels = df['label'].apply(self.clean_text)
        
        # Configuration du vectorizer TF-IDF
        if self.tfidf_vectorizer is None:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=max_features,
                min_df=2,  # Ignorer les termes trop rares
                max_df=0.8,  # Ignorer les termes trop fréquents
                ngram_range=(1, 2),  # Unigrams et bigrams
                stop_words=None  # Pas de stop words pour les données financières
            )
            tfidf_features = self.tfidf_vectorizer.fit_transform(clean_labels)
        else:
            tfidf_features = self.tfidf_vectorizer.transform(clean_labels)
        
        feature_names = self.tfidf_vectorizer.get_feature_names_out()
        return tfidf_features.toarray(), feature_names.tolist()
    
    def engineer_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
        """Pipeline complet de feature engineering"""
        logger.info(f"Starting feature engineering for {len(df)} transactions")
        
        # 1. Features numériques
        features_df = self.create_numerical_features(df)
        logger.info(\"✅ Numerical features created\")
        
        # 2. Features catégorielles
        features_df = self.create_categorical_features(features_df)
        logger.info(\"✅ Categorical features created\")
        
        # 3. Features textuelles (TF-IDF)
        tfidf_features, tfidf_feature_names = self.create_text_features(df)
        logger.info(f\"✅ TF-IDF features created: {tfidf_features.shape[1]} features\")
        
        # Sélection des features numériques pour la normalisation
        numerical_cols = [
            'amount_abs', 'amount_log', 'amount_rounded',
            'day_of_week', 'day_of_month', 'month',
            'label_length', 'label_word_count'
        ]
        
        # Normalisation des features numériques
        features_df[numerical_cols] = self.scaler.fit_transform(features_df[numerical_cols])
        
        logger.info(\"Feature engineering completed successfully\")
        
        return features_df, tfidf_features, tfidf_feature_names
    
    def create_merchant_clusters(self, df: pd.DataFrame, min_frequency: int = 2) -> Dict[str, int]:
        """Crée des clusters de marchands basés sur la fréquence"""
        merchant_names = df['label'].apply(self.extract_merchant_name)
        merchant_counts = Counter(merchant_names)
        
        # Garder seulement les marchands fréquents
        frequent_merchants = {
            merchant: idx for idx, (merchant, count) 
            in enumerate(merchant_counts.most_common()) 
            if count >= min_frequency and merchant != ''
        }
        
        logger.info(f\"Created {len(frequent_merchants)} merchant clusters\")
        return frequent_merchants
    
    def prepare_target_labels(self, df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, int]]:
        \"\"\"Prépare les labels cibles pour l'entraînement\"\"\"
        # Utiliser les catégories existantes comme labels
        categories = df['category'].fillna('Non catégorisé')
        
        # Encoder les catégories
        if self.label_encoder is None:
            self.label_encoder = LabelEncoder()
            encoded_labels = self.label_encoder.fit_transform(categories)
        else:
            encoded_labels = self.label_encoder.transform(categories)
        
        # Créer le mapping
        label_mapping = {
            label: idx for idx, label in enumerate(self.label_encoder.classes_)
        }
        
        logger.info(f\"Prepared {len(set(encoded_labels))} target categories\")
        
        return encoded_labels, label_mapping

def main():
    \"\"\"Test du feature engineering\"\"\"
    # Chargement des données
    conn = sqlite3.connect('budget.db')
    df = pd.read_sql_query('SELECT * FROM transactions', conn)
    conn.close()
    
    # Feature engineering
    extractor = TransactionFeatureExtractor()
    features_df, tfidf_features, tfidf_names = extractor.engineer_features(df)
    target_labels, label_mapping = extractor.prepare_target_labels(df)
    
    print(\"=== FEATURE ENGINEERING RESULTS ===\")
    print(f\"Features shape: {features_df.shape}\")
    print(f\"TF-IDF features shape: {tfidf_features.shape}\")
    print(f\"Target labels: {len(set(target_labels))} classes\")
    
    # Affichage des features les plus importantes (TF-IDF)
    print(\"\\nTop TF-IDF features:\")
    for i, name in enumerate(tfidf_names[:10]):
        importance = np.mean(tfidf_features[:, i])
        print(f\"  - {name}: {importance:.4f}\")
    
    # Affichage des catégories
    print(\"\\nTarget categories:\")
    for category, idx in sorted(label_mapping.items(), key=lambda x: x[1]):
        count = (target_labels == idx).sum()
        print(f\"  - {category}: {count} transactions\")

if __name__ == \"__main__\":
    main()