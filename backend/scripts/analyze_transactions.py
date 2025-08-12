#!/usr/bin/env python3
"""
Script d'analyse des transactions pour identifier les patterns récurrents
et définir les critères de détection intelligente pour les provisions automatiques
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from typing import Dict, List, Tuple, Any

class TransactionAnalyzer:
    def __init__(self, db_path: str = "budget.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def get_schema_info(self):
        """Examiner le schéma de la base de données"""
        cursor = self.conn.cursor()
        
        # Obtenir la liste des tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema_info[table_name] = [
                {
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default': col[4],
                    'primary_key': bool(col[5])
                }
                for col in columns
            ]
            
        return schema_info
    
    def get_transaction_stats(self):
        """Analyser les statistiques générales des transactions"""
        cursor = self.conn.cursor()
        
        # Déterminer quelle table utiliser (tx ou transactions)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('tx', 'transactions')")
        available_tables = [row[0] for row in cursor.fetchall()]
        
        if 'tx' in available_tables:
            table_name = 'tx'
            date_col = 'date'
            amount_col = 'montant'
            desc_col = 'description'
            tag_col = 'tag'
        elif 'transactions' in available_tables:
            table_name = 'transactions'
            date_col = 'date_op'
            amount_col = 'amount'
            desc_col = 'label'
            tag_col = 'tags'
        else:
            raise ValueError("Aucune table de transactions trouvée")
        
        # Compter le nombre total de transactions
        cursor.execute(f"SELECT COUNT(*) as total FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        # Analyser les dates (plage et distribution)
        cursor.execute(f"""
            SELECT 
                MIN({date_col}) as earliest_date,
                MAX({date_col}) as latest_date,
                COUNT(*) as count
            FROM {table_name}
        """)
        date_stats = cursor.fetchone()
        
        # Analyser les montants
        cursor.execute(f"""
            SELECT 
                AVG({amount_col}) as avg_amount,
                MIN({amount_col}) as min_amount,
                MAX({amount_col}) as max_amount,
                COUNT(CASE WHEN {amount_col} < 0 THEN 1 END) as negative_count,
                COUNT(CASE WHEN {amount_col} > 0 THEN 1 END) as positive_count
            FROM {table_name}
        """)
        amount_stats = cursor.fetchone()
        
        # Analyser les tags
        cursor.execute(f"""
            SELECT 
                {tag_col},
                COUNT(*) as count,
                AVG({amount_col}) as avg_amount
            FROM {table_name}
            WHERE {tag_col} IS NOT NULL AND {tag_col} != ''
            GROUP BY {tag_col}
            ORDER BY count DESC
        """)
        tag_stats = cursor.fetchall()
        
        # Stocker les informations de la table utilisée
        self.table_info = {
            'name': table_name,
            'date_col': date_col,
            'amount_col': amount_col,
            'desc_col': desc_col,
            'tag_col': tag_col
        }
        
        return {
            'total_transactions': total_count,
            'date_range': {
                'earliest': date_stats[0],
                'latest': date_stats[1],
                'count': date_stats[2]
            },
            'amounts': {
                'average': round(amount_stats[0], 2) if amount_stats[0] else 0,
                'min': amount_stats[1],
                'max': amount_stats[2],
                'negative_count': amount_stats[3],
                'positive_count': amount_stats[4]
            },
            'tags': [
                {
                    'tag': row[0],
                    'count': row[1],
                    'avg_amount': round(row[2], 2) if row[2] else 0
                }
                for row in tag_stats
            ]
        }
    
    def analyze_recurring_patterns(self):
        """Identifier les patterns de récurrence dans les transactions"""
        cursor = self.conn.cursor()
        
        # S'assurer que table_info est disponible
        if not hasattr(self, 'table_info'):
            self.get_transaction_stats()  # Cela initialise table_info
        
        # Récupérer toutes les transactions avec leurs informations
        table = self.table_info['name']
        date_col = self.table_info['date_col']
        amount_col = self.table_info['amount_col']
        desc_col = self.table_info['desc_col']
        tag_col = self.table_info['tag_col']
        
        # Adapter la requête selon la table
        if table == 'tx':
            cursor.execute(f"""
                SELECT id, {date_col}, {amount_col}, {desc_col}, {tag_col}, NULL as category
                FROM {table}
                ORDER BY {date_col}
            """)
        else:  # table transactions
            cursor.execute(f"""
                SELECT id, {date_col}, {amount_col}, {desc_col}, {tag_col}, category
                FROM {table}
                ORDER BY {date_col}
            """)
        transactions = cursor.fetchall()
        
        # Analyser les patterns par libellé similaire
        libelle_groups = defaultdict(list)
        
        for tx in transactions:
            # Nettoyer le libellé pour regrouper les transactions similaires
            clean_description = self._clean_description(tx[3])
            libelle_groups[clean_description].append({
                'id': tx[0],
                'date': tx[1],
                'amount': tx[2],
                'original_description': tx[3],
                'tag': tx[4],
                'category': tx[5]
            })
        
        # Identifier les groupes récurrents (2+ occurrences)
        recurring_patterns = {}
        for description, txs in libelle_groups.items():
            if len(txs) >= 2:
                # Calculer les statistiques de récurrence
                amounts = [tx['amount'] for tx in txs]
                dates = [datetime.strptime(tx['date'], '%Y-%m-%d') for tx in txs]
                dates.sort()
                
                # Calculer les intervalles entre transactions
                intervals = []
                for i in range(1, len(dates)):
                    interval = (dates[i] - dates[i-1]).days
                    intervals.append(interval)
                
                recurring_patterns[description] = {
                    'count': len(txs),
                    'transactions': txs,
                    'amount_stats': {
                        'min': min(amounts),
                        'max': max(amounts),
                        'avg': sum(amounts) / len(amounts),
                        'variation': max(amounts) - min(amounts) if amounts else 0
                    },
                    'date_intervals': {
                        'intervals': intervals,
                        'avg_interval': sum(intervals) / len(intervals) if intervals else 0,
                        'first_date': dates[0].strftime('%Y-%m-%d'),
                        'last_date': dates[-1].strftime('%Y-%m-%d')
                    }
                }
        
        return recurring_patterns
    
    def _clean_description(self, description: str) -> str:
        """Nettoyer un libellé pour le regroupement"""
        if not description:
            return "UNKNOWN"
            
        # Convertir en majuscules
        clean = description.upper().strip()
        
        # Supprimer les dates communes
        clean = re.sub(r'\d{2}/\d{2}(/\d{4})?', '', clean)
        clean = re.sub(r'\d{4}-\d{2}-\d{2}', '', clean)
        
        # Supprimer les numéros de référence/transaction
        clean = re.sub(r'\b\d{6,}\b', '', clean)
        clean = re.sub(r'REF\s*:?\s*\w+', '', clean)
        clean = re.sub(r'TXN\s*:?\s*\w+', '', clean)
        
        # Supprimer les caractères spéciaux multiples
        clean = re.sub(r'[*-]{2,}', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean)
        
        # Extraire les mots-clés principaux (supprimer les mots courts)
        words = [w for w in clean.split() if len(w) > 2]
        
        # Prendre les 3 premiers mots significatifs
        return ' '.join(words[:3]) if words else "UNKNOWN"
    
    def identify_subscription_patterns(self):
        """Identifier spécifiquement les patterns d'abonnements"""
        recurring_patterns = self.analyze_recurring_patterns()
        
        # Mots-clés typiques d'abonnements
        subscription_keywords = [
            'NETFLIX', 'AMAZON', 'SPOTIFY', 'APPLE', 'MICROSOFT',
            'GOOGLE', 'ADOBE', 'DROPBOX', 'CANAL', 'ORANGE',
            'SFR', 'BOUYGUES', 'FREE', 'YOUTUBE', 'DISNEY',
            'SUBSCRIPTION', 'ABONNEMENT', 'MONTHLY', 'MENSUEL'
        ]
        
        subscription_candidates = {}
        
        for description, pattern in recurring_patterns.items():
            # Vérifier si c'est probablement un abonnement
            score = 0
            reasons = []
            
            # Score basé sur mots-clés
            for keyword in subscription_keywords:
                if keyword in description:
                    score += 20
                    reasons.append(f"Keyword: {keyword}")
            
            # Score basé sur la régularité des montants
            amount_variation = pattern['amount_stats']['variation']
            avg_amount = abs(pattern['amount_stats']['avg'])
            if avg_amount > 0:
                variation_pct = (amount_variation / avg_amount) * 100
                if variation_pct < 5:  # Moins de 5% de variation
                    score += 15
                    reasons.append(f"Stable amount (variation: {variation_pct:.1f}%)")
            
            # Score basé sur la régularité des intervalles
            if pattern['date_intervals']['intervals']:
                avg_interval = pattern['date_intervals']['avg_interval']
                # Vérifier si c'est proche d'un mois (25-35 jours)
                if 25 <= avg_interval <= 35:
                    score += 15
                    reasons.append(f"Monthly pattern ({avg_interval:.0f} days)")
                elif 85 <= avg_interval <= 95:  # Trimestre
                    score += 10
                    reasons.append(f"Quarterly pattern ({avg_interval:.0f} days)")
            
            # Score basé sur le nombre d'occurrences
            if pattern['count'] >= 3:
                score += 10
                reasons.append(f"Multiple occurrences ({pattern['count']})")
            
            if score >= 20:  # Seuil minimum pour être considéré comme abonnement
                subscription_candidates[description] = {
                    **pattern,
                    'subscription_score': score,
                    'reasons': reasons,
                    'suggested_monthly_amount': abs(pattern['amount_stats']['avg'])
                }
        
        return subscription_candidates
    
    def generate_analysis_report(self):
        """Générer le rapport complet d'analyse"""
        print("=== ANALYSE DES TRANSACTIONS RÉCURRENTES ===\n")
        
        # 1. Informations sur le schéma
        print("1. STRUCTURE DE LA BASE DE DONNÉES")
        schema = self.get_schema_info()
        for table_name, columns in schema.items():
            print(f"\nTable: {table_name}")
            for col in columns:
                print(f"  - {col['name']} ({col['type']}) {'NOT NULL' if col['not_null'] else ''}")
        
        # 2. Statistiques générales
        print("\n2. STATISTIQUES GÉNÉRALES")
        stats = self.get_transaction_stats()
        print(f"Total transactions: {stats['total_transactions']}")
        print(f"Période: {stats['date_range']['earliest']} à {stats['date_range']['latest']}")
        print(f"Montant moyen: {stats['amounts']['average']}€")
        print(f"Transactions négatives: {stats['amounts']['negative_count']}")
        print(f"Transactions positives: {stats['amounts']['positive_count']}")
        
        print("\nTags les plus fréquents:")
        for tag_info in stats['tags'][:10]:
            print(f"  - {tag_info['tag']}: {tag_info['count']} transactions (moyenne: {tag_info['avg_amount']}€)")
        
        # 3. Patterns récurrents
        print("\n3. PATTERNS RÉCURRENTS DÉTECTÉS")
        recurring = self.analyze_recurring_patterns()
        print(f"Nombre de patterns récurrents identifiés: {len(recurring)}")
        
        for description, pattern in list(recurring.items())[:10]:
            print(f"\nPattern: {description}")
            print(f"  Occurrences: {pattern['count']}")
            print(f"  Montant moyen: {pattern['amount_stats']['avg']:.2f}€")
            print(f"  Variation: {pattern['amount_stats']['variation']:.2f}€")
            if pattern['date_intervals']['intervals']:
                print(f"  Intervalle moyen: {pattern['date_intervals']['avg_interval']:.0f} jours")
        
        # 4. Abonnements identifiés
        print("\n4. ABONNEMENTS POTENTIELS")
        subscriptions = self.identify_subscription_patterns()
        print(f"Nombre d'abonnements potentiels: {len(subscriptions)}")
        
        for description, sub in subscriptions.items():
            print(f"\nAbonnement: {description}")
            print(f"  Score de confiance: {sub['subscription_score']}/100")
            print(f"  Montant mensuel suggéré: {sub['suggested_monthly_amount']:.2f}€")
            print(f"  Raisons: {', '.join(sub['reasons'])}")
            print(f"  Dernière transaction: {sub['transactions'][-1]['original_description']}")
        
        return {
            'schema': schema,
            'stats': stats,
            'recurring_patterns': recurring,
            'subscription_candidates': subscriptions
        }
    
    def export_analysis(self, filename: str = "transaction_analysis.json"):
        """Exporter l'analyse complète en JSON"""
        analysis = self.generate_analysis_report()
        
        # Convertir les objets datetime en strings pour JSON
        def json_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            raise TypeError(f"Object {obj} is not JSON serializable")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False, default=json_serializer)
        
        print(f"\nAnalyse exportée vers: {filename}")
        return analysis
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    analyzer = TransactionAnalyzer()
    analysis = analyzer.generate_analysis_report()
    analyzer.export_analysis()