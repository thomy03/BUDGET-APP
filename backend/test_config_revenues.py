import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import app
from dependencies.database import get_db
from models.database import Config

def test_config_revenue_update(client: TestClient, db: Session, login_user):
    """
    Test de validation de la sauvegarde des revenus
    
    Scénarios de test:
    1. Modification des revenus des membres
    2. Vérification de la sauvegarde
    3. Validation de la persistance
    4. Confirmation des calculs mis à jour
    """
    # 1. Authentification
    token = login_user
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Configuration initiale des revenus
    initial_config_response = client.get("/config", headers=headers)
    assert initial_config_response.status_code == 200
    initial_config = initial_config_response.json()
    
    # 3. Mise à jour des revenus
    updated_config = {
        "rev1": 3000,  # Revenu membre 1
        "rev2": 2500,  # Revenu membre 2
        "member1": "Membre Test 1",
        "member2": "Membre Test 2"
    }
    
    # 4. Envoi de la configuration mise à jour
    update_response = client.post("/config", json=updated_config, headers=headers)
    
    # Assertions de validation
    assert update_response.status_code == 200, "Échec de la mise à jour de configuration"
    updated_config_response = update_response.json()
    
    # Vérification des revenus mis à jour
    assert updated_config_response['rev1'] == 3000, "Revenu membre 1 non mis à jour"
    assert updated_config_response['rev2'] == 2500, "Revenu membre 2 non mis à jour"
    
    # 5. Vérification de la persistance
    verification_response = client.get("/config", headers=headers)
    verified_config = verification_response.json()
    
    assert verified_config['rev1'] == 3000, "Revenu membre 1 non persistant"
    assert verified_config['rev2'] == 2500, "Revenu membre 2 non persistant"
    
    # 6. Vérification des détails membres
    assert verified_config['member1'] == "Membre Test 1", "Nom membre 1 incorrect"
    assert verified_config['member2'] == "Membre Test 2", "Nom membre 2 incorrect"

def test_config_revenue_validation(client: TestClient, db: Session, login_user):
    """
    Test de validation des contraintes sur les revenus
    """
    token = login_user
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test revenus négatifs
    invalid_config = {
        "rev1": -1000,  # Revenu négatif non autorisé
        "rev2": 2500
    }
    
    update_response = client.post("/config", json=invalid_config, headers=headers)
    assert update_response.status_code == 422, "Configuration avec revenu négatif devrait être refusée"