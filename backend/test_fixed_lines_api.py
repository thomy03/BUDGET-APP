#!/usr/bin/env python3
"""
Tests complets pour l'API FixedLine
Tests des endpoints CRUD et de la logique de calcul
"""

import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import de l'application
from app import app, get_db, Base, FixedLine, Config
from auth import create_access_token


class TestFixedLinesAPI:
    """Tests pour l'API des lignes fixes"""
    
    @classmethod
    def setup_class(cls):
        """Configuration des tests"""
        # Base de données temporaire en mémoire
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp()
        cls.engine = create_engine(f"sqlite:///{cls.test_db_path}", connect_args={"check_same_thread": False})
        
        # Créer les tables
        Base.metadata.create_all(bind=cls.engine)
        
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        
        def override_get_db():
            try:
                db = cls.TestingSessionLocal()
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)
        
        # Créer un utilisateur de test et un token
        cls.test_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "fake_hash"
        }
        
        # Token de test
        cls.test_token = create_access_token(data={"sub": cls.test_user_data["username"]})
        cls.headers = {"Authorization": f"Bearer {cls.test_token}"}
        
        # Configuration par défaut
        db = cls.TestingSessionLocal()
        default_config = Config(
            member1="Alice", member2="Bob", rev1=3000, rev2=2500,
            loan_amount=1200, other_fixed_monthly=800
        )
        db.add(default_config)
        db.commit()
        db.close()
    
    @classmethod
    def teardown_class(cls):
        """Nettoyage après les tests"""
        os.close(cls.test_db_fd)
        os.unlink(cls.test_db_path)
    
    def setup_method(self):
        """Nettoyage avant chaque test"""
        db = self.TestingSessionLocal()
        db.query(FixedLine).delete()
        db.commit()
        db.close()
    
    def test_create_fixed_line_success(self):
        """Test création d'une ligne fixe valide"""
        payload = {
            "label": "Électricité",
            "amount": 120.50,
            "freq": "mensuelle",
            "split_mode": "50/50",
            "split1": 0.5,
            "split2": 0.5,
            "category": "logement",
            "active": True
        }
        
        response = self.client.post("/fixed-lines", json=payload, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["label"] == "Électricité"
        assert data["amount"] == 120.5
        assert data["freq"] == "mensuelle"
        assert data["split_mode"] == "50/50"
        assert data["category"] == "logement"
        assert data["active"] is True
        assert "id" in data
    
    def test_create_fixed_line_invalid_category(self):
        """Test création avec catégorie invalide"""
        payload = {
            "label": "Test",
            "amount": 100,
            "freq": "mensuelle",
            "split_mode": "50/50",
            "category": "invalide",  # Catégorie non autorisée
            "active": True
        }
        
        response = self.client.post("/fixed-lines", json=payload, headers=self.headers)
        assert response.status_code == 422
    
    def test_create_fixed_line_invalid_freq(self):
        """Test création avec fréquence invalide"""
        payload = {
            "label": "Test",
            "amount": 100,
            "freq": "quotidienne",  # Fréquence non autorisée
            "split_mode": "50/50",
            "category": "logement",
            "active": True
        }
        
        response = self.client.post("/fixed-lines", json=payload, headers=self.headers)
        assert response.status_code == 422
    
    def test_list_fixed_lines_empty(self):
        """Test liste vide"""
        response = self.client.get("/fixed-lines", headers=self.headers)
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_fixed_lines_with_data(self):
        """Test liste avec données"""
        # Créer des lignes fixes de test
        db = self.TestingSessionLocal()
        
        lines = [
            FixedLine(label="Électricité", amount=120, freq="mensuelle", split_mode="50/50", category="logement"),
            FixedLine(label="Assurance auto", amount=600, freq="annuelle", split_mode="clé", category="transport"),
            FixedLine(label="Internet", amount=45, freq="mensuelle", split_mode="50/50", category="services")
        ]
        
        for line in lines:
            db.add(line)
        db.commit()
        db.close()
        
        response = self.client.get("/fixed-lines", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Vérifier le tri par catégorie
        categories = [item["category"] for item in data]
        assert categories == ["logement", "services", "transport"]
    
    def test_list_fixed_lines_filter_by_category(self):
        """Test filtrage par catégorie"""
        # Créer des lignes fixes de test
        db = self.TestingSessionLocal()
        
        lines = [
            FixedLine(label="Électricité", amount=120, category="logement"),
            FixedLine(label="Assurance auto", amount=600, category="transport"),
            FixedLine(label="Internet", amount=45, category="services")
        ]
        
        for line in lines:
            db.add(line)
        db.commit()
        db.close()
        
        # Filtrer par logement
        response = self.client.get("/fixed-lines?category=logement", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "logement"
        assert data[0]["label"] == "Électricité"
    
    def test_list_fixed_lines_inactive_filter(self):
        """Test filtrage des lignes inactives"""
        # Créer des lignes fixes de test (une active, une inactive)
        db = self.TestingSessionLocal()
        
        lines = [
            FixedLine(label="Active", amount=120, category="logement", active=True),
            FixedLine(label="Inactive", amount=60, category="logement", active=False)
        ]
        
        for line in lines:
            db.add(line)
        db.commit()
        db.close()
        
        # Par défaut (active_only=True)
        response = self.client.get("/fixed-lines", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["label"] == "Active"
        
        # Inclure les inactives
        response = self.client.get("/fixed-lines?active_only=false", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_fixed_line_by_id_success(self):
        """Test récupération d'une ligne par ID"""
        # Créer une ligne fixe
        db = self.TestingSessionLocal()
        line = FixedLine(label="Test", amount=100, category="logement")
        db.add(line)
        db.commit()
        db.refresh(line)
        line_id = line.id
        db.close()
        
        response = self.client.get(f"/fixed-lines/{line_id}", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == line_id
        assert data["label"] == "Test"
        assert data["category"] == "logement"
    
    def test_get_fixed_line_by_id_not_found(self):
        """Test récupération d'une ligne inexistante"""
        response = self.client.get("/fixed-lines/999", headers=self.headers)
        assert response.status_code == 404
    
    def test_update_fixed_line_success(self):
        """Test mise à jour d'une ligne fixe"""
        # Créer une ligne fixe
        db = self.TestingSessionLocal()
        line = FixedLine(label="Original", amount=100, category="logement")
        db.add(line)
        db.commit()
        db.refresh(line)
        line_id = line.id
        db.close()
        
        # Mettre à jour
        payload = {
            "label": "Modifié",
            "amount": 150,
            "freq": "mensuelle",
            "split_mode": "clé",
            "split1": 0.6,
            "split2": 0.4,
            "category": "transport",
            "active": True
        }
        
        response = self.client.patch(f"/fixed-lines/{line_id}", json=payload, headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Modifié"
        assert data["amount"] == 150
        assert data["category"] == "transport"
    
    def test_update_fixed_line_not_found(self):
        """Test mise à jour d'une ligne inexistante"""
        payload = {
            "label": "Test",
            "amount": 100,
            "freq": "mensuelle",
            "split_mode": "50/50",
            "category": "logement",
            "active": True
        }
        
        response = self.client.patch("/fixed-lines/999", json=payload, headers=self.headers)
        assert response.status_code == 404
    
    def test_delete_fixed_line_success(self):
        """Test suppression d'une ligne fixe"""
        # Créer une ligne fixe
        db = self.TestingSessionLocal()
        line = FixedLine(label="À supprimer", amount=100, category="logement")
        db.add(line)
        db.commit()
        db.refresh(line)
        line_id = line.id
        db.close()
        
        response = self.client.delete(f"/fixed-lines/{line_id}", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "À supprimer" in data["message"]
        
        # Vérifier que la ligne n'existe plus
        response = self.client.get(f"/fixed-lines/{line_id}", headers=self.headers)
        assert response.status_code == 404
    
    def test_delete_fixed_line_not_found(self):
        """Test suppression d'une ligne inexistante"""
        response = self.client.delete("/fixed-lines/999", headers=self.headers)
        assert response.status_code == 404
    
    def test_get_stats_by_category(self):
        """Test récupération des statistiques par catégorie"""
        # Créer des lignes fixes de test avec différentes fréquences
        db = self.TestingSessionLocal()
        
        lines = [
            # Logement: 120 + 50 = 170/mois
            FixedLine(label="Électricité", amount=120, freq="mensuelle", category="logement"),
            FixedLine(label="Assurance habitation", amount=600, freq="annuelle", category="logement"),  # 50/mois
            
            # Transport: 150 + 33.33 = 183.33/mois  
            FixedLine(label="Essence", amount=150, freq="mensuelle", category="transport"),
            FixedLine(label="Assurance auto", amount=400, freq="trimestrielle", category="transport"),  # 133.33/mois
        ]
        
        for line in lines:
            db.add(line)
        db.commit()
        db.close()
        
        response = self.client.get("/fixed-lines/stats/by-category", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "by_category" in data
        assert "global_monthly_total" in data
        assert "total_lines" in data
        
        # Vérifier les totaux
        assert data["total_lines"] == 4
        
        # Vérifier les catégories
        categories_data = {item["category"]: item for item in data["by_category"]}
        
        assert "logement" in categories_data
        assert "transport" in categories_data
        
        # Vérifier les calculs mensuels (avec tolérance pour les arrondis)
        logement_monthly = categories_data["logement"]["monthly_total"]
        transport_monthly = categories_data["transport"]["monthly_total"]
        
        assert abs(logement_monthly - 170) < 0.01  # 120 + 600/12
        assert abs(transport_monthly - 283.33) < 0.01  # 150 + 400/3
    
    def test_unauthorized_access(self):
        """Test accès sans authentification"""
        response = self.client.get("/fixed-lines")
        assert response.status_code == 401


def run_tests():
    """Exécute les tests et génère un rapport"""
    import sys
    
    print("🧪 Tests API FixedLine - Démarrage...")
    print("=" * 50)
    
    try:
        # Exécuter les tests
        exit_code = pytest.main([
            __file__,
            "-v",
            "--tb=short",
            "--disable-warnings"
        ])
        
        if exit_code == 0:
            print("\n✅ Tous les tests sont passés avec succès!")
            print("\n📋 Résumé des fonctionnalités testées:")
            print("   • CRUD complet des lignes fixes")
            print("   • Validation des données d'entrée")
            print("   • Filtrage par catégorie")
            print("   • Filtrage par statut actif/inactif")
            print("   • Calculs de statistiques mensuelles")
            print("   • Gestion des erreurs (404, 422)")
            print("   • Authentification JWT")
            
            return True
        else:
            print(f"\n❌ Certains tests ont échoué (code: {exit_code})")
            return False
            
    except Exception as e:
        print(f"\n💥 Erreur lors de l'exécution des tests: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)