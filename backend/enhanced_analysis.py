#!/usr/bin/env python3
"""
Analyse approfondie pour identifier les vrais patterns récurrents
et comparer les données des deux tables (tx et transactions)
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import numpy as np

class EnhancedTransactionAnalyzer:
    def __init__(self, db_path: str = "budget.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def compare_tables(self):
        """Comparer les données entre les tables tx et transactions"""
        cursor = self.conn.cursor()
        
        # Analyser la table tx
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM tx")
        tx_stats = cursor.fetchone()
        
        # Analyser la table transactions
        cursor.execute("SELECT COUNT(*), MIN(date_op), MAX(date_op) FROM transactions")
        trans_stats = cursor.fetchone()
        
        print("=== COMPARAISON DES TABLES ===")
        print(f"Table 'tx': {tx_stats[0]} transactions du {tx_stats[1]} au {tx_stats[2]}")
        print(f"Table 'transactions': {trans_stats[0]} transactions du {trans_stats[1]} au {trans_stats[2]}")
        
        # Échantillons de données
        print("\n--- Échantillon table 'tx' ---")
        cursor.execute("SELECT date, description, montant, tag FROM tx LIMIT 10")
        for row in cursor.fetchall():
            print(f"{row[0]} | {row[1][:30]:30} | {row[2]:8.2f}€ | {row[3] or 'N/A'}")
            
        print("\n--- Échantillon table 'transactions' ---")
        cursor.execute("SELECT date_op, label, amount, tags, category FROM transactions LIMIT 10")
        for row in cursor.fetchall():
            print(f"{row[0]} | {row[1][:30]:30} | {row[2]:8.2f}€ | {row[3] or 'N/A'} | {row[4] or 'N/A'}")
        
        return {
            'tx': {'count': tx_stats[0], 'date_range': (tx_stats[1], tx_stats[2])},
            'transactions': {'count': trans_stats[0], 'date_range': (trans_stats[1], trans_stats[2])}
        }
    
    def analyze_real_patterns(self):
        """Analyser les vrais patterns avec une logique plus sophistiquée"""
        cursor = self.conn.cursor()
        
        # Utiliser la table avec le plus de données
        cursor.execute("SELECT COUNT(*) FROM tx")
        tx_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM transactions") 
        trans_count = cursor.fetchone()[0]
        
        if trans_count > tx_count:
            table = 'transactions'
            query = """
                SELECT date_op as date, label as description, amount, tags, category
                FROM transactions 
                WHERE exclude = 0 OR exclude IS NULL
                ORDER BY date_op
            """
        else:
            table = 'tx'
            query = """
                SELECT date, description, montant as amount, tag as tags, NULL as category
                FROM tx
                ORDER BY date
            """
        
        cursor.execute(query)
        transactions = cursor.fetchall()
        
        print(f"\n=== ANALYSE APPROFONDIE ({len(transactions)} transactions de '{table}') ===")
        
        # Grouper par libellé similaire avec une logique plus fine
        groups = defaultdict(list)
        
        for tx in transactions:
            clean_desc = self._advanced_clean_description(tx[1])
            if clean_desc and clean_desc != "UNKNOWN":
                groups[clean_desc].append({
                    'date': tx[0],
                    'description': tx[1],
                    'amount': float(tx[2]) if tx[2] else 0.0,
                    'tags': tx[3],
                    'category': tx[4]
                })
        
        # Analyser les vrais patterns récurrents
        recurring_candidates = {}
        
        for desc, txs in groups.items():
            if len(txs) >= 2:  # Au moins 2 occurrences
                amounts = [tx['amount'] for tx in txs]
                dates = [datetime.strptime(tx['date'], '%Y-%m-%d') for tx in txs]
                dates.sort()
                
                # Calculer les statistiques
                amount_std = np.std(amounts)
                amount_mean = np.mean(amounts)
                amount_variation_pct = (amount_std / abs(amount_mean) * 100) if amount_mean != 0 else 100
                
                # Intervalles entre transactions
                intervals = []
                for i in range(1, len(dates)):
                    interval = (dates[i] - dates[i-1]).days
                    intervals.append(interval)
                
                # Score de récurrence
                score = self._calculate_recurrence_score(
                    len(txs), amount_variation_pct, intervals, desc, abs(amount_mean)
                )
                
                if score >= 30:  # Seuil plus élevé pour les vrais patterns
                    recurring_candidates[desc] = {
                        'count': len(txs),
                        'transactions': txs,
                        'amount_stats': {
                            'mean': round(amount_mean, 2),
                            'std': round(amount_std, 2),
                            'variation_pct': round(amount_variation_pct, 2),
                            'min': min(amounts),
                            'max': max(amounts)
                        },
                        'date_intervals': {
                            'intervals': intervals,
                            'avg_interval': round(np.mean(intervals), 1) if intervals else 0,
                            'std_interval': round(np.std(intervals), 1) if intervals else 0
                        },
                        'recurrence_score': score,
                        'period_days': (dates[-1] - dates[0]).days if len(dates) > 1 else 0
                    }
        
        # Trier par score de récurrence
        sorted_candidates = dict(sorted(
            recurring_candidates.items(), 
            key=lambda x: x[1]['recurrence_score'], 
            reverse=True
        ))
        
        return sorted_candidates
    
    def _advanced_clean_description(self, description: str) -> str:
        """Nettoyage plus sophistiqué des libellés"""
        if not description:
            return "UNKNOWN"
            
        # Convertir en majuscules et nettoyer
        clean = description.upper().strip()
        
        # Supprimer les éléments variables spécifiques
        patterns_to_remove = [
            r'\d{2}/\d{2}(/\d{4})?',  # Dates
            r'\d{4}-\d{2}-\d{2}',     # Dates ISO
            r'\b\d{6,}\b',            # Numéros longs (références)
            r'REF\s*:?\s*\w+',        # Références
            r'TXN\s*:?\s*\w+',        # Transactions ID
            r'N°\s*\d+',              # Numéros de transaction
            r'\*{2,}',                # Étoiles multiples
            r'-{2,}',                 # Tirets multiples
            r'\s+',                   # Espaces multiples
        ]
        
        for pattern in patterns_to_remove:
            clean = re.sub(pattern, ' ', clean)
        
        # Normaliser les espaces
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Extraire les mots-clés significatifs (au moins 3 caractères)
        words = [w for w in clean.split() if len(w) >= 3]
        
        # Prendre les 2-3 premiers mots les plus significatifs
        if len(words) >= 2:
            return ' '.join(words[:3])
        elif words:
            return words[0]
        else:
            return "UNKNOWN"
    
    def _calculate_recurrence_score(self, count, amount_variation_pct, intervals, description, avg_amount):
        """Calculer un score de récurrence plus sophistiqué"""
        score = 0
        
        # Points pour le nombre d'occurrences
        if count >= 5:
            score += 25
        elif count >= 3:
            score += 15
        else:
            score += 5
        
        # Points pour la stabilité du montant
        if amount_variation_pct < 2:
            score += 25  # Très stable
        elif amount_variation_pct < 10:
            score += 15  # Assez stable
        elif amount_variation_pct < 25:
            score += 10  # Moyennement stable
        
        # Points pour la régularité temporelle
        if intervals:
            interval_std = np.std(intervals)
            interval_mean = np.mean(intervals)
            
            if interval_std / interval_mean < 0.2:  # Très régulier
                score += 20
            elif interval_std / interval_mean < 0.5:  # Assez régulier
                score += 10
                
            # Bonus pour les patterns mensuels/hebdomadaires
            if 25 <= interval_mean <= 35:  # ~Mensuel
                score += 15
            elif 6 <= interval_mean <= 8:   # ~Hebdomadaire  
                score += 10
        
        # Points pour les mots-clés d'abonnements
        subscription_keywords = [
            'NETFLIX', 'AMAZON', 'SPOTIFY', 'APPLE', 'MICROSOFT',
            'GOOGLE', 'ADOBE', 'DROPBOX', 'CANAL', 'ORANGE',
            'SFR', 'BOUYGUES', 'FREE', 'YOUTUBE', 'DISNEY',
            'SUBSCRIPTION', 'ABONNEMENT', 'MONTHLY', 'MENSUEL',
            'PRIME', 'PLUS', 'PREMIUM'
        ]
        
        for keyword in subscription_keywords:
            if keyword in description:
                score += 20
                break
        
        # Points pour les montants typiques d'abonnements
        if 5 <= avg_amount <= 100:  # Plage typique d'abonnements
            score += 10
        
        return score
    
    def identify_provision_candidates(self, recurring_patterns):
        """Identifier les meilleurs candidats pour conversion en provisions"""
        
        provision_candidates = []
        
        for desc, pattern in recurring_patterns.items():
            # Critères pour être un bon candidat à provision
            is_good_candidate = (
                pattern['recurrence_score'] >= 50 and
                pattern['count'] >= 3 and
                pattern['amount_stats']['variation_pct'] < 20 and
                abs(pattern['amount_stats']['mean']) >= 10  # Montant significatif
            )
            
            if is_good_candidate:
                # Déterminer le type de provision
                avg_amount = pattern['amount_stats']['mean']
                avg_interval = pattern['date_intervals']['avg_interval']
                
                if avg_interval > 0:
                    if 25 <= avg_interval <= 35:
                        frequency = 'monthly'
                        monthly_amount = abs(avg_amount)
                    elif 85 <= avg_interval <= 95:
                        frequency = 'quarterly'
                        monthly_amount = abs(avg_amount) / 3
                    elif avg_interval >= 350:
                        frequency = 'yearly'
                        monthly_amount = abs(avg_amount) / 12
                    else:
                        frequency = 'irregular'
                        monthly_amount = abs(avg_amount)
                else:
                    frequency = 'monthly'  # Par défaut
                    monthly_amount = abs(avg_amount)
                
                # Déterminer la catégorie suggérée
                category = self._suggest_category(desc)
                
                provision_candidates.append({
                    'description': desc,
                    'suggested_name': self._generate_provision_name(desc),
                    'monthly_amount': round(monthly_amount, 2),
                    'frequency': frequency,
                    'suggested_category': category,
                    'confidence_score': pattern['recurrence_score'],
                    'supporting_data': {
                        'occurrences': pattern['count'],
                        'amount_stability': f"{pattern['amount_stats']['variation_pct']:.1f}% variation",
                        'last_transaction': pattern['transactions'][-1]['description'],
                        'date_range': f"{pattern['transactions'][0]['date']} à {pattern['transactions'][-1]['date']}"
                    }
                })
        
        # Trier par score de confiance
        provision_candidates.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return provision_candidates
    
    def _suggest_category(self, description):
        """Suggérer une catégorie basée sur le libellé"""
        categories_map = {
            'LOYER': 'Logement',
            'FACTURE': 'Utilities',
            'ÉLECTRICITÉ': 'Utilities', 
            'GAZ': 'Utilities',
            'INTERNET': 'Utilities',
            'TELEPHONE': 'Utilities',
            'ASSURANCE': 'Insurance',
            'MUTUELLE': 'Insurance',
            'NETFLIX': 'Entertainment',
            'SPOTIFY': 'Entertainment',
            'AMAZON': 'Shopping',
            'COURSES': 'Groceries',
            'CARREFOUR': 'Groceries',
            'LECLERC': 'Groceries',
            'RESTAURANT': 'Dining',
            'ESSENCE': 'Transportation',
            'TOTAL': 'Transportation',
            'CINEMA': 'Entertainment',
            'SALAIRE': 'Income',
            'PHARMACIE': 'Healthcare'
        }
        
        desc_upper = description.upper()
        for keyword, category in categories_map.items():
            if keyword in desc_upper:
                return category
        
        return 'Other'
    
    def _generate_provision_name(self, description):
        """Générer un nom de provision lisible"""
        # Mappings pour des noms plus lisibles
        name_mappings = {
            'FACTURE ÉLECTRICITÉ': 'Électricité',
            'FACTURE GAZ': 'Gaz',
            'COURSES LECLERC': 'Courses alimentaires',
            'COURSES CARREFOUR': 'Courses alimentaires', 
            'RESTAURANT PIZZA': 'Restaurants',
            'CINEMA UGC': 'Sorties cinéma',
            'ESSENCE TOTAL': 'Carburant',
            'NETFLIX': 'Netflix',
            'SPOTIFY': 'Spotify',
            'AMAZON PRIME': 'Amazon Prime',
            'LOYER': 'Loyer',
            'ASSURANCE AUTO': 'Assurance automobile',
            'PHARMACIE': 'Pharmacie'
        }
        
        return name_mappings.get(description, description.title())
    
    def generate_comprehensive_report(self):
        """Générer le rapport complet avec recommandations"""
        print("=== RAPPORT D'ANALYSE COMPLET - INTELLIGENCE RÉCURRENCE ===\n")
        
        # 1. Comparaison des tables
        table_comparison = self.compare_tables()
        
        # 2. Analyse des patterns réels
        recurring_patterns = self.analyze_real_patterns()
        
        print(f"\n=== PATTERNS RÉCURRENTS IDENTIFIÉS ({len(recurring_patterns)}) ===")
        for desc, pattern in list(recurring_patterns.items())[:15]:
            print(f"\nPattern: {desc}")
            print(f"  Score de récurrence: {pattern['recurrence_score']}/100")
            print(f"  Occurrences: {pattern['count']}")
            print(f"  Montant moyen: {pattern['amount_stats']['mean']:.2f}€")
            print(f"  Stabilité: {pattern['amount_stats']['variation_pct']:.1f}% de variation")
            if pattern['date_intervals']['avg_interval'] > 0:
                print(f"  Intervalle moyen: {pattern['date_intervals']['avg_interval']:.1f} jours")
            print(f"  Période analysée: {pattern['period_days']} jours")
        
        # 3. Identification des candidats provisions
        provision_candidates = self.identify_provision_candidates(recurring_patterns)
        
        print(f"\n=== CANDIDATS PROVISIONS AUTOMATIQUES ({len(provision_candidates)}) ===")
        for candidate in provision_candidates:
            print(f"\n✓ {candidate['suggested_name']}")
            print(f"  Montant mensuel suggéré: {candidate['monthly_amount']:.2f}€")
            print(f"  Fréquence: {candidate['frequency']}")
            print(f"  Catégorie: {candidate['suggested_category']}")
            print(f"  Confiance: {candidate['confidence_score']}/100")
            print(f"  Basé sur: {candidate['supporting_data']['occurrences']} transactions")
            print(f"  Stabilité: {candidate['supporting_data']['amount_stability']}")
        
        return {
            'table_comparison': table_comparison,
            'recurring_patterns': recurring_patterns,
            'provision_candidates': provision_candidates,
            'summary': {
                'total_patterns': len(recurring_patterns),
                'high_confidence_provisions': len([c for c in provision_candidates if c['confidence_score'] >= 70]),
                'medium_confidence_provisions': len([c for c in provision_candidates if 50 <= c['confidence_score'] < 70]),
                'total_monthly_provisions': sum(c['monthly_amount'] for c in provision_candidates if c['monthly_amount'] > 0)
            }
        }
    
    def export_recommendations(self, filename="intelligence_recurrence_report.json"):
        """Exporter les recommandations"""
        report = self.generate_comprehensive_report()
        
        # Sérialiser pour JSON
        def json_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            raise TypeError(f"Object {obj} is not JSON serializable")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=json_serializer)
        
        print(f"\n=== RAPPORT EXPORTÉ VERS: {filename} ===")
        return report
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    analyzer = EnhancedTransactionAnalyzer()
    report = analyzer.export_recommendations()