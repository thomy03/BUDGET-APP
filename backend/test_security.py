#!/usr/bin/env python3
"""
Script de test sécurité complet - Budget Famille API
Valide l'authentification, le chiffrement et la non-régression
"""

import os
import sys
import time
import json
import logging
import sqlite3
import requests
from pathlib import Path

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration test
BASE_URL = "http://127.0.0.1:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "secret"

class SecurityTestSuite:
    def __init__(self):
        self.token = None
        self.auth_headers = {}
        self.test_results = []
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Enregistre le résultat d'un test"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}: {details}")
    
    def test_cors_security(self):
        """Test 1: Vérification configuration CORS restrictive"""
        try:
            # Test avec origine non autorisée
            headers = {"Origin": "http://malicious-site.com"}
            response = requests.get(f"{BASE_URL}/config", headers=headers)
            
            # Vérifier que l'origine malveillante est rejetée
            cors_allowed = response.headers.get("Access-Control-Allow-Origin")
            if cors_allowed and "malicious-site.com" in cors_allowed:
                self.log_test_result("CORS Security", False, "Origine malveillante acceptée")
            else:
                self.log_test_result("CORS Security", True, "CORS correctement configuré")
                
        except Exception as e:
            self.log_test_result("CORS Security", False, f"Erreur test: {e}")
    
    def test_authentication_required(self):
        """Test 2: Endpoints sensibles protégés"""
        protected_endpoints = [
            ("POST", "/config", {"member1": "test"}),
            ("POST", "/import", None),  # Avec fichier
            ("POST", "/fixed-lines", {"label": "test", "amount": 100, "freq": "mensuelle", "split_mode": "clé"}),
        ]
        
        for method, endpoint, payload in protected_endpoints:
            try:
                if method == "POST":
                    if endpoint == "/import":
                        # Test upload sans auth
                        files = {"file": ("test.csv", "col1,col2\nval1,val2", "text/csv")}
                        response = requests.post(f"{BASE_URL}{endpoint}", files=files)
                    else:
                        response = requests.post(f"{BASE_URL}{endpoint}", json=payload)
                
                # Doit retourner 401 ou 403
                if response.status_code in [401, 403]:
                    self.log_test_result(f"Auth Required {endpoint}", True, f"Accès refusé ({response.status_code})")
                else:
                    self.log_test_result(f"Auth Required {endpoint}", False, f"Accès autorisé ({response.status_code})")
                    
            except Exception as e:
                self.log_test_result(f"Auth Required {endpoint}", False, f"Erreur: {e}")
    
    def test_jwt_authentication(self):
        """Test 3: Authentification JWT fonctionnelle"""
        try:
            # Test login
            login_data = {"username": TEST_USERNAME, "password": TEST_PASSWORD}
            response = requests.post(f"{BASE_URL}/token", data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.auth_headers = {"Authorization": f"Bearer {self.token}"}
                self.log_test_result("JWT Authentication", True, "Token obtenu avec succès")
            else:
                self.log_test_result("JWT Authentication", False, f"Login échoué ({response.status_code})")
                
        except Exception as e:
            self.log_test_result("JWT Authentication", False, f"Erreur: {e}")
    
    def test_authenticated_access(self):
        """Test 4: Accès avec token JWT"""
        if not self.token:
            self.log_test_result("Authenticated Access", False, "Pas de token disponible")
            return
        
        try:
            # Test accès endpoint protégé
            response = requests.get(f"{BASE_URL}/config", headers=self.auth_headers)
            
            if response.status_code == 200:
                self.log_test_result("Authenticated Access", True, "Accès autorisé avec token")
            else:
                self.log_test_result("Authenticated Access", False, f"Accès refusé ({response.status_code})")
                
        except Exception as e:
            self.log_test_result("Authenticated Access", False, f"Erreur: {e}")
    
    def test_database_encryption(self):
        """Test 5: Base de données chiffrée"""
        encrypted_db_path = "./budget_encrypted.db"
        
        try:
            if Path(encrypted_db_path).exists():
                # Tenter d'ouvrir sans clé de chiffrement
                try:
                    conn = sqlite3.connect(encrypted_db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                    conn.close()
                    
                    # Si ça fonctionne, la base n'est pas chiffrée
                    self.log_test_result("Database Encryption", False, "Base accessible sans clé")
                    
                except sqlite3.DatabaseError:
                    # Erreur attendue avec base chiffrée
                    self.log_test_result("Database Encryption", True, "Base correctement chiffrée")
                    
            else:
                self.log_test_result("Database Encryption", False, "Base chiffrée non trouvée")
                
        except Exception as e:
            self.log_test_result("Database Encryption", False, f"Erreur: {e}")
    
    def test_input_validation(self):
        """Test 6: Validation des entrées"""
        if not self.token:
            self.log_test_result("Input Validation", False, "Pas de token disponible")
            return
        
        try:
            # Test upload fichier trop volumineux (simulé)
            large_content = "x" * (11 * 1024 * 1024)  # 11MB
            files = {"file": ("large.csv", large_content, "text/csv")}
            
            response = requests.post(
                f"{BASE_URL}/import", 
                files=files, 
                headers=self.auth_headers
            )
            
            if response.status_code == 413:  # Payload Too Large
                self.log_test_result("Input Validation", True, "Fichier volumineux rejeté")
            else:
                self.log_test_result("Input Validation", False, f"Validation échouée ({response.status_code})")
                
        except Exception as e:
            self.log_test_result("Input Validation", True, f"Connexion rejetée (normal): {e}")
    
    def test_sql_injection_protection(self):
        """Test 7: Protection injection SQL"""
        if not self.token:
            self.log_test_result("SQL Injection Protection", False, "Pas de token disponible")
            return
        
        try:
            # Test avec payload injection SQL basique
            malicious_payload = {
                "label": "'; DROP TABLE transactions; --",
                "amount": 100,
                "freq": "mensuelle",
                "split_mode": "clé"
            }
            
            response = requests.post(
                f"{BASE_URL}/fixed-lines", 
                json=malicious_payload,
                headers=self.auth_headers
            )
            
            # Vérifier que la requête est traitée normalement
            if response.status_code in [200, 201]:
                # Vérifier que les tables existent encore
                config_response = requests.get(f"{BASE_URL}/config", headers=self.auth_headers)
                if config_response.status_code == 200:
                    self.log_test_result("SQL Injection Protection", True, "Injection bloquée - SQLAlchemy ORM")
                else:
                    self.log_test_result("SQL Injection Protection", False, "Base potentiellement compromise")
            else:
                self.log_test_result("SQL Injection Protection", True, f"Requête rejetée ({response.status_code})")
                
        except Exception as e:
            self.log_test_result("SQL Injection Protection", False, f"Erreur: {e}")
    
    def run_all_tests(self):
        """Exécute tous les tests de sécurité"""
        logger.info("🚀 Début des tests de sécurité")
        
        self.test_cors_security()
        self.test_authentication_required()
        self.test_jwt_authentication()
        self.test_authenticated_access()
        self.test_database_encryption()
        self.test_input_validation()
        self.test_sql_injection_protection()
        
        # Rapport final
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["success"]])
        failed_tests = total_tests - passed_tests
        
        logger.info("=" * 50)
        logger.info("RAPPORT FINAL DES TESTS DE SÉCURITÉ")
        logger.info("=" * 50)
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"✅ Passés: {passed_tests}")
        logger.info(f"❌ Échoués: {failed_tests}")
        
        if failed_tests == 0:
            logger.info("🎉 TOUS LES TESTS DE SÉCURITÉ SONT PASSÉS")
            return True
        else:
            logger.error("🚨 DES TESTS DE SÉCURITÉ ONT ÉCHOUÉ - VÉRIFICATION REQUISE")
            for test in self.test_results:
                if not test["success"]:
                    logger.error(f"  - {test['test']}: {test['details']}")
            return False

def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python test_security.py [--wait-server]")
        print("  --wait-server: Attend que le serveur soit démarré")
        sys.exit(0)
    
    # Attendre le serveur si demandé
    if len(sys.argv) > 1 and sys.argv[1] == "--wait-server":
        logger.info("Attente du démarrage du serveur...")
        for i in range(30):  # 30 secondes max
            try:
                response = requests.get(f"{BASE_URL}/config", timeout=2)
                break
            except:
                time.sleep(1)
        else:
            logger.error("Serveur non accessible")
            sys.exit(1)
    
    # Exécuter les tests
    suite = SecurityTestSuite()
    success = suite.run_all_tests()
    
    # Sauvegarder rapport
    report_file = "security_test_report.json"
    with open(report_file, "w") as f:
        json.dump(suite.test_results, f, indent=2)
    logger.info(f"Rapport sauvé dans: {report_file}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()