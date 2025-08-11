import pytest
from fastapi.testclient import TestClient
from app import app
import os
import csv
from datetime import datetime

client = TestClient(app)

def generate_test_csv(filename, data):
    """Générer un fichier CSV de test."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['date', 'category', 'amount', 'description'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    return filename

def test_jwt_authentication():
    """Test complet du flux d'authentification JWT."""
    # Test inscription
    signup_response = client.post("/auth/signup", json={
        "username": "testuser",
        "email": "test@example.com", 
        "password": "SecurePass123!"
    })
    assert signup_response.status_code == 201
    
    # Test login
    login_response = client.post("/auth/token", json={
        "username": "testuser",
        "password": "SecurePass123!"
    })
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    
    token = login_response.json()["access_token"]
    
    # Test accès ressource protégée
    protected_response = client.get("/user/profile", headers={
        "Authorization": f"Bearer {token}"
    })
    assert protected_response.status_code == 200

def test_csv_import_multi_month():
    """Test d'import CSV avec données multi-mois."""
    test_data = [
        {"date": "2023-01-15", "category": "Alimentaire", "amount": "50.00", "description": "Courses janvier"},
        {"date": "2023-02-20", "category": "Transport", "amount": "30.50", "description": "Essence février"},
        {"date": "2023-03-10", "category": "Loisirs", "amount": "75.25", "description": "Cinéma mars"}
    ]
    
    csv_file = generate_test_csv("/tmp/multi_month_test.csv", test_data)
    
    # Login pour obtenir le token
    login_response = client.post("/auth/token", json={
        "username": "testuser",
        "password": "SecurePass123!"
    })
    token = login_response.json()["access_token"]
    
    # Import CSV
    with open(csv_file, 'rb') as f:
        upload_response = client.post("/import/csv", 
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("multi_month_test.csv", f, "text/csv")}
        )
    
    assert upload_response.status_code == 200
    
    # Vérifier que les transactions sont bien importées pour chaque mois
    summary_response = client.get("/summary", 
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert summary_response.status_code == 200
    summary_data = summary_response.json()
    
    assert len(summary_data["months"]) == 3
    assert all(month in ["2023-01", "2023-02", "2023-03"] for month in summary_data["months"])

def test_transaction_crud():
    """Test des opérations CRUD sur les transactions."""
    # Login
    login_response = client.post("/auth/token", json={
        "username": "testuser",
        "password": "SecurePass123!"
    })
    token = login_response.json()["access_token"]
    
    # Créer une transaction
    create_response = client.post("/transactions", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "date": "2023-04-01",
            "category": "Test",
            "amount": 100.00,
            "description": "Transaction de test"
        }
    )
    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]
    
    # Lire la transaction
    read_response = client.get(f"/transactions/{transaction_id}", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert read_response.status_code == 200
    
    # Mettre à jour la transaction
    update_response = client.put(f"/transactions/{transaction_id}", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "date": "2023-04-01",
            "category": "Test Modifié",
            "amount": 150.00,
            "description": "Transaction modifiée"
        }
    )
    assert update_response.status_code == 200
    
    # Supprimer la transaction
    delete_response = client.delete(f"/transactions/{transaction_id}", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 204

def test_security_validations():
    """Tests de validation de sécurité."""
    # Test création utilisateur avec mot de passe faible
    weak_signup = client.post("/auth/signup", json={
        "username": "weakuser",
        "email": "weak@example.com", 
        "password": "weak"
    })
    assert weak_signup.status_code == 422  # Validation échouée
    
    # Test login avec identifiants invalides
    invalid_login = client.post("/auth/token", json={
        "username": "nonexistent",
        "password": "wrongpassword"
    })
    assert invalid_login.status_code == 401  # Non autorisé