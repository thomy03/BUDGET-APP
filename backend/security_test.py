#!/usr/bin/env python3
"""
Script de test de sécurité automatisé pour l'application Budget Famille
Tests les vulnérabilités courantes et la robustesse des endpoints
"""

import os
import sys
import requests
import json
import time
import tempfile
from typing import Dict, List, Tuple
from pathlib import Path

# Configuration des tests
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "secret"

class SecurityTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.test_results: List[Dict] = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Enregistre le résultat d'un test"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def authenticate(self) -> bool:
        """Authentification pour les tests"""
        try:
            response = self.session.post(
                f"{self.base_url}/token",
                data={
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                self.log_test("Authentication", True, "Token obtenu")
                return True
            else:
                self.log_test("Authentication", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Authentication", False, str(e))
            return False
    
    def test_cors_security(self):
        """Test de la configuration CORS"""
        try:
            # Test avec origin non autorisé
            headers = {"Origin": "https://evil-site.com"}
            response = requests.get(f"{self.base_url}/config", headers=headers)
            
            # Vérifier que CORS refuse l'origine non autorisée
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            if cors_header and "evil-site.com" in cors_header:
                self.log_test("CORS Security", False, "CORS permet des origines non autorisées")
            else:
                self.log_test("CORS Security", True, "CORS correctement configuré")
                
        except Exception as e:
            self.log_test("CORS Security", False, str(e))
    
    def test_jwt_validation(self):
        """Test de validation des tokens JWT"""
        tests = [
            # Token invalide
            ("Bearer invalid_token", "Token invalide"),
            # Token expiré (simulé)
            ("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid", "Token expiré"),
            # Format incorrect
            ("InvalidFormat", "Format incorrect"),
            # Token vide
            ("Bearer ", "Token vide")
        ]
        
        for token, test_name in tests:
            try:
                headers = {"Authorization": token}
                response = requests.post(
                    f"{self.base_url}/config",
                    json={"member1": "test"},
                    headers=headers
                )
                
                if response.status_code == 401:
                    self.log_test(f"JWT Validation - {test_name}", True, "Accès refusé comme attendu")
                else:
                    self.log_test(f"JWT Validation - {test_name}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"JWT Validation - {test_name}", False, str(e))
    
    def test_input_validation(self):
        """Test de validation des entrées"""
        if not self.token:
            self.log_test("Input Validation", False, "Pas de token d'authentification")
            return
            
        # Tests de validation sur endpoint /config
        invalid_configs = [
            # XSS dans member1
            ({"member1": "<script>alert('xss')</script>", "member2": "test"}, "XSS Script"),
            # SQL Injection simulée
            ({"member1": "'; DROP TABLE config; --", "member2": "test"}, "SQL Injection"),
            # Valeurs négatives incorrectes
            ({"rev1": -1000, "rev2": 5000}, "Revenus négatifs"),
            # Valeurs trop élevées
            ({"rev1": 999999999, "rev2": 5000}, "Revenus trop élevés"),
            # Split mode invalide
            ({"split_mode": "invalid_mode"}, "Mode split invalide"),
            # Noms trop longs
            ({"member1": "A" * 100, "member2": "test"}, "Nom trop long")
        ]
        
        for invalid_data, test_name in invalid_configs:
            try:
                response = self.session.post(
                    f"{self.base_url}/config",
                    json=invalid_data
                )
                
                if response.status_code in [400, 422]:  # Validation error expected
                    self.log_test(f"Input Validation - {test_name}", True, "Données invalides rejetées")
                else:
                    self.log_test(f"Input Validation - {test_name}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Input Validation - {test_name}", False, str(e))
    
    def test_file_upload_security(self):
        """Test de sécurité des uploads de fichiers"""
        if not self.token:
            self.log_test("File Upload Security", False, "Pas de token d'authentification")
            return
        
        dangerous_files = [
            # Fichier exécutable
            (b"#!/bin/bash\\necho 'pwned'", "malware.sh", "Fichier exécutable"),
            # Fichier PHP malveillant
            (b"<?php system($_GET['cmd']); ?>", "shell.php", "Script PHP malveillant"),
            # Fichier avec extension double
            (b"malicious content", "file.csv.exe", "Extension double"),
            # Fichier trop volumineux (simulé)
            (b"A" * 1024 * 1024 * 15, "huge.csv", "Fichier trop volumineux"),  # 15MB
            # Caractères spéciaux dans nom
            (b"test,data", "../../../etc/passwd", "Path traversal")
        ]
        
        for content, filename, test_name in dangerous_files:
            try:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(content)
                    temp_file.flush()
                    
                    with open(temp_file.name, 'rb') as f:
                        files = {'file': (filename, f, 'text/plain')}
                        response = self.session.post(
                            f"{self.base_url}/import",
                            files=files
                        )
                
                # Nettoyage
                os.unlink(temp_file.name)
                
                if response.status_code in [400, 413, 415]:  # Erreurs de validation attendues
                    self.log_test(f"File Upload Security - {test_name}", True, "Fichier dangereux rejeté")
                else:
                    self.log_test(f"File Upload Security - {test_name}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"File Upload Security - {test_name}", False, str(e))
    
    def test_rate_limiting(self):
        """Test basique de limitation de débit"""
        # Simulation d'attaque par force brute sur login
        failed_attempts = 0
        
        for i in range(10):  # 10 tentatives rapides
            try:
                response = requests.post(
                    f"{self.base_url}/token",
                    data={
                        "username": "hacker",
                        "password": f"wrong_password_{i}"
                    }
                )
                if response.status_code == 401:
                    failed_attempts += 1
                elif response.status_code == 429:  # Too Many Requests
                    self.log_test("Rate Limiting", True, "Limitation de débit active")
                    return
                    
                time.sleep(0.1)  # Petit délai entre tentatives
                
            except Exception as e:
                self.log_test("Rate Limiting", False, str(e))
                return
        
        # Si aucune limitation détectée
        self.log_test("Rate Limiting", False, "Aucune limitation de débit détectée")
    
    def test_information_disclosure(self):
        """Test de divulgation d'informations"""
        # Test d'endpoints non autorisés
        endpoints_to_test = [
            "/admin",
            "/debug",
            "/.env",
            "/config.json",
            "/database.db",
            "/logs",
            "/backup"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                if response.status_code == 404:
                    self.log_test(f"Info Disclosure - {endpoint}", True, "Endpoint non exposé")
                elif response.status_code in [200, 403]:
                    self.log_test(f"Info Disclosure - {endpoint}", False, f"Endpoint accessible: {response.status_code}")
                else:
                    self.log_test(f"Info Disclosure - {endpoint}", True, f"Status approprié: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Info Disclosure - {endpoint}", False, str(e))
    
    def test_audit_logging(self):
        """Vérification de la présence des logs d'audit"""
        audit_files = [
            "./audit.log",
            "./logs/audit.log",
            "../audit.log"
        ]
        
        audit_found = False
        for audit_file in audit_files:
            if os.path.exists(audit_file):
                audit_found = True
                # Vérifier que le fichier contient des entrées récentes
                try:
                    with open(audit_file, 'r') as f:
                        content = f.read()
                        if "LOGIN_SUCCESS" in content or "LOGIN_FAILED" in content:
                            self.log_test("Audit Logging", True, f"Audit actif dans {audit_file}")
                            return
                except Exception:
                    pass
        
        if audit_found:
            self.log_test("Audit Logging", False, "Fichier d'audit trouvé mais pas d'entrées récentes")
        else:
            self.log_test("Audit Logging", False, "Aucun fichier d'audit trouvé")
    
    def run_all_tests(self):
        """Lance tous les tests de sécurité"""
        print("🔐 DÉMARRAGE DES TESTS DE SÉCURITÉ")
        print("=" * 50)
        
        # Test de connectivité
        try:
            response = requests.get(f"{self.base_url}/config", timeout=5)
            print(f"✅ Serveur accessible sur {self.base_url}")
        except Exception as e:
            print(f"❌ Impossible d'accéder au serveur: {e}")
            return
        
        # Tests d'authentification
        if self.authenticate():
            self.test_jwt_validation()
            self.test_input_validation()
            self.test_file_upload_security()
        
        # Tests sans authentification
        self.test_cors_security()
        self.test_rate_limiting()
        self.test_information_disclosure()
        self.test_audit_logging()
        
        # Rapport final
        print("\\n" + "=" * 50)
        print("📊 RAPPORT DE SÉCURITÉ")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)
        
        print(f"Tests réussis: {passed}/{total} ({passed/total*100:.1f}%)")
        
        print("\\n🔴 ÉCHECS:")
        for result in self.test_results:
            if not result["passed"]:
                print(f"  - {result['test']}: {result['details']}")
        
        print("\\n🟡 RECOMMANDATIONS:")
        if passed / total < 0.8:
            print("  - Corriger les vulnérabilités critiques identifiées")
        if any("Rate Limiting" in r["test"] and not r["passed"] for r in self.test_results):
            print("  - Implémenter une limitation de débit pour prévenir les attaques par force brute")
        if any("Audit" in r["test"] and not r["passed"] for r in self.test_results):
            print("  - Vérifier la configuration du système d'audit")
        
        print("\\n✅ Tests de sécurité terminés")
        
        # Sauvegarder le rapport
        report_file = f"security_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "base_url": self.base_url,
                "total_tests": total,
                "passed_tests": passed,
                "success_rate": passed/total*100,
                "results": self.test_results
            }, f, indent=2)
        
        print(f"📋 Rapport détaillé sauvegardé: {report_file}")

def main():
    """Fonction principale"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"🎯 Tests de sécurité sur: {base_url}")
    
    tester = SecurityTester(base_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()