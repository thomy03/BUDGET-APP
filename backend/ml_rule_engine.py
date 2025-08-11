#!/usr/bin/env python3
"""
ML Rule Engine pour la catégorisation automatique des transactions
Architecture hybride: Règles métier + ML avec fallback intelligent
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class MatchType(Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    REGEX = "regex"
    AMOUNT_RANGE = "amount_range"

@dataclass
class RuleResult:
    category: str
    confidence: float
    rule_id: str
    explanation: str
    matched_pattern: str

@dataclass 
class Rule:
    id: str
    priority: int  # Lower number = higher priority
    match_type: MatchType
    pattern: str
    category: str
    explanation: str
    conditions: Optional[Dict] = None  # Additional conditions
    
class TransactionRuleEngine:
    """
    Moteur de règles métier pour catégorisation automatique
    Objectif: 70% de couverture avec >90% precision
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self.merchant_patterns = {}
        self.load_default_rules()
        
    def load_default_rules(self):
        """Charge les règles par défaut basées sur l'analyse des données"""
        
        # === RÈGLES PRIORITAIRES (P1) - Très haute confiance ===
        priority_1_rules = [
            # Revenus (très spécifique)
            Rule("R001", 1, MatchType.REGEX, r"VIR.*SALAIRE|SALAIRE", 
                 "Revenus", "Virement identifié comme salaire"),
            Rule("R002", 1, MatchType.CONTAINS, "URSSAF", 
                 "Impôts & Taxes", "Prélèvement URSSAF détecté"),
            
            # Carburant (patterns forts)
            Rule("R003", 1, MatchType.REGEX, r"TOTAL\s+\d|SHELL|ESSO|STATION", 
                 "Carburant", "Station-service identifiée"),
            
            # Alimentation (patterns très spécifiques)
            Rule("R004", 1, MatchType.REGEX, r"LECLERC|CARREFOUR|MONOPRIX|AUCHAN|PICARD", 
                 "Alimentation", "Enseigne alimentaire identifiée"),
            
            # Pharmacie (très spécifique)
            Rule("R005", 1, MatchType.REGEX, r"PHARMACIE|PHIE\s", 
                 "Pharmacie et laboratoire", "Pharmacie détectée"),
        ]
        
        # === RÈGLES PRIORITÉ 2 - Haute confiance ===
        priority_2_rules = [
            # E-commerce
            Rule("R010", 2, MatchType.REGEX, r"AMAZON|AMZN", 
                 "Livres, CD/DVD, bijoux, jouets…", "Amazon détecté"),
            Rule("R011", 2, MatchType.CONTAINS, "ALIEXPRESS", 
                 "Livres, CD/DVD, bijoux, jouets…", "AliExpress détecté"),
            Rule("R012", 2, MatchType.CONTAINS, "TEMU", 
                 "Vie Quotidienne - Autres", "Temu marketplace détecté"),
            
            # Restauration
            Rule("R013", 2, MatchType.REGEX, r"DELIVEROO|UBER\s*EATS", 
                 "Restaurants, bars, discothèques…", "Livraison de repas"),
            Rule("R014", 2, MatchType.REGEX, r"RESTAURANT|BISTRO|BRASSERIE", 
                 "Restaurants, bars, discothèques…", "Établissement de restauration"),
            
            # Transport
            Rule("R015", 2, MatchType.REGEX, r"PÉAGE|COFIROUTE|FLOWBIRD", 
                 "Péages", "Péage autoroutier ou parking"),
            Rule("R016", 2, MatchType.CONTAINS, "NAVIGO", 
                 "Transport", "Pass transport public"),
            
            # Énergie/Utilities
            Rule("R017", 2, MatchType.REGEX, r"EDF|ENEDIS|GAZ", 
                 "Énergie", "Fournisseur d'énergie"),
            Rule("R018", 2, MatchType.CONTAINS, "BOUYGUES TELECOM", 
                 "Télécom", "Opérateur télécom"),
        ]
        
        # === RÈGLES PRIORITÉ 3 - Patterns généraux ===
        priority_3_rules = [
            # Types de transactions
            Rule("R020", 3, MatchType.REGEX, r"RETRAIT\s+DAB", 
                 "Retraits cash", "Retrait distributeur automatique"),
            Rule("R021", 3, MatchType.REGEX, r"VIR.*INTERNE", 
                 "Virements émis de comptes à comptes", "Virement interne"),
            
            # Patterns par montant et contexte
            Rule("R025", 3, MatchType.AMOUNT_RANGE, "", "Parking", 
                 "Petit montant parking", conditions={"amount_max": 10, "keywords": ["PARK", "FLOW"]}),
            Rule("R026", 3, MatchType.AMOUNT_RANGE, "", "Pharmacie et laboratoire", 
                 "Petit montant pharmacie", conditions={"amount_max": 30, "keywords": ["PHIE"]}),
        ]
        
        # Combinaison de toutes les règles
        all_rules = priority_1_rules + priority_2_rules + priority_3_rules
        
        for rule in all_rules:
            self.add_rule(rule)
            
        logger.info(f"Loaded {len(self.rules)} default rules")
    
    def add_rule(self, rule: Rule):
        """Ajoute une règle au moteur"""
        self.rules.append(rule)
        # Tri par priorité
        self.rules.sort(key=lambda r: r.priority)
    
    def match_rule(self, rule: Rule, label: str, amount: float, 
                   account_label: str = "") -> Optional[RuleResult]:
        """Test si une règle correspond à une transaction"""
        
        label_upper = label.upper()
        
        try:
            # Conditions spéciales si définies
            if rule.conditions:
                # Vérification montant
                if "amount_max" in rule.conditions:
                    if abs(amount) > rule.conditions["amount_max"]:
                        return None
                        
                if "amount_min" in rule.conditions:
                    if abs(amount) < rule.conditions["amount_min"]:
                        return None
                
                # Vérification keywords additionnels
                if "keywords" in rule.conditions:
                    if not any(kw in label_upper for kw in rule.conditions["keywords"]):
                        return None
            
            # Test du pattern principal
            match_found = False
            matched_text = ""
            
            if rule.match_type == MatchType.EXACT:
                match_found = label_upper == rule.pattern.upper()
                matched_text = label if match_found else ""
                
            elif rule.match_type == MatchType.CONTAINS:
                match_found = rule.pattern.upper() in label_upper
                matched_text = rule.pattern if match_found else ""
                
            elif rule.match_type == MatchType.REGEX:
                match = re.search(rule.pattern, label_upper)
                if match:
                    match_found = True
                    matched_text = match.group(0)
                    
            elif rule.match_type == MatchType.AMOUNT_RANGE:
                # Pour les règles basées sur le montant, on considère que c'est matché
                # si les conditions sont remplies (déjà vérifiées plus haut)
                match_found = True
                matched_text = f"Amount: {amount}"
            
            if match_found:
                # Calcul de la confiance basé sur la priorité et la spécificité
                confidence = self._calculate_confidence(rule, matched_text, label, amount)
                
                return RuleResult(
                    category=rule.category,
                    confidence=confidence,
                    rule_id=rule.id,
                    explanation=rule.explanation,
                    matched_pattern=matched_text
                )
                
        except Exception as e:
            logger.warning(f"Error matching rule {rule.id}: {e}")
            return None
            
        return None
    
    def _calculate_confidence(self, rule: Rule, matched_text: str, 
                            full_label: str, amount: float) -> float:
        """Calcule la confiance d'une règle matchée"""
        base_confidence = {
            1: 0.95,  # Très haute confiance
            2: 0.85,  # Haute confiance  
            3: 0.75,  # Confiance modérée
        }.get(rule.priority, 0.60)
        
        # Bonus pour correspondance exacte/forte
        if rule.match_type == MatchType.EXACT:
            base_confidence += 0.05
        
        # Bonus pour pattern long (plus spécifique)
        if len(matched_text) > 10:
            base_confidence += 0.02
            
        # Malus pour pattern très court dans long label
        if len(matched_text) < 4 and len(full_label) > 20:
            base_confidence -= 0.05
            
        return min(0.99, max(0.50, base_confidence))
    
    def categorize(self, label: str, amount: float, 
                  account_label: str = "") -> Optional[RuleResult]:
        """
        Catégorise une transaction selon les règles
        Retourne la première règle matchée (priorité la plus haute)
        """
        if not label or label.strip() == "":
            return None
            
        for rule in self.rules:
            result = self.match_rule(rule, label, amount, account_label)
            if result:
                logger.debug(f"Rule {rule.id} matched for '{label[:30]}...' -> {result.category}")
                return result
        
        logger.debug(f"No rule matched for '{label[:30]}...'")
        return None
    
    def batch_categorize(self, transactions: List[Dict]) -> List[Optional[RuleResult]]:
        """Catégorise un batch de transactions"""
        results = []
        for tx in transactions:
            result = self.categorize(
                tx.get('label', ''),
                tx.get('amount', 0.0),
                tx.get('account_label', '')
            )
            results.append(result)
        return results
    
    def get_coverage_stats(self, transactions: List[Dict]) -> Dict:
        """Calcule les statistiques de couverture des règles"""
        results = self.batch_categorize(transactions)
        
        total = len(transactions)
        matched = sum(1 for r in results if r is not None)
        high_confidence = sum(1 for r in results if r and r.confidence > 0.85)
        
        rule_usage = {}
        for result in results:
            if result:
                rule_usage[result.rule_id] = rule_usage.get(result.rule_id, 0) + 1
        
        return {
            'total_transactions': total,
            'matched_transactions': matched,
            'coverage_percentage': (matched / total * 100) if total > 0 else 0,
            'high_confidence_matches': high_confidence,
            'high_confidence_percentage': (high_confidence / total * 100) if total > 0 else 0,
            'rule_usage': rule_usage,
            'unmatched_samples': [
                tx['label'][:50] for i, tx in enumerate(transactions) 
                if i < 10 and results[i] is None
            ]
        }
    
    def export_rules(self, filepath: str):
        """Exporte les règles vers un fichier JSON"""
        rules_dict = []
        for rule in self.rules:
            rules_dict.append({
                'id': rule.id,
                'priority': rule.priority,
                'match_type': rule.match_type.value,
                'pattern': rule.pattern,
                'category': rule.category,
                'explanation': rule.explanation,
                'conditions': rule.conditions
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(rules_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Rules exported to {filepath}")

def main():
    """Test du moteur de règles"""
    import sqlite3
    import pandas as pd
    
    # Chargement des transactions test
    try:
        conn = sqlite3.connect('budget.db')
        df = pd.read_sql_query('SELECT * FROM transactions LIMIT 50', conn)
        conn.close()
        
        transactions = df.to_dict('records')
        
        # Test du rule engine
        engine = TransactionRuleEngine()
        
        print("=== TEST RULE ENGINE ===")
        print(f"Loaded {len(engine.rules)} rules")
        
        # Test de catégorisation individuelle
        test_cases = [
            ("CARTE 30/07/25 TOTAL 4 CB*8533", -45.50),
            ("VIR SALAIRE ACME Corp", 2500.00),
            ("PHARMACIE DU CENTRE", -12.80),
            ("AMAZON.FR ACHAT", -89.99),
            ("RETRAIT DAB 12/07/25", -50.00),
        ]
        
        print("\\n--- Tests individuels ---")
        for label, amount in test_cases:
            result = engine.categorize(label, amount)
            if result:
                print(f"'{label}' -> {result.category} (conf: {result.confidence:.2f}) [{result.rule_id}]")
            else:
                print(f"'{label}' -> NO MATCH")
        
        # Statistiques globales
        print("\\n--- Statistiques de couverture ---")
        stats = engine.get_coverage_stats(transactions)
        print(f"Coverage: {stats['coverage_percentage']:.1f}% ({stats['matched_transactions']}/{stats['total_transactions']})")
        print(f"High confidence: {stats['high_confidence_percentage']:.1f}%")
        
        print("\\nRègles les plus utilisées:")
        for rule_id, count in sorted(stats['rule_usage'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {rule_id}: {count} matches")
        
        if stats['unmatched_samples']:
            print("\\nÉchantillon non-matchés:")
            for sample in stats['unmatched_samples']:
                print(f"  - {sample}")
        
        # Export des règles
        engine.export_rules('ml_rules_export.json')
        
    except Exception as e:
        print(f"Erreur: {e}")
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    main()