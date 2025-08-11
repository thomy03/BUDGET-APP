#!/usr/bin/env python3
"""
Script de test compréhensif du système d'authentification
"""
import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"

class AuthTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []

    def log_test(self, test_name, success, details=None, error=None):
        """Enregistrer le résultat d'un test"""
        result = {
            "test": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "error": str(error) if error else None
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        if error:
            print(f"    Erreur: {error}")

    def test_health_endpoint(self):
        """Test 1: Vérifier l'endpoint /health"""
        try:
            response = self.session.get(f"{BASE_URL}/health")
            success = response.status_code == 200
            data = response.json() if success else None
            
            self.log_test(
                "Health endpoint",
                success,
                details=f"Status: {response.status_code}, Auth config: {data.get('auth', {}) if data else 'N/A'}"
            )
            return success
            
        except Exception as e:
            self.log_test("Health endpoint", False, error=e)
            return False

    def test_token_generation_valid(self):
        """Test 2: Génération de token avec credentials valides"""
        try:
            data = {
                "username": "admin",
                "password": "secret"
            }
            response = self.session.post(
                f"{BASE_URL}/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            success = response.status_code == 200
            if success:
                token_data = response.json()
                self.token = token_data.get("access_token")
                
            self.log_test(
                "Token generation (valid credentials)",
                success,
                details=f"Status: {response.status_code}, Token length: {len(self.token) if self.token else 0}"
            )
            return success
            
        except Exception as e:
            self.log_test("Token generation (valid credentials)", False, error=e)
            return False

    def test_token_generation_invalid(self):
        """Test 3: Test avec credentials invalides"""
        try:
            data = {
                "username": "admin",
                "password": "wrong_password"
            }
            response = self.session.post(
                f"{BASE_URL}/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Doit retourner 401
            success = response.status_code == 401
            
            self.log_test(
                "Token generation (invalid credentials)",
                success,
                details=f"Status: {response.status_code} (should be 401)"
            )
            return success
            
        except Exception as e:
            self.log_test("Token generation (invalid credentials)", False, error=e)
            return False

    def test_protected_endpoint_with_token(self):
        """Test 4: Accès à un endpoint protégé avec token"""
        if not self.token:
            self.log_test("Protected endpoint (with token)", False, error="No token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{BASE_URL}/config", headers=headers)
            
            success = response.status_code == 200
            data = response.json() if success else None
            
            self.log_test(
                "Protected endpoint (with token)",
                success,
                details=f"Status: {response.status_code}, Config loaded: {bool(data)}"
            )
            return success
            
        except Exception as e:
            self.log_test("Protected endpoint (with token)", False, error=e)
            return False

    def test_protected_endpoint_without_token(self):
        """Test 5: Accès à un endpoint protégé sans token"""
        try:
            response = self.session.get(f"{BASE_URL}/config")
            
            # Doit retourner 403 ou 401
            success = response.status_code in [401, 403]
            
            self.log_test(
                "Protected endpoint (without token)",
                success,
                details=f"Status: {response.status_code} (should be 401/403)"
            )
            return success
            
        except Exception as e:
            self.log_test("Protected endpoint (without token)", False, error=e)
            return False

    def test_protected_endpoint_invalid_token(self):
        """Test 6: Accès avec token invalide"""
        try:
            headers = {"Authorization": "Bearer invalid_token_here"}
            response = self.session.get(f"{BASE_URL}/config", headers=headers)
            
            # Doit retourner 401
            success = response.status_code == 401
            
            self.log_test(
                "Protected endpoint (invalid token)",
                success,
                details=f"Status: {response.status_code} (should be 401)"
            )
            return success
            
        except Exception as e:
            self.log_test("Protected endpoint (invalid token)", False, error=e)
            return False

    def test_cors_headers(self):
        """Test 7: Vérifier les headers CORS"""
        try:
            # Test OPTIONS request
            response = self.session.options(f"{BASE_URL}/token")
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
                "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
            }
            
            success = any(cors_headers.values())
            
            self.log_test(
                "CORS headers",
                success,
                details=f"Headers found: {sum(1 for v in cors_headers.values() if v)}/4"
            )
            return success
            
        except Exception as e:
            self.log_test("CORS headers", False, error=e)
            return False

    def test_multiple_endpoints(self):
        """Test 8: Test de plusieurs endpoints avec le même token"""
        if not self.token:
            self.log_test("Multiple endpoints test", False, error="No token available")
            return False
            
        endpoints = ["/config", "/health", "/config"]  # Test config twice
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            results = []
            for endpoint in endpoints:
                response = self.session.get(f"{BASE_URL}{endpoint}", headers=headers)
                results.append(response.status_code)
            
            # Health est public, config doit être 200 avec token
            success = results[1] == 200 and results[0] == 200 and results[2] == 200
            
            self.log_test(
                "Multiple endpoints test",
                success,
                details=f"Results: {results}"
            )
            return success
            
        except Exception as e:
            self.log_test("Multiple endpoints test", False, error=e)
            return False

    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 DÉMARRAGE DES TESTS D'AUTHENTIFICATION")
        print("="*50)
        
        tests = [
            self.test_health_endpoint,
            self.test_token_generation_valid,
            self.test_token_generation_invalid,
            self.test_protected_endpoint_with_token,
            self.test_protected_endpoint_without_token,
            self.test_protected_endpoint_invalid_token,
            self.test_cors_headers,
            self.test_multiple_endpoints
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            time.sleep(0.5)  # Pause entre les tests
        
        print("\n" + "="*50)
        print(f"📊 RÉSULTATS: {passed}/{total} tests réussis")
        
        if passed == total:
            print("🎉 TOUS LES TESTS SONT PASSÉS - Authentification opérationnelle!")
            return True
        else:
            print(f"⚠️  {total - passed} tests ont échoué - Vérifications nécessaires")
            return False

    def save_results(self, filename="auth_test_results.json"):
        """Sauvegarder les résultats des tests"""
        try:
            with open(filename, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": len(self.test_results),
                    "passed_tests": sum(1 for r in self.test_results if r["success"]),
                    "results": self.test_results
                }, f, indent=2)
            print(f"💾 Résultats sauvegardés dans {filename}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")

def main():
    print("🔐 TEST COMPRÉHENSIF DU SYSTÈME D'AUTHENTIFICATION")
    print("Serveur attendu: http://localhost:5000")
    print()
    
    tester = AuthTester()
    
    try:
        success = tester.run_all_tests()
        tester.save_results()
        
        if success:
            print("\n✅ Le système d'authentification fonctionne correctement")
            sys.exit(0)
        else:
            print("\n❌ Des problèmes ont été détectés dans l'authentification")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrompus par l'utilisateur")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Erreur critique durant les tests: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()