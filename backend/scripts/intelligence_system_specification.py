#!/usr/bin/env python3
"""
Spécification complète du système d'intelligence pour la détection automatique
des transactions récurrentes et leur conversion en provisions
"""

import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class RecurrenceRule:
    """Règle de détection de récurrence"""
    name: str
    min_occurrences: int
    max_amount_variation_pct: float
    keywords: List[str]
    amount_range: Tuple[float, float]  # (min, max) en euros
    interval_pattern: str  # 'monthly', 'weekly', 'quarterly', 'yearly', 'irregular'
    score_bonus: int
    category_hint: str

@dataclass
class ProvisionSuggestion:
    """Structure d'une suggestion de provision"""
    id: str
    transaction_pattern: str
    suggested_name: str
    monthly_amount: float
    frequency: str
    category: str
    confidence_score: int
    supporting_transactions: List[Dict]
    auto_convert_threshold: int  # Score minimum pour conversion automatique
    user_validation_required: bool
    tags: List[str]

class IntelligenceSystemSpec:
    """Spécification complète du système d'intelligence récurrente"""
    
    def __init__(self):
        self.recurrence_rules = self._define_recurrence_rules()
        self.scoring_criteria = self._define_scoring_criteria()
        self.database_schema = self._define_database_schema()
        self.api_endpoints = self._define_api_endpoints()
        
    def _define_recurrence_rules(self) -> List[RecurrenceRule]:
        """Définir les règles de détection des patterns récurrents"""
        return [
            # Abonnements de streaming
            RecurrenceRule(
                name="streaming_subscriptions",
                min_occurrences=2,
                max_amount_variation_pct=5.0,
                keywords=["NETFLIX", "SPOTIFY", "DISNEY", "AMAZON PRIME", "YOUTUBE", "APPLE MUSIC"],
                amount_range=(4.99, 49.99),
                interval_pattern="monthly",
                score_bonus=25,
                category_hint="Entertainment"
            ),
            
            # Télécommunications
            RecurrenceRule(
                name="telecom",
                min_occurrences=2,
                max_amount_variation_pct=10.0,
                keywords=["ORANGE", "SFR", "BOUYGUES", "FREE", "INTERNET", "MOBILE", "TELEPHONE"],
                amount_range=(15.0, 150.0),
                interval_pattern="monthly",
                score_bonus=20,
                category_hint="Utilities"
            ),
            
            # Utilities (électricité, gaz, eau)
            RecurrenceRule(
                name="utilities",
                min_occurrences=2,
                max_amount_variation_pct=25.0,
                keywords=["ÉLECTRICITÉ", "ELECTRICITE", "GAZ", "EAU", "ENGIE", "EDF", "VEOLIA"],
                amount_range=(30.0, 300.0),
                interval_pattern="monthly",
                score_bonus=20,
                category_hint="Utilities"
            ),
            
            # Assurances
            RecurrenceRule(
                name="insurance",
                min_occurrences=2,
                max_amount_variation_pct=5.0,
                keywords=["ASSURANCE", "MUTUELLE", "MAAF", "MACIF", "GROUPAMA"],
                amount_range=(20.0, 500.0),
                interval_pattern="monthly",
                score_bonus=25,
                category_hint="Insurance"
            ),
            
            # Logement (loyer, copropriété)
            RecurrenceRule(
                name="housing",
                min_occurrences=2,
                max_amount_variation_pct=2.0,
                keywords=["LOYER", "COPROPRIETE", "SYNDIC", "CHARGES"],
                amount_range=(300.0, 3000.0),
                interval_pattern="monthly",
                score_bonus=30,
                category_hint="Logement"
            ),
            
            # Transport (carburant récurrent)
            RecurrenceRule(
                name="fuel_recurring",
                min_occurrences=3,
                max_amount_variation_pct=30.0,
                keywords=["TOTAL", "SHELL", "ESSO", "BP", "CARBURANT", "ESSENCE"],
                amount_range=(40.0, 150.0),
                interval_pattern="weekly",
                score_bonus=15,
                category_hint="Transportation"
            ),
            
            # Courses alimentaires régulières
            RecurrenceRule(
                name="grocery_regular",
                min_occurrences=4,
                max_amount_variation_pct=40.0,
                keywords=["LECLERC", "CARREFOUR", "AUCHAN", "CASINO", "MONOPRIX", "FRANPRIX"],
                amount_range=(30.0, 200.0),
                interval_pattern="weekly",
                score_bonus=10,
                category_hint="Groceries"
            ),
            
            # Pharmacie régulière
            RecurrenceRule(
                name="pharmacy_regular",
                min_occurrences=3,
                max_amount_variation_pct=50.0,
                keywords=["PHARMACIE"],
                amount_range=(5.0, 100.0),
                interval_pattern="irregular",
                score_bonus=10,
                category_hint="Healthcare"
            ),
            
            # Services cloud/software
            RecurrenceRule(
                name="cloud_services",
                min_occurrences=2,
                max_amount_variation_pct=5.0,
                keywords=["DROPBOX", "GOOGLE", "MICROSOFT", "ADOBE", "OFFICE", "DRIVE"],
                amount_range=(2.99, 99.99),
                interval_pattern="monthly",
                score_bonus=25,
                category_hint="Software"
            )
        ]
    
    def _define_scoring_criteria(self) -> Dict[str, Any]:
        """Définir les critères de scoring pour l'IA"""
        return {
            "base_scoring": {
                "occurrence_points": {
                    2: 10,
                    3: 15,
                    4: 20,
                    5: 25,
                    "6+": 30
                },
                "amount_stability_points": {
                    "0-2%": 30,      # Très stable
                    "2-5%": 25,      # Stable
                    "5-15%": 20,     # Assez stable
                    "15-30%": 15,    # Moyennement stable
                    "30-50%": 10,    # Peu stable
                    "50%+": 5        # Instable
                },
                "temporal_regularity_points": {
                    "perfect_monthly": 25,    # 28-32 jours, écart type < 2
                    "good_monthly": 20,       # 25-35 jours, écart type < 5
                    "weekly": 15,             # 6-8 jours
                    "quarterly": 15,          # 85-95 jours
                    "irregular_consistent": 10, # Irrégulier mais cohérent
                    "irregular": 5            # Complètement irrégulier
                }
            },
            "thresholds": {
                "auto_convert": 80,           # Conversion automatique sans validation
                "high_confidence": 70,        # Suggestion avec haute confiance
                "medium_confidence": 50,      # Suggestion avec validation obligatoire
                "low_confidence": 30,         # Mention seulement
                "ignore": 29                  # Ignorer
            },
            "minimum_requirements": {
                "min_occurrences": 2,
                "min_amount": 5.0,           # Montant minimum en euros
                "max_variation_pct": 100.0,  # Variation maximum acceptable
                "min_period_days": 7         # Période minimum d'observation
            }
        }
    
    def _define_database_schema(self) -> Dict[str, Any]:
        """Définir le schéma de base de données pour le système d'intelligence"""
        return {
            "new_tables": {
                "recurring_patterns": {
                    "description": "Stockage des patterns récurrents détectés",
                    "columns": {
                        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                        "pattern_hash": "VARCHAR(64) UNIQUE NOT NULL", # Hash unique du pattern
                        "pattern_name": "VARCHAR(200) NOT NULL",
                        "description_pattern": "VARCHAR(500)",
                        "occurrence_count": "INTEGER NOT NULL",
                        "first_detected": "DATETIME NOT NULL",
                        "last_updated": "DATETIME NOT NULL",
                        "average_amount": "DECIMAL(10,2)",
                        "amount_variation_pct": "DECIMAL(5,2)",
                        "average_interval_days": "INTEGER",
                        "interval_stability": "DECIMAL(5,2)",
                        "confidence_score": "INTEGER NOT NULL",
                        "category_hint": "VARCHAR(50)",
                        "keywords_matched": "TEXT", # JSON array
                        "is_active": "BOOLEAN DEFAULT TRUE",
                        "user_validated": "BOOLEAN DEFAULT FALSE",
                        "auto_converted": "BOOLEAN DEFAULT FALSE"
                    },
                    "indexes": [
                        "CREATE INDEX idx_recurring_patterns_score ON recurring_patterns(confidence_score DESC)",
                        "CREATE INDEX idx_recurring_patterns_active ON recurring_patterns(is_active, confidence_score DESC)"
                    ]
                },
                
                "provision_suggestions": {
                    "description": "Suggestions de provisions basées sur les patterns",
                    "columns": {
                        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                        "pattern_id": "INTEGER REFERENCES recurring_patterns(id)",
                        "suggested_name": "VARCHAR(200) NOT NULL",
                        "suggested_monthly_amount": "DECIMAL(10,2) NOT NULL",
                        "suggested_frequency": "VARCHAR(20) NOT NULL", # monthly, quarterly, yearly
                        "suggested_category": "VARCHAR(50)",
                        "confidence_score": "INTEGER NOT NULL",
                        "user_action": "VARCHAR(20)", # pending, accepted, rejected, modified
                        "created_at": "DATETIME NOT NULL",
                        "acted_at": "DATETIME",
                        "created_provision_id": "INTEGER", # Référence vers la provision créée
                        "rejection_reason": "VARCHAR(500)",
                        "supporting_transaction_ids": "TEXT" # JSON array des IDs de transactions
                    },
                    "indexes": [
                        "CREATE INDEX idx_provision_suggestions_pending ON provision_suggestions(user_action, confidence_score DESC)",
                        "CREATE INDEX idx_provision_suggestions_pattern ON provision_suggestions(pattern_id)"
                    ]
                },
                
                "intelligence_config": {
                    "description": "Configuration du système d'intelligence",
                    "columns": {
                        "id": "INTEGER PRIMARY KEY",
                        "auto_convert_threshold": "INTEGER DEFAULT 80",
                        "suggestion_threshold": "INTEGER DEFAULT 50",
                        "analysis_period_days": "INTEGER DEFAULT 365",
                        "min_occurrences": "INTEGER DEFAULT 2",
                        "notification_enabled": "BOOLEAN DEFAULT TRUE",
                        "auto_categorization": "BOOLEAN DEFAULT TRUE",
                        "updated_at": "DATETIME NOT NULL"
                    }
                }
            },
            
            "table_modifications": {
                "transactions": {
                    "new_columns": [
                        "ADD COLUMN intelligence_processed BOOLEAN DEFAULT FALSE",
                        "ADD COLUMN pattern_id INTEGER REFERENCES recurring_patterns(id)"
                    ]
                },
                "custom_provisions": {
                    "new_columns": [
                        "ADD COLUMN created_from_intelligence BOOLEAN DEFAULT FALSE",
                        "ADD COLUMN source_pattern_id INTEGER REFERENCES recurring_patterns(id)"
                    ]
                }
            }
        }
    
    def _define_api_endpoints(self) -> Dict[str, Any]:
        """Définir les endpoints API pour le système d'intelligence"""
        return {
            "analysis": {
                "POST /api/intelligence/analyze": {
                    "description": "Déclencher l'analyse des patterns récurrents",
                    "parameters": {
                        "period_days": "int (optional, default: 365)",
                        "min_confidence": "int (optional, default: 30)",
                        "force_reanalysis": "bool (optional, default: false)"
                    },
                    "response": {
                        "patterns_detected": "int",
                        "suggestions_created": "int",
                        "processing_time_ms": "int"
                    }
                },
                
                "GET /api/intelligence/patterns": {
                    "description": "Récupérer les patterns détectés",
                    "parameters": {
                        "confidence_min": "int (optional)",
                        "active_only": "bool (optional, default: true)",
                        "limit": "int (optional, default: 50)"
                    },
                    "response": "List[RecurringPattern]"
                }
            },
            
            "suggestions": {
                "GET /api/intelligence/suggestions": {
                    "description": "Récupérer les suggestions de provisions",
                    "parameters": {
                        "status": "str (pending, accepted, rejected, all)",
                        "confidence_min": "int (optional)"
                    },
                    "response": "List[ProvisionSuggestion]"
                },
                
                "POST /api/intelligence/suggestions/{id}/accept": {
                    "description": "Accepter une suggestion et créer la provision",
                    "parameters": {
                        "modifications": "dict (optional) - Modifications à apporter"
                    },
                    "response": {
                        "provision_created": "ProvisionDetails",
                        "suggestion_updated": "bool"
                    }
                },
                
                "POST /api/intelligence/suggestions/{id}/reject": {
                    "description": "Rejeter une suggestion",
                    "parameters": {
                        "reason": "str (optional)"
                    },
                    "response": {"status": "success"}
                }
            },
            
            "configuration": {
                "GET /api/intelligence/config": {
                    "description": "Récupérer la configuration du système",
                    "response": "IntelligenceConfig"
                },
                
                "PUT /api/intelligence/config": {
                    "description": "Mettre à jour la configuration",
                    "parameters": {
                        "auto_convert_threshold": "int (optional)",
                        "suggestion_threshold": "int (optional)",
                        "notification_enabled": "bool (optional)"
                    },
                    "response": "IntelligenceConfig"
                }
            }
        }
    
    def generate_implementation_recommendations(self) -> Dict[str, Any]:
        """Générer les recommandations d'implémentation"""
        return {
            "phase1_core_detection": {
                "priority": "HIGH",
                "estimated_effort": "2-3 semaines",
                "components": [
                    "Création des tables de base de données",
                    "Implémentation de l'algorithme de détection des patterns",
                    "Système de scoring basique",
                    "API endpoints de base (analyze, patterns, suggestions)"
                ],
                "acceptance_criteria": [
                    "Détection automatique des patterns avec score >= 50",
                    "Stockage persistant des patterns détectés",
                    "API fonctionnelle pour récupérer les suggestions"
                ]
            },
            
            "phase2_intelligence_advanced": {
                "priority": "MEDIUM",
                "estimated_effort": "3-4 semaines", 
                "components": [
                    "Amélioration de l'algorithme de scoring",
                    "Détection des catégories automatique",
                    "Interface utilisateur pour validation des suggestions",
                    "Système de notifications",
                    "Conversion automatique (seuil configurable)"
                ],
                "acceptance_criteria": [
                    "Interface utilisateur complète",
                    "Conversion automatique des provisions haute confiance",
                    "Système de notifications fonctionnel"
                ]
            },
            
            "phase3_machine_learning": {
                "priority": "LOW",
                "estimated_effort": "4-6 semaines",
                "components": [
                    "Apprentissage automatique basé sur les actions utilisateur",
                    "Amélioration des patterns de détection par ML",
                    "Prédiction des montants futurs",
                    "Détection d'anomalies dans les patterns"
                ],
                "acceptance_criteria": [
                    "Amélioration continue de la précision",
                    "Détection d'anomalies dans les habitudes",
                    "Suggestions personnalisées par utilisateur"
                ]
            }
        }
    
    def generate_kpis(self) -> Dict[str, Any]:
        """Définir les KPIs pour mesurer l'efficacité du système"""
        return {
            "effectiveness_metrics": {
                "pattern_detection_accuracy": {
                    "description": "Pourcentage de patterns correctement identifiés",
                    "calculation": "(Patterns validés par utilisateur / Total patterns suggérés) * 100",
                    "target": "> 70%"
                },
                "suggestion_acceptance_rate": {
                    "description": "Taux d'acceptance des suggestions de provisions",
                    "calculation": "(Suggestions acceptées / Total suggestions) * 100",
                    "target": "> 60%"
                },
                "false_positive_rate": {
                    "description": "Taux de faux positifs dans les détections",
                    "calculation": "(Patterns rejetés / Total patterns) * 100",
                    "target": "< 20%"
                },
                "automation_efficiency": {
                    "description": "Pourcentage de provisions créées automatiquement",
                    "calculation": "(Provisions auto-créées / Total provisions créées via IA) * 100",
                    "target": "> 40%"
                }
            },
            
            "user_experience_metrics": {
                "time_to_decision": {
                    "description": "Temps moyen pour traiter une suggestion",
                    "target": "< 2 minutes par suggestion"
                },
                "user_satisfaction_score": {
                    "description": "Score de satisfaction utilisateur (1-5)",
                    "target": "> 4.0"
                },
                "feature_adoption_rate": {
                    "description": "Pourcentage d'utilisateurs utilisant l'IA",
                    "target": "> 80%"
                }
            },
            
            "technical_metrics": {
                "analysis_performance": {
                    "description": "Temps d'analyse pour 1000 transactions",
                    "target": "< 5 secondes"
                },
                "memory_usage": {
                    "description": "Utilisation mémoire pour l'analyse",
                    "target": "< 100 MB"
                },
                "api_response_time": {
                    "description": "Temps de réponse API moyen",
                    "target": "< 500ms"
                }
            }
        }
    
    def export_complete_specification(self, filename="intelligence_system_specification.json"):
        """Exporter la spécification complète"""
        spec = {
            "overview": {
                "name": "Système d'Intelligence de Récurrence",
                "version": "1.0",
                "description": "Système automatique de détection des transactions récurrentes et de suggestion de provisions",
                "created_at": datetime.now().isoformat()
            },
            "recurrence_rules": [asdict(rule) for rule in self.recurrence_rules],
            "scoring_criteria": self.scoring_criteria,
            "database_schema": self.database_schema,
            "api_endpoints": self.api_endpoints,
            "implementation_plan": self.generate_implementation_recommendations(),
            "kpis": self.generate_kpis(),
            "sample_use_cases": self._generate_use_cases()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        
        print(f"Spécification complète exportée vers: {filename}")
        return spec
    
    def _generate_use_cases(self) -> List[Dict[str, Any]]:
        """Générer des cas d'usage exemples"""
        return [
            {
                "name": "Détection Netflix",
                "scenario": "Utilisateur paie Netflix 15.99€ chaque mois depuis 3 mois",
                "expected_detection": {
                    "pattern": "NETFLIX",
                    "confidence_score": 85,
                    "suggested_provision": {
                        "name": "Netflix",
                        "monthly_amount": 15.99,
                        "category": "Entertainment"
                    },
                    "action": "Auto-conversion (score > 80)"
                }
            },
            {
                "name": "Courses variables mais régulières",
                "scenario": "Courses Leclerc: 45€, 67€, 52€, 48€ chaque semaine",
                "expected_detection": {
                    "pattern": "COURSES LECLERC",
                    "confidence_score": 65,
                    "suggested_provision": {
                        "name": "Courses alimentaires",
                        "monthly_amount": 224.0,  # Moyenne hebdo * 4
                        "category": "Groceries"
                    },
                    "action": "Suggestion avec validation utilisateur"
                }
            },
            {
                "name": "Facture électricité trimestrielle",
                "scenario": "EDF: 150€ tous les 3 mois",
                "expected_detection": {
                    "pattern": "FACTURE ÉLECTRICITÉ",
                    "confidence_score": 75,
                    "suggested_provision": {
                        "name": "Électricité",
                        "monthly_amount": 50.0,  # 150/3
                        "category": "Utilities"
                    },
                    "action": "Suggestion haute confiance"
                }
            }
        ]

if __name__ == "__main__":
    spec_system = IntelligenceSystemSpec()
    specification = spec_system.export_complete_specification()
    
    print("\n=== RÉSUMÉ DE LA SPÉCIFICATION ===")
    print(f"• Règles de détection définies: {len(spec_system.recurrence_rules)}")
    print(f"• Endpoints API spécifiés: {sum(len(v) for v in spec_system.api_endpoints.values())}")
    print(f"• Nouvelles tables DB: {len(spec_system.database_schema['new_tables'])}")
    print(f"• Phases d'implémentation: {len(specification['implementation_plan'])}")
    print(f"• KPIs définis: {sum(len(v) for v in specification['kpis'].values())}")
    print(f"• Cas d'usage: {len(specification['sample_use_cases'])}")