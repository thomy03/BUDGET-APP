"""
Test Validation des Tags - Scénarios de Test Complets

Ce script teste exhaustivement le comportement de mise à jour des tags
pour identifier précisément les problèmes de validation.
"""
import pytest
import requests
import json
from typing import Dict, Any

# Configuration de base
BASE_URL = "http://localhost:8000"

def get_auth_token():
    """Récupérer un token d'authentification valide"""
    auth_data = {
        "username": "diana",  # Remplacer par un utilisateur de test
        "password": "diana123"  # Remplacer par le mot de passe de test
    }
    response = requests.post(f"{BASE_URL}/token", json=auth_data)
    assert response.status_code == 200, "Impossible de récupérer le token d'authentification"
    return response.json()['access_token']

def test_tags_validation():
    """
    Test complet de validation des tags pour PATCH /transactions/{id}/tags
    
    Objectifs:
    - Tester différents formats de payload pour les tags
    - Capturer les messages d'erreur exacts
    - Identifier les formats acceptés
    """
    token = get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Transaction ID de test (à ajuster selon votre base de données)
    test_transaction_id = 1
    
    # Scénarios de test
    test_scenarios = [
        {
            "name": "Tags comme string",
            "payload": {"tags": "tag1,tag2,tag3"},
            "expected_status": 200,
            "description": "Chaîne de tags séparés par des virgules"
        },
        {
            "name": "Tags comme string vide",
            "payload": {"tags": ""},
            "expected_status": 200,
            "description": "Chaîne de tags vide"
        },
        {
            "name": "Tags comme None",
            "payload": {"tags": None},
            "expected_status": 422,
            "description": "Valeur None pour les tags"
        },
        {
            "name": "Payload sans tags",
            "payload": {},
            "expected_status": 422,
            "description": "Payload sans champ tags"
        },
        {
            "name": "Tags avec espaces",
            "payload": {"tags": " tag1 , tag2 , tag3 "},
            "expected_status": 200,
            "description": "Tags avec espaces supplémentaires"
        }
    ]
    
    # Exécution des tests
    detailed_results = []
    
    for scenario in test_scenarios:
        response = requests.patch(
            f"{BASE_URL}/transactions/{test_transaction_id}/tags", 
            headers=headers,
            json=scenario['payload']
        )
        
        result = {
            "scenario_name": scenario['name'],
            "status_code": response.status_code,
            "expected_status": scenario['expected_status'],
            "description": scenario['description'],
            "payload": scenario['payload'],
            "response_text": response.text
        }
        
        try:
            result['response_json'] = response.json()
        except json.JSONDecodeError:
            result['response_json'] = None
        
        # Validation du statut
        assert response.status_code == scenario['expected_status'], \
            f"Échec du scénario {scenario['name']}: " \
            f"Status attendu {scenario['expected_status']}, " \
            f"reçu {response.status_code}. Détails: {response.text}"
        
        detailed_results.append(result)
    
    # Génération du rapport détaillé
    rapport_validation = {
        "titre": "Rapport de Validation des Tags de Transaction",
        "scenarios": detailed_results,
        "resume": {
            "total_scenarios": len(test_scenarios),
            "scenarios_passes": sum(1 for r in detailed_results if r['status_code'] == 200),
            "scenarios_echoues": sum(1 for r in detailed_results if r['status_code'] != 200)
        }
    }
    
    # Sauvegarder le rapport
    with open('tags_validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(rapport_validation, f, ensure_ascii=False, indent=2)
    
    print("✅ Test complet de validation des tags terminé. Rapport généré.")
    return rapport_validation

# Pour une exécution individuelle du script
if __name__ == "__main__":
    test_tags_validation()