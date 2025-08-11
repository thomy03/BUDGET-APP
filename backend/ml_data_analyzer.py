#!/usr/bin/env python3
"""
Analyseur de données pour le système ML d'auto-tagging
Extrait et analyse les transactions pour préparer l'entraînement ML
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import re
from collections import Counter
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionDataAnalyzer:
    def __init__(self, db_path: str = "budget.db"):
        self.db_path = db_path
        self.df = None
        
    def load_data(self) -> pd.DataFrame:
        """Charge les données depuis la base SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            self.df = pd.read_sql_query('SELECT * FROM transactions', conn)
            conn.close()
            logger.info(f"Loaded {len(self.df)} transactions")
            return self.df
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return None
    
    def analyze_labels(self) -> Dict:
        """Analyse les labels des transactions pour extraction de features"""
        if self.df is None:
            return {}
            
        labels = self.df['label'].fillna('')
        
        # Statistiques de base
        stats = {
            'total_labels': len(labels),
            'unique_labels': labels.nunique(),
            'avg_length': labels.str.len().mean(),
            'max_length': labels.str.len().max(),
            'empty_labels': (labels == '').sum()
        }
        
        # Extraction de patterns fréquents
        # Détection des codes CB
        cb_pattern = r'CB\*\d+'
        cb_matches = labels.str.extract(f'({cb_pattern})', expand=False).dropna()
        
        # Détection des dates
        date_pattern = r'\d{2}/\d{2}/\d{2,4}'
        date_matches = labels.str.extract(f'({date_pattern})', expand=False).dropna()
        
        # Mots les plus fréquents
        all_words = []
        for label in labels:
            # Nettoyage et extraction des mots
            clean_label = re.sub(r'[^\w\s]', ' ', label.upper())
            words = [w for w in clean_label.split() if len(w) > 2]
            all_words.extend(words)
        
        word_freq = Counter(all_words).most_common(20)
        
        patterns = {
            'cb_codes': len(cb_matches),
            'date_patterns': len(date_matches),
            'top_words': word_freq
        }
        
        return {'stats': stats, 'patterns': patterns}
    
    def analyze_categories(self) -> Dict:
        """Analyse la distribution des catégories"""
        if self.df is None:
            return {}
            
        category_dist = self.df['category'].value_counts().to_dict()
        parent_dist = self.df['category_parent'].value_counts().to_dict()
        
        # Catégories manquantes ou "Non catégorisé"
        missing_categories = self.df[
            (self.df['category'].isna()) | 
            (self.df['category'] == '') | 
            (self.df['category'] == 'Non catégorisé')
        ]
        
        return {
            'category_distribution': category_dist,
            'parent_category_distribution': parent_dist,
            'missing_categories_count': len(missing_categories),
            'missing_percentage': len(missing_categories) / len(self.df) * 100
        }
    
    def analyze_tags(self) -> Dict:
        """Analyse les tags existants"""
        if self.df is None:
            return {}
            
        # Transactions avec tags non vides
        tagged_df = self.df[
            self.df['tags'].notna() & 
            (self.df['tags'] != '')
        ]
        
        if len(tagged_df) == 0:
            return {
                'tagged_count': 0,
                'tagged_percentage': 0,
                'tag_distribution': {},
                'samples': []
            }
        
        # Distribution des tags
        all_tags = []
        for tags_str in tagged_df['tags']:
            # Supposer que les tags sont séparés par des virgules
            tags = [tag.strip() for tag in str(tags_str).split(',') if tag.strip()]
            all_tags.extend(tags)
        
        tag_dist = Counter(all_tags).most_common(10)
        
        # Échantillons de transactions taguées
        samples = []
        for _, row in tagged_df.head(5).iterrows():
            samples.append({
                'label': row['label'][:60] + '...' if len(row['label']) > 60 else row['label'],
                'tags': row['tags'],
                'category': row['category']
            })
        
        return {
            'tagged_count': len(tagged_df),
            'tagged_percentage': len(tagged_df) / len(self.df) * 100,
            'tag_distribution': tag_dist,
            'samples': samples
        }
    
    def extract_merchant_patterns(self) -> Dict:
        """Extrait les patterns de marchands pour le feature engineering"""
        if self.df is None:
            return {}
        
        labels = self.df['label'].fillna('')
        
        # Patterns courants des marchands
        patterns = {
            'carte_patterns': [],
            'virement_patterns': [],
            'prelevement_patterns': [],
            'merchant_names': []
        }
        
        for label in labels:
            label_upper = label.upper()
            
            # Patterns de carte
            if 'CARTE' in label_upper and 'CB*' in label_upper:
                # Extraction du nom du marchand
                match = re.search(r'CARTE\s+\d{2}/\d{2}/\d{2}\s+([^C]+)\s+CB', label_upper)
                if match:
                    merchant = match.group(1).strip()
                    patterns['carte_patterns'].append(merchant)
            
            # Patterns de virement
            elif 'VIR' in label_upper or 'VIREMENT' in label_upper:
                patterns['virement_patterns'].append(label[:50])
            
            # Patterns de prélèvement
            elif 'PRLV' in label_upper or 'PRELEVEMENT' in label_upper:
                patterns['prelevement_patterns'].append(label[:50])
        
        # Comptage des patterns les plus fréquents
        for key in patterns:
            if patterns[key]:
                patterns[key] = Counter(patterns[key]).most_common(10)
        
        return patterns
    
    def generate_ml_features_sample(self) -> Dict:
        """Génère un échantillon des features pour l'entraînement ML"""
        if self.df is None:
            return {}
        
        # Sélection d'un échantillon représentatif
        sample_size = min(50, len(self.df))
        sample_df = self.df.sample(n=sample_size, random_state=42)
        
        features_sample = []
        for _, row in sample_df.iterrows():
            features = {
                'label': row['label'],
                'category': row['category'],
                'category_parent': row['category_parent'],
                'amount': row['amount'],
                'is_expense': row['is_expense'],
                'tags': row['tags'] if pd.notna(row['tags']) and row['tags'] else '',
                'account_label': row['account_label']
            }
            features_sample.append(features)
        
        return {'sample_data': features_sample, 'sample_size': sample_size}
    
    def run_complete_analysis(self) -> Dict:
        """Lance l'analyse complète des données"""
        logger.info("Starting complete data analysis...")
        
        # Chargement des données
        if self.load_data() is None:
            return {'error': 'Failed to load data'}
        
        analysis = {
            'dataset_info': {
                'total_transactions': len(self.df),
                'date_range': {
                    'min_date': self.df['date_op'].min(),
                    'max_date': self.df['date_op'].max()
                },
                'accounts': self.df['account_label'].value_counts().to_dict()
            },
            'label_analysis': self.analyze_labels(),
            'category_analysis': self.analyze_categories(),
            'tag_analysis': self.analyze_tags(),
            'merchant_patterns': self.extract_merchant_patterns(),
            'ml_sample': self.generate_ml_features_sample()
        }
        
        logger.info("Analysis completed successfully")
        return analysis

def main():
    """Point d'entrée principal"""
    analyzer = TransactionDataAnalyzer()
    analysis = analyzer.run_complete_analysis()
    
    # Sauvegarde des résultats
    with open('ml_data_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
    
    # Affichage des résultats clés
    print("=== ANALYSE DES DONNÉES POUR ML ===")
    
    if 'error' in analysis:
        print(f"Erreur: {analysis['error']}")
        return
    
    dataset_info = analysis['dataset_info']
    print(f"\nDataset: {dataset_info['total_transactions']} transactions")
    print(f"Période: {dataset_info['date_range']['min_date']} -> {dataset_info['date_range']['max_date']}")
    
    label_stats = analysis['label_analysis']['stats']
    print(f"\nLabels: {label_stats['unique_labels']} uniques sur {label_stats['total_labels']}")
    print(f"Longueur moyenne: {label_stats['avg_length']:.1f} caractères")
    
    tag_info = analysis['tag_analysis']
    print(f"\nTags: {tag_info['tagged_count']} transactions taguées ({tag_info['tagged_percentage']:.1f}%)")
    
    category_info = analysis['category_analysis']
    print(f"\nCatégories manquantes: {category_info['missing_categories_count']} ({category_info['missing_percentage']:.1f}%)")
    
    print("\nTop mots dans les labels:")
    for word, count in analysis['label_analysis']['patterns']['top_words'][:5]:
        print(f"  - {word}: {count}")
    
    print("\nAnalyse sauvegardée dans 'ml_data_analysis.json'")

if __name__ == "__main__":
    main()