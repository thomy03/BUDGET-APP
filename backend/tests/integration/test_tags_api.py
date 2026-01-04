#!/usr/bin/env python3
"""
Test de l'API des tags
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8743"

def test_list_tags():
    """Test de la liste des tags"""
    print("\n🔍 Test de l'endpoint GET /api/tags")
    
    response = requests.get(f"{BASE_URL}/api/tags")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Endpoint accessible")
        print(f"📊 Statistiques:")
        print(f"  - Total des tags: {data.get('total_count', 0)}")
        print(f"  - Tags les plus utilisés: {data.get('stats', {}).get('most_used_tags', [])}")
        
        if 'tags' in data and data['tags']:
            print(f"\n📋 Liste des tags ({len(data['tags'])} tags):")
            for tag in data['tags'][:5]:  # Afficher les 5 premiers
                print(f"  - {tag['name']}:")
                print(f"    • Transactions: {tag.get('transaction_count', 0)}")
                print(f"    • Montant total: {tag.get('total_amount', 0):.2f}€")
                print(f"    • Type: {tag.get('expense_type', 'N/A')}")
                if tag.get('last_used'):
                    print(f"    • Dernière utilisation: {tag['last_used']}")
        else:
            print("⚠️ Aucun tag trouvé")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
    
    return response.status_code == 200

def test_delete_tag(tag_name):
    """Test de suppression d'un tag"""
    print(f"\n🗑️ Test de suppression du tag '{tag_name}'")
    
    # Essayer de supprimer avec le nouvel endpoint
    response = requests.delete(
        f"{BASE_URL}/api/tags/by-name/{tag_name}",
        params={"cascade": "true"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Tag supprimé avec succès")
        if 'details' in data:
            details = data['details']
            print(f"  - Transactions modifiées: {details.get('removed_from_transactions', 0)}")
            print(f"  - Mappings supprimés: {details.get('removed_mappings', 0)}")
    elif response.status_code == 404:
        print(f"⚠️ Tag '{tag_name}' introuvable")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
    
    return response.status_code in [200, 404]

def test_tags_summary():
    """Test du résumé des tags"""
    print("\n📊 Test de l'endpoint GET /api/tags-summary")
    
    # Tester avec le mois actuel
    current_month = datetime.now().strftime("%Y-%m")
    response = requests.get(
        f"{BASE_URL}/api/tags-summary",
        params={"month": current_month}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Résumé pour le mois {current_month}")
        print(f"  - Transactions taguées: {data.get('total_tagged_transactions', 0)}")
        
        tags = data.get('tags', {})
        if tags:
            print(f"  - Nombre de tags uniques: {len(tags)}")
            for tag_name, stats in list(tags.items())[:3]:  # Afficher les 3 premiers
                print(f"    • {tag_name}: {stats.get('count', 0)} transactions, {stats.get('total_amount', 0):.2f}€")
        else:
            print("  - Aucun tag pour ce mois")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
    
    return response.status_code == 200

def main():
    """Tests principaux"""
    print("🚀 Démarrage des tests de l'API des tags")
    print(f"📍 URL du backend: {BASE_URL}")
    
    success = True
    
    # Test 1: Liste des tags
    if not test_list_tags():
        success = False
    
    # Test 2: Résumé des tags
    if not test_tags_summary():
        success = False
    
    # Test 3: Suppression d'un tag de test
    # test_delete_tag("test-tag")  # Décommenter pour tester la suppression
    
    if success:
        print("\n✅ Tous les tests sont passés!")
    else:
        print("\n❌ Certains tests ont échoué")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au backend. Assurez-vous qu'il est lancé sur le port 8743")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")