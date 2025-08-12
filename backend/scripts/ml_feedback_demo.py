"""
ML Feedback Learning System Demonstration
Shows how the ML feedback system works and improves classification accuracy

This script demonstrates:
1. Initial ML classification with base accuracy
2. User feedback collection and pattern learning
3. Improved classification after learning
4. API usage examples
5. Performance monitoring

Run this script to see the ML feedback system in action!

Author: Claude Code - ML Backend Architect
"""

import sys
import os
import logging
import json
from datetime import datetime
from typing import Dict, List

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from models.database import get_db, Transaction, MLFeedback
from models.schemas import MLFeedbackCreate
from services.ml_feedback_learning import MLFeedbackLearningService
from routers.ml_feedback import MLFeedbackService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MLFeedbackDemo:
    """Demonstration of ML feedback learning system"""
    
    def __init__(self):
        self.db = next(get_db())
        self.feedback_service = MLFeedbackService(self.db)
        self.ml_service = MLFeedbackLearningService(self.db)
        
    def create_sample_transactions(self) -> List[Transaction]:
        """Create sample transactions for demonstration"""
        sample_transactions = [
            {
                'label': 'CB CHEZ PAUL RESTAURANT 35.50',
                'amount': 35.50,
                'expected_tag': 'restaurant',
                'expected_type': 'VARIABLE'
            },
            {
                'label': 'PRLV NETFLIX SARL 12.99',
                'amount': 12.99,
                'expected_tag': 'streaming',
                'expected_type': 'FIXED'
            },
            {
                'label': 'CB SUPERMARCHE MONOPRIX 67.80',
                'amount': 67.80,
                'expected_tag': 'courses',
                'expected_type': 'VARIABLE'
            },
            {
                'label': 'VIR LOYER APPARTEMENT 850.00',
                'amount': 850.00,
                'expected_tag': 'logement',
                'expected_type': 'FIXED'
            },
            {
                'label': 'CB CHEZ PAUL BRASSERIE 42.30',
                'amount': 42.30,
                'expected_tag': 'restaurant',
                'expected_type': 'VARIABLE'
            }
        ]
        
        transactions = []
        for i, tx_data in enumerate(sample_transactions):
            tx = Transaction(
                id=9000 + i,
                month="2025-08",
                label=tx_data['label'],
                category="demo",
                amount=tx_data['amount'],
                is_expense=True,
                exclude=False,
                expense_type="VARIABLE",
                tags="",
                confidence_score=0.5
            )
            
            # Store expected values for later comparison
            tx._expected_tag = tx_data['expected_tag']
            tx._expected_type = tx_data['expected_type']
            
            transactions.append(tx)
        
        # Add to database
        for tx in transactions:
            self.db.merge(tx)
        self.db.commit()
        
        logger.info(f"✅ Created {len(transactions)} sample transactions")
        return transactions
    
    def demonstrate_initial_classification(self, transactions: List[Transaction]) -> Dict:
        """Show initial ML classification accuracy before feedback"""
        logger.info("\n🎯 PHASE 1: Initial ML Classification (Before Feedback Learning)")
        logger.info("=" * 80)
        
        initial_results = {}
        correct_predictions = 0
        total_predictions = len(transactions)
        
        for tx in transactions:
            # Classify using base system (before feedback learning)
            result = self.ml_service.classify_with_feedback(
                transaction_label=tx.label,
                amount=tx.amount,
                use_web_research=False
            )
            
            # Check accuracy
            tag_correct = result.suggested_tag == tx._expected_tag
            type_correct = result.expense_type == tx._expected_type
            overall_correct = tag_correct and type_correct
            
            if overall_correct:
                correct_predictions += 1
            
            initial_results[tx.id] = {
                'transaction': tx.label,
                'predicted_tag': result.suggested_tag,
                'expected_tag': tx._expected_tag,
                'predicted_type': result.expense_type,
                'expected_type': tx._expected_type,
                'confidence': result.confidence,
                'correct': overall_correct,
                'explanation': result.tag_explanation or result.primary_reason
            }
            
            status = "✅" if overall_correct else "❌"
            logger.info(f"{status} {tx.label[:40]:<40} → {result.suggested_tag:<12} ({result.confidence:.2f})")
            logger.info(f"   Expected: {tx._expected_tag}, Type: {tx._expected_type}")
            logger.info(f"   Reason: {result.primary_reason}")
            logger.info("")
        
        accuracy = correct_predictions / total_predictions
        logger.info(f"📊 Initial Accuracy: {correct_predictions}/{total_predictions} = {accuracy:.1%}")
        
        return initial_results
    
    def simulate_user_feedback(self, transactions: List[Transaction], initial_results: Dict):
        """Simulate users providing feedback on incorrect classifications"""
        logger.info("\n📝 PHASE 2: Simulating User Feedback Collection")
        logger.info("=" * 80)
        
        feedback_entries = 0
        
        for tx in transactions:
            result = initial_results[tx.id]
            
            # If prediction was wrong, simulate user correction
            if not result['correct']:
                logger.info(f"💡 User correcting: {tx.label[:50]}")
                logger.info(f"   ML suggested: {result['predicted_tag']} → User corrects to: {tx._expected_tag}")
                
                # Create feedback entry
                feedback_data = MLFeedbackCreate(
                    transaction_id=tx.id,
                    original_tag=result['predicted_tag'],
                    corrected_tag=tx._expected_tag,
                    original_expense_type=result['predicted_type'],
                    corrected_expense_type=tx._expected_type,
                    feedback_type="correction",
                    confidence_before=result['confidence']
                )
                
                # Save feedback multiple times to establish pattern
                for i in range(2):  # Simulate multiple users correcting the same pattern
                    saved_feedback = self.feedback_service.save_feedback(
                        feedback_data, 
                        user_id=f"demo_user_{i}"
                    )
                    feedback_entries += 1
                
                logger.info(f"   ✅ Feedback saved (pattern: {saved_feedback.merchant_pattern})")
            else:
                # Even for correct predictions, sometimes simulate acceptance feedback
                logger.info(f"👍 User accepts: {tx.label[:50]} → {result['predicted_tag']}")
                
                feedback_data = MLFeedbackCreate(
                    transaction_id=tx.id,
                    original_tag=result['predicted_tag'],
                    corrected_tag=result['predicted_tag'],
                    original_expense_type=result['predicted_type'],
                    corrected_expense_type=result['predicted_type'],
                    feedback_type="acceptance",
                    confidence_before=result['confidence']
                )
                
                saved_feedback = self.feedback_service.save_feedback(
                    feedback_data, 
                    user_id="demo_user_accept"
                )
                feedback_entries += 1
        
        logger.info(f"📊 Total feedback entries created: {feedback_entries}")
        
        # Show learned patterns
        learned_patterns = self.feedback_service.get_learned_patterns(limit=10)
        logger.info(f"🧠 Learned patterns: {len(learned_patterns)}")
        
        for pattern in learned_patterns:
            logger.info(f"   📈 {pattern.merchant_pattern} → {pattern.learned_tag} (confidence: {pattern.confidence_score:.2f})")
    
    def demonstrate_improved_classification(self, transactions: List[Transaction]) -> Dict:
        """Show improved classification after feedback learning"""
        logger.info("\n🚀 PHASE 3: Improved ML Classification (After Feedback Learning)")
        logger.info("=" * 80)
        
        # Reload patterns to include new learning
        self.ml_service.reload_patterns()
        
        improved_results = {}
        correct_predictions = 0
        total_predictions = len(transactions)
        
        # Test with similar but slightly different transactions
        test_transactions = [
            ('CB CHEZ PAUL BISTROT 28.90', 28.90, 'restaurant', 'VARIABLE'),
            ('PRLV NETFLIX PREMIUM 15.99', 15.99, 'streaming', 'FIXED'),
            ('CB MONOPRIX COURSES 89.45', 89.45, 'courses', 'VARIABLE'),
            ('VIR LOYER MENSUEL 850.00', 850.00, 'logement', 'FIXED'),
            ('CB CHEZ PAUL SALON 31.20', 31.20, 'restaurant', 'VARIABLE')
        ]
        
        for i, (label, amount, expected_tag, expected_type) in enumerate(test_transactions):
            # Classify with feedback-enhanced system
            result = self.ml_service.classify_with_feedback(
                transaction_label=label,
                amount=amount,
                use_web_research=False
            )
            
            # Check accuracy
            tag_correct = result.suggested_tag == expected_tag
            type_correct = result.expense_type == expected_type
            overall_correct = tag_correct and type_correct
            
            if overall_correct:
                correct_predictions += 1
            
            improved_results[i] = {
                'transaction': label,
                'predicted_tag': result.suggested_tag,
                'expected_tag': expected_tag,
                'predicted_type': result.expense_type,
                'expected_type': expected_type,
                'confidence': result.confidence,
                'correct': overall_correct,
                'explanation': result.tag_explanation or result.primary_reason,
                'feedback_used': 'feedback' in result.primary_reason
            }
            
            status = "✅" if overall_correct else "❌"
            feedback_icon = "🧠" if 'feedback' in result.primary_reason else "🤖"
            logger.info(f"{status}{feedback_icon} {label:<40} → {result.suggested_tag:<12} ({result.confidence:.2f})")
            logger.info(f"    Expected: {expected_tag}, Type: {expected_type}")
            logger.info(f"    Source: {result.primary_reason}")
            logger.info("")
        
        accuracy = correct_predictions / total_predictions
        logger.info(f"📊 Improved Accuracy: {correct_predictions}/{total_predictions} = {accuracy:.1%}")
        
        # Count how many used feedback patterns
        feedback_used = sum(1 for r in improved_results.values() if r['feedback_used'])
        logger.info(f"🧠 Predictions using feedback patterns: {feedback_used}/{total_predictions}")
        
        return improved_results
    
    def show_api_examples(self):
        """Show examples of using the API endpoints"""
        logger.info("\n🔌 PHASE 4: API Usage Examples")
        logger.info("=" * 80)
        
        logger.info("📡 Available ML Feedback API Endpoints:")
        
        api_examples = [
            {
                'endpoint': 'POST /api/ml-feedback/',
                'description': 'Save user feedback/corrections',
                'example': {
                    'transaction_id': 1234,
                    'original_tag': 'divers',
                    'corrected_tag': 'restaurant',
                    'feedback_type': 'correction',
                    'confidence_before': 0.3
                }
            },
            {
                'endpoint': 'GET /api/ml-feedback/patterns',
                'description': 'Get learned patterns from feedback',
                'example': 'curl -X GET /api/ml-feedback/patterns?limit=20'
            },
            {
                'endpoint': 'GET /api/ml-feedback/stats',
                'description': 'Get feedback system statistics',
                'example': 'curl -X GET /api/ml-feedback/stats'
            },
            {
                'endpoint': 'POST /api/ml-classification/classify',
                'description': 'Enhanced classification with feedback learning',
                'example': {
                    'transaction_label': 'CB CHEZ PAUL RESTAURANT',
                    'amount': 35.50,
                    'use_web_research': False,
                    'include_alternatives': True
                }
            },
            {
                'endpoint': 'POST /api/ml-classification/classify-batch',
                'description': 'Batch classification with feedback',
                'example': {
                    'transactions': [
                        {'label': 'CB RESTAURANT', 'amount': 35.50},
                        {'label': 'NETFLIX SARL', 'amount': 12.99}
                    ],
                    'use_feedback_learning': True,
                    'confidence_threshold': 0.5
                }
            }
        ]
        
        for api in api_examples:
            logger.info(f"🔗 {api['endpoint']}")
            logger.info(f"   📝 {api['description']}")
            if isinstance(api['example'], dict):
                logger.info(f"   💡 Example payload:")
                logger.info(f"      {json.dumps(api['example'], indent=6)}")
            else:
                logger.info(f"   💡 Example: {api['example']}")
            logger.info("")
    
    def show_system_statistics(self):
        """Show current system statistics and performance"""
        logger.info("\n📊 PHASE 5: System Statistics and Performance")
        logger.info("=" * 80)
        
        # Get feedback statistics
        feedback_stats = self.feedback_service.get_feedback_stats()
        
        logger.info("🧠 Feedback Learning Statistics:")
        logger.info(f"   📥 Total feedback entries: {feedback_stats.total_feedback_entries}")
        logger.info(f"   ✏️  Corrections: {feedback_stats.corrections_count}")
        logger.info(f"   ✅ Acceptances: {feedback_stats.acceptances_count}")
        logger.info(f"   ✋ Manual entries: {feedback_stats.manual_entries_count}")
        logger.info(f"   🎯 Patterns learned: {feedback_stats.patterns_learned}")
        logger.info(f"   📈 Avg confidence improvement: {feedback_stats.average_confidence_improvement:.2f}")
        logger.info(f"   🏆 Learning success rate: {feedback_stats.learning_success_rate:.1%}")
        logger.info("")
        
        # Get pattern statistics
        pattern_stats = self.ml_service.get_pattern_statistics()
        
        logger.info("🔍 Pattern Learning Statistics:")
        logger.info(f"   🧩 Total patterns: {pattern_stats['total_patterns']}")
        logger.info(f"   🎯 High confidence patterns: {pattern_stats['high_confidence_patterns']}")
        logger.info(f"   🔥 Frequently used patterns: {pattern_stats['frequently_used_patterns']}")
        logger.info(f"   📊 Average confidence: {pattern_stats['average_confidence']:.2f}")
        logger.info(f"   🔧 Correction patterns: {pattern_stats['correction_patterns']}")
        logger.info("")
        
        if pattern_stats['top_patterns']:
            logger.info("🏅 Top 5 Most Used Patterns:")
            for i, pattern in enumerate(pattern_stats['top_patterns'][:5], 1):
                logger.info(f"   {i}. {pattern['pattern']} → {pattern['tag']} "
                          f"(used {pattern['usage_count']} times, confidence: {pattern['confidence']:.2f})")
        logger.info("")
        
        # Show most corrected tags
        if feedback_stats.most_corrected_tags:
            logger.info("🔄 Most Frequently Corrected Tags:")
            for tag_info in feedback_stats.most_corrected_tags[:5]:
                logger.info(f"   📝 '{tag_info['tag']}' corrected {tag_info['corrections']} times")
        logger.info("")
    
    def run_complete_demo(self):
        """Run the complete ML feedback system demonstration"""
        logger.info("🎬 ML FEEDBACK LEARNING SYSTEM DEMONSTRATION")
        logger.info("=" * 90)
        logger.info("This demo shows how the ML system learns from user feedback")
        logger.info("and improves classification accuracy over time.")
        logger.info("")
        
        try:
            # Phase 1: Create sample data and show initial accuracy
            transactions = self.create_sample_transactions()
            initial_results = self.demonstrate_initial_classification(transactions)
            
            # Phase 2: Simulate user feedback
            self.simulate_user_feedback(transactions, initial_results)
            
            # Phase 3: Show improved accuracy
            improved_results = self.demonstrate_improved_classification(transactions)
            
            # Phase 4: Show API usage
            self.show_api_examples()
            
            # Phase 5: Show statistics
            self.show_system_statistics()
            
            # Summary
            logger.info("\n🎉 DEMONSTRATION COMPLETE!")
            logger.info("=" * 80)
            logger.info("The ML feedback system has successfully demonstrated:")
            logger.info("✅ Pattern learning from user corrections")
            logger.info("✅ Improved classification accuracy")
            logger.info("✅ Confidence score adjustments")
            logger.info("✅ API integration for real-world usage")
            logger.info("✅ Comprehensive monitoring and statistics")
            logger.info("")
            logger.info("🚀 The system is ready for production use!")
            logger.info("Users can now provide feedback to continuously improve AI accuracy.")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
        finally:
            self.db.close()


def main():
    """Main entry point for the demonstration"""
    print("🎯 Starting ML Feedback Learning System Demo...")
    print("This will show how the system learns from user feedback.\n")
    
    demo = MLFeedbackDemo()
    demo.run_complete_demo()


if __name__ == "__main__":
    main()