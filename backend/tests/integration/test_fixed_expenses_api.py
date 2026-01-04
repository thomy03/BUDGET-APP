#!/usr/bin/env python3
"""
Script de test pour l'API des dépenses fixes
Teste tous les endpoints CRUD : POST, GET, PUT, DELETE
"""
import requests
import json
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de l'API
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/fixed-expenses"

# Données de test
test_user = {
    "username": "testuser",
    "password": "testpass123"
}

test_expense = {
    "label": "Test Loyer Appartement",
    "amount": 1200.50,
    "freq": "mensuel",
    "description": "Loyer mensuel de l'appartement principal",
    "category": "logement",
    "active": True,
    "split_mode": "50/50",
    "split1": 50.0,
    "split2": 50.0
}

def get_auth_token():
    """Obtenir un token d'authentification"""
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            data={
                "username": test_user["username"],
                "password": test_user["password"]
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data["access_token"]
        else:
            logger.error(f"Échec d'authentification: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de l'authentification: {str(e)}")
        return None

def test_api_endpoints():
    """Tester tous les endpoints de l'API des dépenses fixes"""
    logger.info("🚀 Début des tests de l'API des dépenses fixes")
    
    # 1. Authentification
    logger.info("📝 Test d'authentification...")
    token = get_auth_token()
    if not token:
        logger.error("❌ Impossible d'obtenir un token d'authentification")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    logger.info("✅ Authentification réussie")
    
    created_expense_id = None
    
    try:
        # 2. Test GET /api/fixed-expenses (liste vide)
        logger.info("📋 Test GET /api/fixed-expenses (liste initiale)...")
        response = requests.get(API_BASE, headers=headers)
        if response.status_code == 200:
            expenses = response.json()
            logger.info(f"✅ Liste obtenue: {len(expenses)} dépenses existantes")
        else:
            logger.error(f"❌ Échec GET liste: {response.status_code} - {response.text}")
            return False
        
        # 3. Test POST /api/fixed-expenses (création)
        logger.info("➕ Test POST /api/fixed-expenses (création)...")
        response = requests.post(API_BASE, headers=headers, json=test_expense)
        if response.status_code == 201:
            created_expense = response.json()
            created_expense_id = created_expense["id"]
            logger.info(f"✅ Dépense créée avec l'ID: {created_expense_id}")
            logger.info(f"   Label: {created_expense['label']}")
            logger.info(f"   Montant: {created_expense['amount']}€")
            logger.info(f"   Fréquence: {created_expense['freq']}")
            logger.info(f"   Description: {created_expense['description']}")
        else:
            logger.error(f"❌ Échec POST création: {response.status_code} - {response.text}")
            return False
        
        # 4. Test GET /api/fixed-expenses/{id} (lecture spécifique)
        logger.info(f"🔍 Test GET /api/fixed-expenses/{created_expense_id} (lecture spécifique)...")
        response = requests.get(f"{API_BASE}/{created_expense_id}", headers=headers)
        if response.status_code == 200:
            expense = response.json()
            logger.info(f"✅ Dépense récupérée: {expense['label']}")
            logger.info(f"   Créée le: {expense.get('created_at', 'N/A')}")
            logger.info(f"   Modifiée le: {expense.get('updated_at', 'N/A')}")
        else:
            logger.error(f"❌ Échec GET spécifique: {response.status_code} - {response.text}")
            return False
        
        # 5. Test PUT /api/fixed-expenses/{id} (modification)
        logger.info(f"✏️ Test PUT /api/fixed-expenses/{created_expense_id} (modification)...")
        updated_expense = test_expense.copy()
        updated_expense["label"] = "Test Loyer Appartement - Modifié"
        updated_expense["amount"] = 1300.00
        updated_expense["description"] = "Loyer mensuel de l'appartement principal - Augmentation"
        
        response = requests.put(f"{API_BASE}/{created_expense_id}", headers=headers, json=updated_expense)
        if response.status_code == 200:
            modified_expense = response.json()
            logger.info(f"✅ Dépense modifiée: {modified_expense['label']}")
            logger.info(f"   Nouveau montant: {modified_expense['amount']}€")
            logger.info(f"   Nouvelle description: {modified_expense['description']}")
        else:
            logger.error(f"❌ Échec PUT modification: {response.status_code} - {response.text}")
            return False
        
        # 6. Test GET /api/fixed-expenses (vérification après modification)
        logger.info("📋 Test GET /api/fixed-expenses (après modification)...")
        response = requests.get(API_BASE, headers=headers)
        if response.status_code == 200:
            expenses = response.json()
            logger.info(f"✅ Liste mise à jour: {len(expenses)} dépenses")
            for expense in expenses:
                if expense["id"] == created_expense_id:
                    logger.info(f"   Dépense modifiée trouvée: {expense['label']} - {expense['amount']}€")
        else:
            logger.error(f"❌ Échec GET après modification: {response.status_code} - {response.text}")
        
        # 7. Test GET /api/fixed-expenses/stats/summary (statistiques)
        logger.info("📊 Test GET /api/fixed-expenses/stats/summary (statistiques)...")
        response = requests.get(f"{API_BASE}/stats/summary", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            logger.info("✅ Statistiques obtenues:")
            logger.info(f"   Total dépenses: {stats['summary']['total_expenses']}")
            logger.info(f"   Équivalent mensuel global: {stats['summary']['global_monthly_equivalent']}€")
            logger.info(f"   Nombre de catégories: {stats['summary']['categories_count']}")
            for category_stat in stats["by_category"]:
                logger.info(f"   - {category_stat['category']}: {category_stat['count']} dépenses, {category_stat['monthly_equivalent']}€/mois")
        else:
            logger.error(f"❌ Échec GET statistiques: {response.status_code} - {response.text}")
        
        # 8. Test filtrage par catégorie
        logger.info("🏷️ Test filtrage par catégorie (logement)...")
        response = requests.get(f"{API_BASE}?category=logement", headers=headers)
        if response.status_code == 200:
            filtered_expenses = response.json()
            logger.info(f"✅ Dépenses de logement: {len(filtered_expenses)}")
            for expense in filtered_expenses:
                logger.info(f"   - {expense['label']}: {expense['amount']}€ ({expense['freq']})")
        else:
            logger.error(f"❌ Échec filtrage: {response.status_code} - {response.text}")
        
        # 9. Test DELETE /api/fixed-expenses/{id} (suppression)
        logger.info(f"🗑️ Test DELETE /api/fixed-expenses/{created_expense_id} (suppression)...")
        response = requests.delete(f"{API_BASE}/{created_expense_id}", headers=headers)
        if response.status_code == 200:
            delete_result = response.json()
            logger.info(f"✅ Dépense supprimée: {delete_result['message']}")
            logger.info(f"   Mappings supprimés: {delete_result['related_mappings_deleted']}")
        else:
            logger.error(f"❌ Échec DELETE: {response.status_code} - {response.text}")
            return False
        
        # 10. Vérification de la suppression
        logger.info(f"🔍 Vérification de la suppression...")
        response = requests.get(f"{API_BASE}/{created_expense_id}", headers=headers)
        if response.status_code == 404:
            logger.info("✅ Dépense correctement supprimée (404 attendu)")
        else:
            logger.error(f"❌ La dépense existe encore: {response.status_code}")
            return False
        
        # 11. Test des erreurs
        logger.info("⚠️ Test des cas d'erreur...")
        
        # Test montant négatif
        invalid_expense = test_expense.copy()
        invalid_expense["amount"] = -100.0
        response = requests.post(API_BASE, headers=headers, json=invalid_expense)
        if response.status_code == 400:
            logger.info("✅ Validation montant négatif: erreur 400 attendue")
        else:
            logger.warning(f"⚠️ Validation montant: {response.status_code} (400 attendu)")
        
        # Test ID inexistant
        response = requests.get(f"{API_BASE}/99999", headers=headers)
        if response.status_code == 404:
            logger.info("✅ ID inexistant: erreur 404 attendue")
        else:
            logger.warning(f"⚠️ ID inexistant: {response.status_code} (404 attendu)")
        
        logger.info("🎉 Tous les tests sont terminés avec succès!")
        return True
        
    except Exception as e:
        logger.error(f"💥 Erreur pendant les tests: {str(e)}")
        
        # Nettoyage en cas d'erreur
        if created_expense_id:
            logger.info(f"🧹 Nettoyage: suppression de la dépense {created_expense_id}")
            try:
                requests.delete(f"{API_BASE}/{created_expense_id}", headers=headers)
            except:
                pass
        
        return False

def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("🧪 TEST DE L'API DES DÉPENSES FIXES")
    print("=" * 60)
    print(f"🌐 URL de base: {API_BASE}")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    success = test_api_endpoints()
    
    print("=" * 60)
    if success:
        print("✅ RÉSULTAT: Tous les tests ont réussi!")
    else:
        print("❌ RÉSULTAT: Certains tests ont échoué!")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())