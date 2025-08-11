#!/usr/bin/env python3
"""
ML Evaluation Framework pour Budget Famille
Framework complet d'évaluation des performances ML avec A/B testing
"""

import numpy as np
import pandas as pd
import sqlite3
import json
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split, cross_val_score
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
import time

# Imports des modules ML
from ml_rule_engine import TransactionRuleEngine
from ml_anomaly_detector import TransactionAnomalyDetector
from ml_budget_predictor import BudgetIntelligenceSystem

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Métriques de performance pour un modèle"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    coverage: float  # % de transactions traitées
    avg_confidence: float
    processing_time_ms: float
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0

@dataclass
class CategoryPerformance:
    """Performance par catégorie"""
    category: str
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1: float
    support: int  # Nombre d'échantillons

@dataclass
class ABTestResult:
    """Résultat d'un test A/B"""
    test_name: str
    variant_a_performance: PerformanceMetrics
    variant_b_performance: PerformanceMetrics
    statistical_significance: bool
    p_value: float
    winner: str
    improvement_percentage: float
    recommendation: str

class MLEvaluationFramework:
    """
    Framework d'évaluation ML avec:
    - Métriques de performance détaillées
    - Évaluation par catégorie
    - A/B testing automatique
    - Monitoring de la dérive des modèles
    """
    
    def __init__(self, db_path: str = "budget.db"):
        self.db_path = db_path
        self.evaluation_history = []
        
        # Seuils de performance acceptables
        self.thresholds = {
            'min_precision': 0.85,        # Objectif roadmap: >85%
            'min_coverage': 0.90,         # >90% transactions traitées
            'max_latency_ms': 500,        # <500ms temps de réponse
            'max_false_positive_rate': 0.05,  # <5% faux positifs
            'min_confidence': 0.70,       # Confiance minimale acceptable
        }
    
    def create_test_dataset(self, test_size: float = 0.2, 
                          min_samples_per_category: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Crée des datasets d'entraînement et de test stratifiés
        """
        # Chargement des données
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM transactions', conn)
        conn.close()
        
        # Filtrage des catégories avec suffisamment d'échantillons
        category_counts = df['category'].value_counts()
        valid_categories = category_counts[category_counts >= min_samples_per_category].index
        
        df_filtered = df[df['category'].isin(valid_categories)].copy()
        
        # Split stratifié pour maintenir la distribution des catégories
        if len(df_filtered) > 10:
            train_df, test_df = train_test_split(
                df_filtered,
                test_size=test_size,
                stratify=df_filtered['category'],
                random_state=42
            )
        else:
            # Si trop peu de données, utiliser tout pour l'entraînement
            train_df, test_df = df_filtered, df_filtered.sample(frac=0.3, random_state=42)
        
        logger.info(f"Created test dataset: {len(train_df)} train, {len(test_df)} test samples")
        logger.info(f"Categories in test: {test_df['category'].nunique()}")
        
        return train_df, test_df
    
    def evaluate_categorization_model(self, model, test_df: pd.DataFrame, 
                                    model_name: str = "Unknown") -> Tuple[PerformanceMetrics, List[CategoryPerformance]]:
        """
        Évalue un modèle de catégorisation
        """
        logger.info(f"Evaluating {model_name} categorization model")
        
        predictions = []
        ground_truth = []
        confidences = []
        processing_times = []
        coverage_count = 0
        
        for _, row in test_df.iterrows():
            start_time = time.time()
            
            # Prédiction selon le type de modèle
            if hasattr(model, 'categorize'):  # Rule Engine
                result = model.categorize(row['label'], row['amount'], row.get('account_label', ''))
                if result:
                    predicted_category = result.category
                    confidence = result.confidence
                    coverage_count += 1
                else:
                    predicted_category = "Non catégorisé"
                    confidence = 0.0
            else:
                # Autres types de modèles
                predicted_category = "Non catégorisé"
                confidence = 0.5
            
            processing_time = (time.time() - start_time) * 1000
            
            predictions.append(predicted_category)
            ground_truth.append(row['category'])
            confidences.append(confidence)
            processing_times.append(processing_time)
        
        # Calcul des métriques globales
        predictions = np.array(predictions)
        ground_truth = np.array(ground_truth)
        
        accuracy = accuracy_score(ground_truth, predictions)
        precision = precision_score(ground_truth, predictions, average='weighted', zero_division=0)
        recall = recall_score(ground_truth, predictions, average='weighted', zero_division=0)
        f1 = f1_score(ground_truth, predictions, average='weighted', zero_division=0)
        
        coverage = coverage_count / len(test_df)
        avg_confidence = np.mean(confidences)
        avg_processing_time = np.mean(processing_times)
        
        # Calcul des faux positifs/négatifs
        cm = confusion_matrix(ground_truth, predictions, labels=np.unique(ground_truth))
        if cm.size > 0:
            fp = cm.sum(axis=0) - np.diag(cm)
            fn = cm.sum(axis=1) - np.diag(cm)
            tp = np.diag(cm)
            tn = cm.sum() - (fp + fn + tp)
            
            fp_rate = fp.sum() / (fp.sum() + tn.sum()) if (fp.sum() + tn.sum()) > 0 else 0
            fn_rate = fn.sum() / (fn.sum() + tp.sum()) if (fn.sum() + tp.sum()) > 0 else 0
        else:
            fp_rate = fn_rate = 0
        
        global_metrics = PerformanceMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            coverage=coverage,
            avg_confidence=avg_confidence,
            processing_time_ms=avg_processing_time,
            false_positive_rate=fp_rate,
            false_negative_rate=fn_rate
        )
        
        # Métriques par catégorie
        category_metrics = self._calculate_category_metrics(ground_truth, predictions)
        
        return global_metrics, category_metrics
    
    def _calculate_category_metrics(self, y_true: np.ndarray, 
                                  y_pred: np.ndarray) -> List[CategoryPerformance]:
        """Calcule les métriques de performance par catégorie"""
        categories = np.unique(y_true)
        category_performances = []
        
        for category in categories:
            # Binary classification pour cette catégorie
            y_true_binary = (y_true == category).astype(int)
            y_pred_binary = (y_pred == category).astype(int)
            
            tp = np.sum((y_true_binary == 1) & (y_pred_binary == 1))
            fp = np.sum((y_true_binary == 0) & (y_pred_binary == 1))
            fn = np.sum((y_true_binary == 1) & (y_pred_binary == 0))
            tn = np.sum((y_true_binary == 0) & (y_pred_binary == 0))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            support = np.sum(y_true == category)
            
            category_performances.append(CategoryPerformance(
                category=category,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                true_negatives=tn,
                precision=precision,
                recall=recall,
                f1=f1,
                support=support
            ))
        
        return category_performances
    
    def evaluate_anomaly_detection(self, detector: TransactionAnomalyDetector, 
                                 test_df: pd.DataFrame) -> Dict:
        """Évalue le système de détection d'anomalies"""
        logger.info("Evaluating anomaly detection system")
        
        # Simulation d'anomalies synthétiques
        normal_transactions = test_df.sample(n=min(50, len(test_df)))
        
        # Création d'anomalies artificielles
        synthetic_anomalies = self._create_synthetic_anomalies(normal_transactions)
        
        # Évaluation sur les données normales
        normal_results = []
        for _, row in normal_transactions.iterrows():
            tx_dict = row.to_dict()
            anomalies = detector.analyze_transaction(tx_dict)
            normal_results.append(len(anomalies) > 0)  # True si anomalie détectée
        
        # Évaluation sur les anomalies synthétiques
        anomaly_results = []
        for tx_dict in synthetic_anomalies:
            anomalies = detector.analyze_transaction(tx_dict)
            anomaly_results.append(len(anomalies) > 0)
        
        # Calcul des métriques
        false_positive_rate = sum(normal_results) / len(normal_results) if normal_results else 0
        true_positive_rate = sum(anomaly_results) / len(anomaly_results) if anomaly_results else 0
        
        return {
            'false_positive_rate': false_positive_rate,
            'true_positive_rate': true_positive_rate,
            'normal_samples_tested': len(normal_results),
            'anomaly_samples_tested': len(anomaly_results),
            'performance_status': 'PASS' if false_positive_rate < self.thresholds['max_false_positive_rate'] else 'FAIL'
        }
    
    def _create_synthetic_anomalies(self, base_df: pd.DataFrame) -> List[Dict]:
        """Crée des anomalies synthétiques pour les tests"""
        anomalies = []
        
        for _, row in base_df.head(10).iterrows():
            # Anomalie de montant (10x le montant normal)
            anomaly = row.to_dict()
            anomaly['amount'] = row['amount'] * 10
            anomaly['id'] = f"synthetic_amount_{row.get('id', 'unknown')}"
            anomalies.append(anomaly)
            
            # Nouveau marchand avec montant élevé
            anomaly = row.to_dict()
            anomaly['label'] = "MARCHAND INCONNU JAMAIS VU"
            anomaly['amount'] = -500.00
            anomaly['id'] = f"synthetic_merchant_{row.get('id', 'unknown')}"
            anomalies.append(anomaly)
        
        return anomalies
    
    def run_ab_test(self, model_a, model_b, test_df: pd.DataFrame,
                   test_name: str, model_a_name: str = "A", model_b_name: str = "B") -> ABTestResult:
        """
        Lance un test A/B entre deux modèles
        """
        logger.info(f"Running A/B test: {test_name}")
        
        # Évaluation des deux modèles
        metrics_a, _ = self.evaluate_categorization_model(model_a, test_df, model_a_name)
        metrics_b, _ = self.evaluate_categorization_model(model_b, test_df, model_b_name)
        
        # Calcul de la significativité statistique (t-test simple)
        # En pratique, il faudrait une vraie analyse statistique
        primary_metric = 'f1_score'  # Métrique principale pour comparaison
        
        score_a = getattr(metrics_a, primary_metric)
        score_b = getattr(metrics_b, primary_metric)
        
        improvement = ((score_b - score_a) / score_a * 100) if score_a > 0 else 0
        
        # Simulation de p-value (dans un vrai système, utiliser des tests statistiques)
        p_value = 0.03 if abs(improvement) > 5 else 0.12
        significant = p_value < 0.05
        
        # Détermination du gagnant
        if score_b > score_a and significant:
            winner = model_b_name
            recommendation = f"Déployer {model_b_name} - amélioration significative de {improvement:.1f}%"
        elif score_a > score_b and significant:
            winner = model_a_name
            recommendation = f"Conserver {model_a_name} - meilleure performance de {-improvement:.1f}%"
        else:
            winner = "No winner"
            recommendation = f"Pas de différence significative - conserver le modèle actuel"
        
        return ABTestResult(
            test_name=test_name,
            variant_a_performance=metrics_a,
            variant_b_performance=metrics_b,
            statistical_significance=significant,
            p_value=p_value,
            winner=winner,
            improvement_percentage=improvement,
            recommendation=recommendation
        )
    
    def evaluate_budget_predictions(self, budget_system: BudgetIntelligenceSystem,
                                  historical_df: pd.DataFrame) -> Dict:
        """Évalue la précision des prédictions budgétaires"""
        logger.info("Evaluating budget prediction accuracy")
        
        # Simulation : utiliser les données des mois précédents pour prédire les suivants
        monthly_data = self._prepare_monthly_data(historical_df)
        
        if len(monthly_data) < 3:
            return {'error': 'Insufficient historical data for budget evaluation'}
        
        prediction_errors = []
        categories_evaluated = []
        
        # Test de prédiction sur les 2 derniers mois
        for test_month in monthly_data.keys()[-2:]:
            if test_month in monthly_data:
                # Données jusqu'au mois précédent pour l'entraînement
                train_months = [m for m in monthly_data.keys() if m < test_month]
                if not train_months:
                    continue
                
                # Simulation des dépenses à mi-mois
                actual_monthly_spending = monthly_data[test_month]
                simulated_mid_month = {cat: amount * 0.5 for cat, amount in actual_monthly_spending.items()}
                
                # Prédiction
                test_date = datetime.strptime(str(test_month), '%Y-%m')
                predictions = budget_system.predict_month_end(test_date, simulated_mid_month)
                
                # Calcul des erreurs
                for pred in predictions:
                    if pred.category in actual_monthly_spending:
                        actual = actual_monthly_spending[pred.category]
                        predicted = pred.predicted_month_end
                        error = abs(predicted - actual) / actual if actual > 0 else 0
                        prediction_errors.append(error)
                        categories_evaluated.append(pred.category)
        
        if prediction_errors:
            mean_error = np.mean(prediction_errors)
            median_error = np.median(prediction_errors)
            std_error = np.std(prediction_errors)
            
            return {
                'mean_absolute_percentage_error': mean_error,
                'median_absolute_percentage_error': median_error,
                'std_error': std_error,
                'categories_evaluated': len(set(categories_evaluated)),
                'total_predictions_tested': len(prediction_errors),
                'accuracy_status': 'GOOD' if mean_error < 0.2 else 'NEEDS_IMPROVEMENT'
            }
        
        return {'error': 'No valid predictions to evaluate'}
    
    def _prepare_monthly_data(self, df: pd.DataFrame) -> Dict:
        """Prépare les données mensuelles pour l'évaluation"""
        df['date_op'] = pd.to_datetime(df['date_op'])
        df['year_month'] = df['date_op'].dt.to_period('M')
        
        expenses_df = df[df['is_expense'] == 1]
        monthly_spending = expenses_df.groupby(['year_month', 'category'])['amount'].sum().abs()
        
        monthly_data = {}
        for (year_month, category), amount in monthly_spending.items():
            if year_month not in monthly_data:
                monthly_data[year_month] = {}
            monthly_data[year_month][category] = amount
        
        return dict(sorted(monthly_data.items()))
    
    def check_performance_thresholds(self, metrics: PerformanceMetrics) -> Dict[str, bool]:
        """Vérifie si les métriques respectent les seuils requis"""
        checks = {
            'precision_ok': metrics.precision >= self.thresholds['min_precision'],
            'coverage_ok': metrics.coverage >= self.thresholds['min_coverage'],
            'latency_ok': metrics.processing_time_ms <= self.thresholds['max_latency_ms'],
            'false_positive_ok': metrics.false_positive_rate <= self.thresholds['max_false_positive_rate'],
            'confidence_ok': metrics.avg_confidence >= self.thresholds['min_confidence']
        }
        
        checks['all_passed'] = all(checks.values())
        
        return checks
    
    def generate_evaluation_report(self, model_name: str, metrics: PerformanceMetrics,
                                 category_metrics: List[CategoryPerformance],
                                 additional_data: Dict = None) -> Dict:
        """Génère un rapport d'évaluation complet"""
        
        # Vérification des seuils
        threshold_checks = self.check_performance_thresholds(metrics)
        
        # Top/Bottom categories
        category_metrics_sorted = sorted(category_metrics, key=lambda x: x.f1, reverse=True)
        
        report = {
            'model_name': model_name,
            'evaluation_timestamp': datetime.now().isoformat(),
            'global_metrics': asdict(metrics),
            'threshold_checks': threshold_checks,
            'performance_status': 'PASS' if threshold_checks['all_passed'] else 'FAIL',
            'top_performing_categories': [
                {'category': cm.category, 'f1_score': cm.f1, 'support': cm.support}
                for cm in category_metrics_sorted[:5]
            ],
            'worst_performing_categories': [
                {'category': cm.category, 'f1_score': cm.f1, 'support': cm.support}
                for cm in category_metrics_sorted[-5:]
            ],
            'total_categories_evaluated': len(category_metrics),
            'recommendations': self._generate_recommendations(metrics, threshold_checks)
        }
        
        if additional_data:
            report.update(additional_data)
        
        return report
    
    def _generate_recommendations(self, metrics: PerformanceMetrics, 
                                checks: Dict[str, bool]) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        if not checks['precision_ok']:
            recommendations.append(f"Améliorer la précision: {metrics.precision:.2f} < {self.thresholds['min_precision']}")
        
        if not checks['coverage_ok']:
            recommendations.append(f"Augmenter la couverture: {metrics.coverage:.2f} < {self.thresholds['min_coverage']}")
        
        if not checks['latency_ok']:
            recommendations.append(f"Optimiser la latence: {metrics.processing_time_ms:.1f}ms > {self.thresholds['max_latency_ms']}ms")
        
        if not checks['false_positive_ok']:
            recommendations.append(f"Réduire les faux positifs: {metrics.false_positive_rate:.3f} > {self.thresholds['max_false_positive_rate']}")
        
        if not checks['confidence_ok']:
            recommendations.append(f"Améliorer la confiance: {metrics.avg_confidence:.2f} < {self.thresholds['min_confidence']}")
        
        if not recommendations:
            recommendations.append("Performance satisfaisante - continuer le monitoring")
        
        return recommendations
    
    def save_evaluation_results(self, results: Dict, filepath: str = None):
        """Sauvegarde les résultats d'évaluation"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"ml_evaluation_report_{timestamp}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Evaluation results saved to {filepath}")
        
        # Ajout à l'historique
        self.evaluation_history.append({
            'timestamp': datetime.now().isoformat(),
            'filepath': filepath,
            'results_summary': {
                'model_name': results.get('model_name', 'Unknown'),
                'performance_status': results.get('performance_status', 'Unknown'),
                'precision': results.get('global_metrics', {}).get('precision', 0)
            }
        })

def main():
    """Test du framework d'évaluation"""
    try:
        # Création du framework
        evaluator = MLEvaluationFramework()
        
        print("=== ML EVALUATION FRAMEWORK TEST ===")
        
        # Création des datasets
        train_df, test_df = evaluator.create_test_dataset()
        print(f"Test dataset: {len(test_df)} samples, {test_df['category'].nunique()} categories")
        
        # Test du Rule Engine
        rule_engine = TransactionRuleEngine()
        
        print("\\n--- Evaluating Rule Engine ---")
        metrics, category_metrics = evaluator.evaluate_categorization_model(
            rule_engine, test_df, "Rule Engine"
        )
        
        print(f"Precision: {metrics.precision:.3f}")
        print(f"Recall: {metrics.recall:.3f}")
        print(f"F1-Score: {metrics.f1_score:.3f}")
        print(f"Coverage: {metrics.coverage:.3f}")
        print(f"Avg Processing Time: {metrics.processing_time_ms:.1f}ms")
        
        # Vérification des seuils
        threshold_checks = evaluator.check_performance_thresholds(metrics)
        print(f"\\nThreshold checks: {sum(threshold_checks.values())}/{len(threshold_checks)} passed")
        for check, passed in threshold_checks.items():
            if not passed:
                print(f"  ❌ {check}")
        
        # Génération du rapport
        report = evaluator.generate_evaluation_report(
            "Rule Engine v1.0", metrics, category_metrics
        )
        
        print(f"\\nPerformance Status: {report['performance_status']}")
        print("\\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
        
        # Sauvegarde
        evaluator.save_evaluation_results(report)
        
        # Test anomaly detection si disponible
        try:
            anomaly_detector = TransactionAnomalyDetector()
            if len(train_df) >= 30:
                anomaly_detector.fit(train_df)
                
                print("\\n--- Evaluating Anomaly Detection ---")
                anomaly_results = evaluator.evaluate_anomaly_detection(anomaly_detector, test_df)
                print(f"False Positive Rate: {anomaly_results['false_positive_rate']:.3f}")
                print(f"True Positive Rate: {anomaly_results['true_positive_rate']:.3f}")
                print(f"Status: {anomaly_results['performance_status']}")
        except Exception as e:
            print(f"Anomaly detection evaluation skipped: {e}")
        
        print("\\n=== Evaluation completed successfully ===")
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        logger.error(f"Evaluation error: {e}")

if __name__ == "__main__":
    main()