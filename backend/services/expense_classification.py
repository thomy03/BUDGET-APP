"""
Expense Classification Service for Budget Famille v2.3
Intelligent classification of expenses as Fixed (Fixe) or Variable
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ExpenseType(Enum):
    FIXED = "fixe"
    VARIABLE = "variable"

@dataclass
class ClassificationResult:
    """Result of expense classification"""
    expense_type: ExpenseType
    confidence_score: float  # 0.0 to 1.0
    matching_patterns: List[str]
    reasoning: str

class ExpenseClassificationService:
    """
    Service for intelligent classification of expenses as Fixed or Variable
    
    Fixed expenses are recurring, predictable expenses like:
    - Subscriptions (Netflix, Spotify, etc.)
    - Utilities (EDF, gas, electricity)
    - Insurance, telecommunications, rent
    
    Variable expenses are occasional, unpredictable expenses like:
    - Restaurants, groceries, shopping
    - Transport (taxi, fuel for trips)
    - One-time purchases
    """
    
    def __init__(self):
        self.fixed_patterns = self._init_fixed_patterns()
        self.variable_patterns = self._init_variable_patterns()
    
    def _init_fixed_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for Fixed expenses classification"""
        return {
            'abonnements': [
                'netflix', 'spotify', 'disney', 'prime', 'amazon prime',
                'youtube', 'deezer', 'apple music', 'canal+', 'ocs',
                'molotov', 'salto', 'dailymotion', 'twitch'
            ],
            'utilities': [
                'edf', 'engie', 'total', 'direct energie', 'gdf',
                'electricite', 'gaz', 'eau', 'veolia', 'suez',
                'energie', 'kwh', 'compteur', 'facture energie'
            ],
            'telecom': [
                'orange', 'sfr', 'free', 'bouygues', 'red',
                'internet', 'mobile', 'telephone', 'fibre',
                'adsl', 'forfait', 'sosh', 'b&you'
            ],
            'insurance': [
                'assurance', 'mutuelle', 'axa', 'generali', 'maif',
                'macif', 'matmut', 'mma', 'groupama', 'allianz',
                'ag2r', 'harmonie', 'april', 'swiss life'
            ],
            'banking': [
                'banque', 'credit', 'pret', 'emprunt', 'carte',
                'cotisation', 'frais bancaire', 'commission',
                'virement', 'prelevement'
            ],
            'housing': [
                'loyer', 'charge', 'syndic', 'copropriete',
                'gardien', 'ascenseur', 'chauffage collectif',
                'eau chaude', 'ordures'
            ],
            'transport_fixed': [
                'abonnement', 'navigo', 'metro', 'bus', 'tram',
                'sncf connect', 'oui.sncf', 'velib', 'autolib',
                'parking resident', 'stationnement abonne'
            ]
        }
    
    def _init_variable_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for Variable expenses classification"""
        return {
            'food': [
                'restaurant', 'resto', 'mcdo', 'mcdonald', 'burger',
                'pizza', 'kebab', 'sushi', 'boulangerie',
                'courses', 'supermarche', 'leclerc', 'carrefour',
                'auchan', 'intermarche', 'casino', 'monoprix',
                'franprix', 'epicerie', 'marche'
            ],
            'shopping': [
                'fnac', 'darty', 'ikea', 'leroy merlin',
                'decathlon', 'zara', 'h&m', 'uniqlo',
                'amazon achat', 'cdiscount', 'vinted',
                'leboncoin', 'marketplace', 'magasin'
            ],
            'transport_variable': [
                'uber', 'taxi', 'chauffeur', 'vtc',
                'essence', 'carburant', 'station service',
                'total access', 'shell', 'bp', 'esso',
                'parking ponctuel', 'peage', 'autoroute'
            ],
            'entertainment': [
                'cinema', 'concert', 'theatre', 'musee',
                'exposition', 'parc attraction', 'zoo',
                'bowling', 'karting', 'escape game',
                'bar', 'cafe', 'pub', 'discothèque'
            ],
            'health_variable': [
                'pharmacie ponctuel', 'medecin consultation',
                'dentiste', 'kine', 'osteopathe',
                'analyses', 'radio', 'urgences'
            ],
            'travel': [
                'hotel', 'airbnb', 'booking', 'voyage',
                'avion', 'train ponctuel', 'location voiture',
                'vacances', 'week-end', 'sejour'
            ]
        }
    
    def classify_expense(self, label: str, amount: float = None, category: str = None) -> ClassificationResult:
        """
        Classify an expense as Fixed or Variable with confidence score
        
        Args:
            label: Transaction label/description
            amount: Transaction amount (optional, helps with classification)
            category: Transaction category (optional, additional context)
            
        Returns:
            ClassificationResult with type, confidence, and reasoning
        """
        if not label or not label.strip():
            return ClassificationResult(
                expense_type=ExpenseType.VARIABLE,
                confidence_score=0.1,
                matching_patterns=[],
                reasoning="Label vide - classé Variable par défaut"
            )
        
        label_normalized = self._normalize_text(label)
        category_normalized = self._normalize_text(category or "")
        
        # Check for Fixed patterns
        fixed_matches = self._find_pattern_matches(label_normalized, self.fixed_patterns)
        fixed_confidence = self._calculate_confidence(fixed_matches, label_normalized)
        
        # Check for Variable patterns
        variable_matches = self._find_pattern_matches(label_normalized, self.variable_patterns)
        variable_confidence = self._calculate_confidence(variable_matches, label_normalized)
        
        # Enhanced classification with amount and category context
        fixed_confidence = self._adjust_confidence_with_context(
            fixed_confidence, amount, category_normalized, ExpenseType.FIXED
        )
        variable_confidence = self._adjust_confidence_with_context(
            variable_confidence, amount, category_normalized, ExpenseType.VARIABLE
        )
        
        # Decision logic
        if fixed_confidence > variable_confidence and fixed_confidence >= 0.5:
            return ClassificationResult(
                expense_type=ExpenseType.FIXED,
                confidence_score=fixed_confidence,
                matching_patterns=fixed_matches,
                reasoning=f"Motifs récurrents détectés: {', '.join(fixed_matches[:3])}"
            )
        elif variable_confidence >= 0.5:
            return ClassificationResult(
                expense_type=ExpenseType.VARIABLE,
                confidence_score=variable_confidence,
                matching_patterns=variable_matches,
                reasoning=f"Motifs ponctuels détectés: {', '.join(variable_matches[:3])}"
            )
        else:
            # Default to Variable with low confidence
            reasoning = "Classification incertaine"
            if fixed_matches or variable_matches:
                reasoning += f" - Motifs partiels: {', '.join((fixed_matches + variable_matches)[:2])}"
            else:
                reasoning += " - Aucun motif spécifique détecté"
            
            return ClassificationResult(
                expense_type=ExpenseType.VARIABLE,
                confidence_score=max(0.2, max(fixed_confidence, variable_confidence)),
                matching_patterns=fixed_matches + variable_matches,
                reasoning=reasoning + " - Classé Variable par défaut"
            )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching"""
        if not text:
            return ""
        
        # Convert to lowercase and remove special characters
        normalized = text.lower()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common transaction prefixes
        prefixes_to_remove = [
            'cb', 'carte', 'paiement', 'achat', 'retrait',
            'virement', 'prelevement', 'facture'
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix + ' '):
                normalized = normalized[len(prefix):].strip()
        
        return normalized
    
    def _find_pattern_matches(self, text: str, pattern_dict: Dict[str, List[str]]) -> List[str]:
        """Find matching patterns in text"""
        matches = []
        
        for category, patterns in pattern_dict.items():
            for pattern in patterns:
                pattern_normalized = self._normalize_text(pattern)
                
                # Exact match
                if pattern_normalized in text:
                    matches.append(f"{category}:{pattern}")
                    continue
                
                # Partial match for longer patterns
                if len(pattern_normalized) > 6:
                    pattern_words = pattern_normalized.split()
                    text_words = text.split()
                    
                    # Check if most words of the pattern are in text
                    matching_words = sum(1 for word in pattern_words if word in text_words)
                    if matching_words >= len(pattern_words) * 0.7:  # 70% of words match
                        matches.append(f"{category}:{pattern}")
        
        return matches
    
    def _calculate_confidence(self, matches: List[str], text: str) -> float:
        """Calculate confidence score based on matches"""
        if not matches:
            return 0.0
        
        base_confidence = len(matches) * 0.3  # Base confidence per match
        
        # Boost confidence for exact matches
        exact_matches = sum(1 for match in matches if ':' in match and match.split(':')[1].strip() in text)
        exact_bonus = exact_matches * 0.2
        
        # Boost confidence for multiple category matches
        categories = set(match.split(':')[0] for match in matches if ':' in match)
        category_bonus = (len(categories) - 1) * 0.1 if len(categories) > 1 else 0
        
        total_confidence = min(1.0, base_confidence + exact_bonus + category_bonus)
        return round(total_confidence, 3)
    
    def _adjust_confidence_with_context(self, base_confidence: float, amount: float, 
                                       category: str, expense_type: ExpenseType) -> float:
        """Adjust confidence based on amount and category context"""
        adjusted = base_confidence
        
        if amount is not None:
            # Round amounts often indicate fixed expenses
            if expense_type == ExpenseType.FIXED:
                if amount > 0 and (amount % 10 == 0 or amount % 5 == 0):
                    adjusted += 0.1  # Round amounts are more likely fixed
                
                # Very small amounts are less likely to be fixed recurring
                if amount < 5:
                    adjusted -= 0.2
                
            elif expense_type == ExpenseType.VARIABLE:
                # Odd amounts often indicate variable expenses
                if amount > 0 and (amount % 10 != 0 and amount % 5 != 0):
                    adjusted += 0.05
        
        # Category context
        if category:
            fixed_category_indicators = ['abonnement', 'fixe', 'regulier', 'mensuel']
            variable_category_indicators = ['ponctuel', 'achat', 'divers', 'occasionnel']
            
            if expense_type == ExpenseType.FIXED:
                if any(indicator in category for indicator in fixed_category_indicators):
                    adjusted += 0.15
            else:
                if any(indicator in category for indicator in variable_category_indicators):
                    adjusted += 0.1
        
        return min(1.0, max(0.0, adjusted))
    
    def get_classification_summary(self) -> Dict[str, Any]:
        """Get summary of classification patterns and rules"""
        return {
            "fixed_categories": list(self.fixed_patterns.keys()),
            "variable_categories": list(self.variable_patterns.keys()),
            "total_fixed_patterns": sum(len(patterns) for patterns in self.fixed_patterns.values()),
            "total_variable_patterns": sum(len(patterns) for patterns in self.variable_patterns.values()),
            "default_classification": "variable",
            "confidence_threshold": 0.5,
            "classification_logic": {
                "fixed_indicators": [
                    "Recurring subscriptions (Netflix, Spotify, etc.)",
                    "Utilities (EDF, gas, electricity)",  
                    "Telecommunications (Orange, Free, etc.)",
                    "Insurance and banking fees",
                    "Round amounts suggesting fixed charges"
                ],
                "variable_indicators": [
                    "Restaurants and food purchases",
                    "Shopping and retail",
                    "Transportation (taxi, fuel)",
                    "Entertainment and leisure",
                    "Irregular amounts and one-time purchases"
                ]
            }
        }
    
    def bulk_classify_expenses(self, transactions: List[Dict]) -> List[Dict]:
        """
        Classify multiple expenses at once
        
        Args:
            transactions: List of transaction dicts with 'label', 'amount', 'category'
            
        Returns:
            List of transactions with added classification results
        """
        results = []
        
        for tx in transactions:
            label = tx.get('label', '')
            amount = tx.get('amount')
            category = tx.get('category')
            
            classification = self.classify_expense(label, amount, category)
            
            enhanced_tx = tx.copy()
            enhanced_tx.update({
                'expense_type': classification.expense_type.value,
                'classification_confidence': classification.confidence_score,
                'matching_patterns': classification.matching_patterns,
                'classification_reasoning': classification.reasoning
            })
            
            results.append(enhanced_tx)
        
        return results


def get_expense_classifier() -> ExpenseClassificationService:
    """Dependency to get expense classification service"""
    return ExpenseClassificationService()