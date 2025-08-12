#!/usr/bin/env python3
"""
Test complet du système de recherche web pour enrichissement automatique des transactions

Ce script teste tous les composants du système de recherche web :
- Service de recherche web (WebResearchService)
- Base de connaissances marchands (MerchantKnowledgeService)
- API de recherche (research router)
- Intégration avec les transactions

OBJECTIF : Démontrer le fonctionnement complet du système d'intelligence pour
          l'enrichissement automatique des transactions
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import des modules du système
sys.path.append('.')
from services.web_research_service import WebResearchService, get_merchant_from_transaction_label
from services.merchant_knowledge_service import MerchantKnowledgeService
from models.database import get_db, Transaction, MerchantKnowledgeBase
from sqlalchemy.orm import Session


class WebResearchSystemTester:
    """Testeur complet du système de recherche web"""
    
    def __init__(self):
        self.research_service = None
        self.knowledge_service = MerchantKnowledgeService()
        self.test_results = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        
        # Transactions de test réalistes
        self.test_transactions = [
            "CB CARREFOUR VILLENEUVE 15/12 17H45",
            "VIR NETFLIX ABONNEMENT MENSUEL",
            "PRLV EDF FACTURE ELECTRICITE",
            "CB PHARMACIE CENTRALE PARIS 12/12",
            "CB TOTAL ACCESS LYON A6 14/12",
            "VIR SFR MOBILE FORFAIT",
            "CB BOULANGER ELECTROMENAGER",
            "PRLV AXA ASSURANCE AUTO",
            "CB RESTAURANT LE PETIT PARIS",
            "CB FNAC LIVRE COMMANDE WEB",
            "VIR SPOTIFY PREMIUM FAMILLE",
            "CB LECLERC COURSES SEMAINE",
            "PRLV ORANGE INTERNET FIBRE",
            "CB ZARA VETEMENTS FEMME",
            "CB DECATHLON SPORT OUTDOOR"
        ]
    
    async def setup(self):
        """Initialisation du testeur"""
        self.research_service = WebResearchService()
        await self.research_service.__aenter__()
        logger.info("🚀 Système de test initialisé")
    
    async def cleanup(self):
        """Nettoyage du testeur"""
        if self.research_service:
            await self.research_service.__aexit__(None, None, None)
        logger.info("🧹 Nettoyage terminé")
    
    def add_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Ajouter un résultat de test"""
        self.test_results['total_tests'] += 1
        if success:
            self.test_results['successful_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
        
        self.test_results['test_details'].append({
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details
        })
    
    async def test_merchant_name_extraction(self):
        """Test de l'extraction des noms de marchands"""
        logger.info("\n📝 Test 1: Extraction des noms de marchands")
        
        success_count = 0
        total_count = len(self.test_transactions)
        
        results = []
        for transaction_label in self.test_transactions:
            merchant_name = get_merchant_from_transaction_label(transaction_label)
            
            result = {
                'transaction_label': transaction_label,
                'extracted_merchant': merchant_name,
                'extraction_successful': bool(merchant_name and len(merchant_name) > 0)
            }
            
            results.append(result)
            
            if result['extraction_successful']:
                success_count += 1
                logger.info(f"  ✅ '{transaction_label[:50]}...' → '{merchant_name}'")
            else:
                logger.warning(f"  ❌ '{transaction_label[:50]}...' → Aucun marchand extrait")
        
        success_rate = (success_count / total_count) * 100
        test_success = success_rate >= 80  # 80% de réussite minimum
        
        self.add_test_result(
            "merchant_name_extraction",
            test_success,
            {
                'success_rate': success_rate,
                'successful_extractions': success_count,
                'total_transactions': total_count,
                'results': results
            }
        )
        
        logger.info(f"📊 Taux de réussite extraction: {success_rate:.1f}% ({success_count}/{total_count})")
        return test_success
    
    async def test_web_research_service(self):
        """Test du service de recherche web"""
        logger.info("\n🔍 Test 2: Service de recherche web")
        
        # Marchands de test avec différents types
        test_merchants = [
            "CARREFOUR VILLENEUVE",
            "NETFLIX",
            "PHARMACIE CENTRALE",
            "TOTAL ACCESS",
            "RESTAURANT LE PETIT PARIS"
        ]
        
        research_results = []
        successful_research = 0
        
        for merchant_name in test_merchants:
            try:
                logger.info(f"  🔬 Recherche: {merchant_name}")
                start_time = time.time()
                
                merchant_info = await self.research_service.research_merchant(merchant_name)
                
                research_time = (time.time() - start_time) * 1000
                
                result = {
                    'merchant_name': merchant_name,
                    'business_type': merchant_info.business_type,
                    'confidence_score': merchant_info.confidence_score,
                    'suggested_expense_type': merchant_info.suggested_expense_type,
                    'suggested_tags': merchant_info.suggested_tags,
                    'data_sources': merchant_info.data_sources,
                    'research_duration_ms': research_time,
                    'classification_successful': merchant_info.business_type is not None
                }
                
                research_results.append(result)
                
                if result['classification_successful']:
                    successful_research += 1
                    logger.info(f"    ✅ Type: {merchant_info.business_type}, "
                              f"Confiance: {merchant_info.confidence_score:.2f}, "
                              f"Durée: {research_time:.0f}ms")
                else:
                    logger.info(f"    ⚠️ Classification échouée, Confiance: {merchant_info.confidence_score:.2f}")
                
                # Délai entre recherches pour éviter le rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"    ❌ Erreur recherche {merchant_name}: {e}")
                research_results.append({
                    'merchant_name': merchant_name,
                    'error': str(e),
                    'classification_successful': False
                })
        
        success_rate = (successful_research / len(test_merchants)) * 100
        test_success = success_rate >= 60  # 60% de réussite minimum (service web peut être limité)
        
        self.add_test_result(
            "web_research_service",
            test_success,
            {
                'success_rate': success_rate,
                'successful_research': successful_research,
                'total_merchants': len(test_merchants),
                'research_results': research_results
            }
        )
        
        logger.info(f"📊 Taux de réussite recherche: {success_rate:.1f}% ({successful_research}/{len(test_merchants)})")
        return test_success
    
    def test_knowledge_base_operations(self):
        """Test des opérations de base de connaissances"""
        logger.info("\n🧠 Test 3: Base de connaissances marchands")
        
        db_session = next(get_db())
        
        try:
            # Test création d'entrée marchand
            test_merchant = self.knowledge_service.create_merchant_entry(
                db=db_session,
                merchant_name="TEST RESTAURANT DEMO",
                business_type="restaurant",
                category="fast_food",
                expense_type="VARIABLE",
                confidence_score=0.85,
                source="test_system",
                additional_data={
                    'city': 'Paris',
                    'suggested_tags': 'alimentation,restaurant,test'
                }
            )
            
            logger.info(f"  ✅ Création marchand: ID {test_merchant.id}")
            
            # Test recherche fuzzy
            fuzzy_results = self.knowledge_service.search_merchant_fuzzy(
                db=db_session,
                merchant_name="TEST RESTAURANT",
                confidence_threshold=0.5
            )
            
            logger.info(f"  ✅ Recherche fuzzy: {len(fuzzy_results)} résultats")
            
            # Test mise à jour
            updated_merchant = self.knowledge_service.update_merchant_entry(
                db=db_session,
                merchant_id=test_merchant.id,
                accuracy_rating=0.95,
                is_verified=True
            )
            
            logger.info(f"  ✅ Mise à jour marchand: Vérifié")
            
            # Test statistiques
            stats = self.knowledge_service.get_knowledge_base_stats(db=db_session)
            
            logger.info(f"  ✅ Statistiques: {stats.get('total_merchants', 0)} marchands totaux")
            
            # Nettoyage du test
            updated_merchant.is_active = False
            db_session.commit()
            
            test_success = True
            
            self.add_test_result(
                "knowledge_base_operations",
                test_success,
                {
                    'merchant_created': test_merchant.id,
                    'fuzzy_search_results': len(fuzzy_results),
                    'stats': stats
                }
            )
            
        except Exception as e:
            logger.error(f"  ❌ Erreur base de connaissances: {e}")
            test_success = False
            self.add_test_result(
                "knowledge_base_operations",
                False,
                {'error': str(e)}
            )
        
        finally:
            db_session.close()
        
        return test_success
    
    async def test_transaction_enrichment_pipeline(self):
        """Test du pipeline complet d'enrichissement des transactions"""
        logger.info("\n🔄 Test 4: Pipeline d'enrichissement complet")
        
        # Simulation d'enrichissement de transactions
        enrichment_results = []
        successful_enrichments = 0
        
        sample_transactions = self.test_transactions[:5]  # 5 premiers pour économiser du temps
        
        for i, transaction_label in enumerate(sample_transactions):
            try:
                # Extraction du marchand
                merchant_name = get_merchant_from_transaction_label(transaction_label)
                
                if not merchant_name:
                    logger.warning(f"  ⚠️ Transaction {i+1}: Pas de marchand extrait")
                    continue
                
                # Recherche d'informations
                merchant_info = await self.research_service.research_merchant(merchant_name)
                
                # Simulation d'application des suggestions
                enrichment = {
                    'transaction_label': transaction_label,
                    'merchant_name': merchant_name,
                    'business_type': merchant_info.business_type,
                    'suggested_expense_type': merchant_info.suggested_expense_type,
                    'suggested_tags': merchant_info.suggested_tags,
                    'confidence_score': merchant_info.confidence_score,
                    'enrichment_successful': merchant_info.business_type is not None
                }
                
                enrichment_results.append(enrichment)
                
                if enrichment['enrichment_successful']:
                    successful_enrichments += 1
                    logger.info(f"  ✅ Transaction {i+1}: {merchant_name} → {merchant_info.business_type} "
                              f"({merchant_info.suggested_expense_type})")
                else:
                    logger.info(f"  ⚠️ Transaction {i+1}: {merchant_name} → Classification partielle")
                
                await asyncio.sleep(0.5)  # Délai court entre traitements
                
            except Exception as e:
                logger.error(f"  ❌ Transaction {i+1}: Erreur {e}")
                enrichment_results.append({
                    'transaction_label': transaction_label,
                    'error': str(e),
                    'enrichment_successful': False
                })
        
        success_rate = (successful_enrichments / len(sample_transactions)) * 100
        test_success = success_rate >= 50  # 50% minimum pour pipeline complet
        
        self.add_test_result(
            "transaction_enrichment_pipeline",
            test_success,
            {
                'success_rate': success_rate,
                'successful_enrichments': successful_enrichments,
                'total_transactions': len(sample_transactions),
                'enrichment_results': enrichment_results
            }
        )
        
        logger.info(f"📊 Taux de réussite enrichissement: {success_rate:.1f}% ({successful_enrichments}/{len(sample_transactions)})")
        return test_success
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        logger.info("🚀 DÉBUT DES TESTS DU SYSTÈME DE RECHERCHE WEB")
        logger.info("=" * 60)
        
        await self.setup()
        
        try:
            # Exécution des tests
            test1 = await self.test_merchant_name_extraction()
            test2 = await self.test_web_research_service()
            test3 = self.test_knowledge_base_operations()
            test4 = await self.test_transaction_enrichment_pipeline()
            
        finally:
            await self.cleanup()
        
        # Génération du rapport final
        self.generate_final_report()
    
    def generate_final_report(self):
        """Générer le rapport final"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 RAPPORT FINAL DU SYSTÈME DE RECHERCHE WEB")
        logger.info("=" * 60)
        
        total_tests = self.test_results['total_tests']
        successful_tests = self.test_results['successful_tests']
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"Tests exécutés: {total_tests}")
        logger.info(f"Tests réussis: {successful_tests}")
        logger.info(f"Tests échoués: {self.test_results['failed_tests']}")
        logger.info(f"Taux de réussite global: {success_rate:.1f}%")
        
        # Détails par test
        logger.info("\nDétails des tests:")
        for test in self.test_results['test_details']:
            status = "✅ RÉUSSI" if test['success'] else "❌ ÉCHEC"
            logger.info(f"  {status} - {test['test_name']}")
        
        # Évaluation globale
        if success_rate >= 75:
            logger.info("\n🎉 SYSTÈME DE RECHERCHE WEB: OPÉRATIONNEL")
            logger.info("Le système est prêt pour l'enrichissement automatique des transactions")
        elif success_rate >= 50:
            logger.info("\n⚠️ SYSTÈME DE RECHERCHE WEB: FONCTIONNEL AVEC LIMITATIONS")
            logger.info("Le système fonctionne mais nécessite des améliorations")
        else:
            logger.info("\n❌ SYSTÈME DE RECHERCHE WEB: NÉCESSITE DES CORRECTIONS")
            logger.info("Le système présente des problèmes critiques à résoudre")
        
        # Sauvegarde du rapport
        report_data = {
            'test_execution_date': datetime.now().isoformat(),
            'system_status': 'operational' if success_rate >= 75 else 'limited' if success_rate >= 50 else 'needs_fixes',
            'overall_success_rate': success_rate,
            'test_summary': self.test_results,
            'recommendations': self.generate_recommendations()
        }
        
        with open('web_research_system_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n💾 Rapport détaillé sauvegardé: web_research_system_test_report.json")
    
    def generate_recommendations(self):
        """Générer des recommandations basées sur les résultats de test"""
        recommendations = []
        
        for test in self.test_results['test_details']:
            if not test['success']:
                if test['test_name'] == 'merchant_name_extraction':
                    recommendations.append("Améliorer les patterns d'extraction des noms de marchands")
                elif test['test_name'] == 'web_research_service':
                    recommendations.append("Optimiser les sources de données web ou ajuster les timeouts")
                elif test['test_name'] == 'knowledge_base_operations':
                    recommendations.append("Vérifier la configuration de la base de données")
                elif test['test_name'] == 'transaction_enrichment_pipeline':
                    recommendations.append("Améliorer la robustesse du pipeline d'enrichissement")
        
        if not recommendations:
            recommendations.append("Système fonctionnel - continuer le monitoring en production")
        
        return recommendations


async def main():
    """Fonction principale"""
    tester = WebResearchSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())