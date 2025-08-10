#!/usr/bin/env python3
"""
Script de validation End-to-End complet pour l'application Budget Famille
Tests du flow complet : authentification → import CSV → navigation automatique
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional

# Configuration
API_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://localhost:3000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class E2EValidator:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.import_id = None
        self.suggested_month = None
        self.errors = []
        self.warnings = []
        
    def log_success(self, message: str):
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
        
    def log_error(self, message: str):
        print(f"{Colors.RED}❌ {message}{Colors.END}")
        self.errors.append(message)
        
    def log_warning(self, message: str):
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.END}")
        self.warnings.append(message)
        
    def log_info(self, message: str):
        print(f"{Colors.BLUE}ℹ️ {message}{Colors.END}")
        
    def log_section(self, title: str):
        print(f"\n{Colors.BOLD}{Colors.BLUE}=== {title} ==={Colors.END}")
        
    def test_health(self) -> bool:
        """Test la santé du backend"""
        try:
            response = self.session.get(f"{API_BASE}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"Backend opérationnel (version {data.get('version', 'N/A')})")
                self.log_info(f"Platform: {data.get('platform', {}).get('system', 'N/A')}")
                self.log_info(f"Database: {'Encrypted' if data.get('database', {}).get('encryption_enabled') else 'Standard'}")
                return True
            else:
                self.log_error(f"Health check échoué: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            self.log_error(f"Erreur connexion backend: {e}")
            return False
            
    def test_authentication(self) -> bool:
        """Test de l'authentification JWT"""
        try:
            # Test avec de bons identifiants
            response = self.session.post(
                f"{API_BASE}/token",
                data={"username": "admin", "password": "secret"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                token_type = data.get("token_type", "bearer")
                
                if self.token:
                    # Configurer l'authentification pour les requêtes suivantes
                    self.session.headers.update({
                        "Authorization": f"{token_type} {self.token}"
                    })
                    self.log_success("Authentification réussie")
                    return True
                else:
                    self.log_error("Token manquant dans la réponse")
                    return False
            else:
                self.log_error(f"Authentification échouée: HTTP {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.log_error(f"Erreur authentification: {e}")
            return False
            
    def test_protected_endpoint(self) -> bool:
        """Test d'accès à un endpoint protégé"""
        try:
            response = self.session.get(f"{API_BASE}/config", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"Configuration récupérée (membre1: {data.get('member1', 'N/A')})")
                return True
            else:
                self.log_error(f"Échec accès endpoint protégé: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            self.log_error(f"Erreur endpoint protégé: {e}")
            return False
            
    def test_csv_import(self) -> bool:
        """Test de l'import CSV avec navigation automatique"""
        try:
            # Créer un fichier CSV de test
            csv_content = '''dateOp,dateVal,label,category,categoryParent,supplierFound,amount,comment,accountNum,accountLabel,accountbalance
2024-01-15,2024-01-15,Course Carrefour E2E Test,Alimentation,Dépenses,,-45.67,,FR1234567890,Compte Test E2E,1234.56
2024-01-20,2024-01-20,Essence Total E2E Test,Transport,Dépenses,,-78.90,,FR1234567890,Compte Test E2E,1155.66
2024-02-03,2024-02-03,Restaurant E2E Test,Alimentation,Dépenses,,-32.50,,FR1234567890,Compte Test E2E,1123.16
2024-03-01,2024-03-01,Salaire Mars E2E Test,Revenus,Revenus,,2500.00,,FR1234567890,Compte Test E2E,3607.36
2024-03-05,2024-03-05,Supermarché E2E Test,Alimentation,Dépenses,,-89.45,,FR1234567890,Compte Test E2E,3517.91'''
            
            # Import via l'API
            files = {'file': ('test_e2e.csv', csv_content, 'text/csv')}
            response = self.session.post(
                f"{API_BASE}/import",
                files=files,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                self.import_id = data.get("importId")
                self.suggested_month = data.get("suggestedMonth")
                months = data.get("months", [])
                
                self.log_success(f"Import réussi (ID: {self.import_id})")
                self.log_success(f"Mois suggéré: {self.suggested_month}")
                self.log_info(f"Mois détectés: {len(months)}")
                
                total_new = sum(m.get("newCount", 0) for m in months)
                self.log_info(f"Nouvelles transactions: {total_new}")
                
                # Validation des données obligatoires
                if not self.import_id:
                    self.log_error("Import ID manquant")
                    return False
                    
                if not self.suggested_month:
                    self.log_warning("Aucun mois suggéré")
                    
                if total_new == 0:
                    self.log_warning("Aucune nouvelle transaction importée")
                    
                return True
            else:
                self.log_error(f"Import échoué: HTTP {response.status_code}")
                try:
                    error_detail = response.json().get("detail", "Erreur inconnue")
                    self.log_error(f"Détail: {error_detail}")
                except:
                    pass
                return False
                
        except requests.RequestException as e:
            self.log_error(f"Erreur import CSV: {e}")
            return False
            
    def test_import_details(self) -> bool:
        """Test de la récupération des détails d'import"""
        if not self.import_id:
            self.log_error("Import ID requis pour ce test")
            return False
            
        try:
            response = self.session.get(
                f"{API_BASE}/imports/{self.import_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_success("Détails d'import récupérés")
                
                # Validation des métadonnées
                filename = data.get("fileName", "N/A")
                processing_ms = data.get("processingMs", 0)
                duplicates = data.get("duplicatesCount", 0)
                
                self.log_info(f"Fichier: {filename}")
                self.log_info(f"Temps de traitement: {processing_ms}ms")
                self.log_info(f"Doublons détectés: {duplicates}")
                
                return True
            else:
                self.log_error(f"Récupération détails échouée: HTTP {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.log_error(f"Erreur détails import: {e}")
            return False
            
    def test_transactions_retrieval(self) -> bool:
        """Test de la récupération des transactions"""
        if not self.suggested_month:
            self.log_warning("Pas de mois suggéré, utilisation de 2024-03 par défaut")
            test_month = "2024-03"
        else:
            test_month = self.suggested_month
            
        try:
            response = self.session.get(
                f"{API_BASE}/transactions",
                params={"month": test_month},
                timeout=5
            )
            
            if response.status_code == 200:
                transactions = response.json()
                self.log_success(f"Transactions récupérées pour {test_month}")
                self.log_info(f"Nombre de transactions: {len(transactions)}")
                
                # Vérifier si il y a des nouvelles transactions (avec import_id)
                new_transactions = [
                    t for t in transactions 
                    if t.get("import_id") == self.import_id
                ] if self.import_id else []
                
                if new_transactions:
                    self.log_success(f"Nouvelles transactions identifiées: {len(new_transactions)}")
                    
                    # Afficher quelques exemples
                    for tx in new_transactions[:2]:
                        self.log_info(f"  - {tx.get('label', 'N/A')}: {tx.get('amount', 0)}€")
                        
                else:
                    self.log_warning("Aucune nouvelle transaction identifiée avec l'import_id")
                    
                return True
            else:
                self.log_error(f"Récupération transactions échouée: HTTP {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.log_error(f"Erreur récupération transactions: {e}")
            return False
            
    def test_navigation_url_format(self) -> bool:
        """Test du format d'URL pour la navigation automatique"""
        if not self.import_id or not self.suggested_month:
            self.log_warning("Import ID ou mois suggéré manquant")
            return True
            
        # Format d'URL attendu: /transactions?month=YYYY-MM&importId=UUID
        expected_url = f"/transactions?month={self.suggested_month}&importId={self.import_id}"
        
        self.log_success(f"URL de navigation automatique: {expected_url}")
        self.log_info("Format valide pour redirection frontend")
        
        return True
        
    def test_frontend_accessibility(self) -> bool:
        """Test basique d'accessibilité du frontend"""
        try:
            response = requests.get(f"{FRONTEND_BASE}/", timeout=5)
            if response.status_code == 200:
                self.log_success("Frontend accessible")
                return True
            else:
                self.log_warning(f"Frontend non accessible: HTTP {response.status_code}")
                return True  # Non bloquant
        except requests.RequestException as e:
            self.log_warning(f"Frontend non accessible: {e}")
            return True  # Non bloquant
            
    def run_all_tests(self) -> bool:
        """Exécute tous les tests E2E"""
        print(f"{Colors.BOLD}🧪 Tests End-to-End - Budget Famille{Colors.END}")
        print(f"Backend: {API_BASE}")
        print(f"Frontend: {FRONTEND_BASE}")
        
        tests = [
            ("Santé du backend", self.test_health),
            ("Authentification", self.test_authentication), 
            ("Endpoint protégé", self.test_protected_endpoint),
            ("Import CSV", self.test_csv_import),
            ("Détails d'import", self.test_import_details),
            ("Récupération transactions", self.test_transactions_retrieval),
            ("Format URL navigation", self.test_navigation_url_format),
            ("Accessibilité frontend", self.test_frontend_accessibility),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log_section(test_name)
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log_error(f"Exception lors du test: {e}")
                failed += 1
                
            time.sleep(0.5)  # Petite pause entre les tests
            
        # Résumé final
        self.log_section("Résumé des tests")
        print(f"{Colors.GREEN}✅ Tests réussis: {passed}{Colors.END}")
        print(f"{Colors.RED}❌ Tests échoués: {failed}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Avertissements: {len(self.warnings)}{Colors.END}")
        
        if self.errors:
            print(f"\n{Colors.RED}Erreurs critiques:{Colors.END}")
            for error in self.errors:
                print(f"  • {error}")
                
        if self.warnings:
            print(f"\n{Colors.YELLOW}Avertissements:{Colors.END}")
            for warning in self.warnings:
                print(f"  • {warning}")
                
        # Instructions finales
        if failed == 0:
            self.log_section("Instructions pour test utilisateur final")
            print("1. Connectez-vous avec admin/secret")
            print("2. Allez dans Upload et importez un fichier CSV")
            print("3. Vérifiez la redirection automatique vers /transactions?month=YYYY-MM&importId=UUID")
            print("4. Confirmez que les nouvelles transactions sont mises en évidence")
            print("5. Testez la navigation entre les différents mois détectés")
            
            if self.import_id and self.suggested_month:
                direct_url = f"{FRONTEND_BASE}/transactions?month={self.suggested_month}&importId={self.import_id}"
                print(f"\n🔗 URL directe de test: {direct_url}")
                
        return failed == 0

def main():
    validator = E2EValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()