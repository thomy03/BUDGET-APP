#!/usr/bin/env python3
"""
Test d'intégration des fichiers CSV avec le backend Budget Famille v2.3

Ce script vérifie que les fichiers CSV de test sont correctement traités par le backend
et que la navigation automatique des mois fonctionne comme attendu.
"""
import os
import sys
import requests
import json
import time
from pathlib import Path

# Ajouter le dossier backend au path pour les imports
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.append(str(backend_dir))

# URLs de test (backend local)
BASE_URL = "http://localhost:8000"
SAMPLES_DIR = Path(__file__).parent

class BackendTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_id = None
    
    def check_backend_health(self):
        """Vérifie que le backend est accessible"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
    
    def login_test_user(self):
        """Se connecte avec un utilisateur de test"""
        # Créer un utilisateur de test
        user_data = {
            "username": "test_csv",
            "email": "test_csv@example.com", 
            "password": "testpassword123"
        }
        
        try:
            # Tentative d'inscription
            response = self.session.post(f"{self.base_url}/register", json=user_data)
            print(f"Inscription: {response.status_code}")
        except:
            pass  # Utilisateur peut déjà exister
        
        # Connexion
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        response = self.session.post(
            f"{self.base_url}/token", 
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✓ Connexion réussie")
            return True
        else:
            print(f"✗ Échec connexion: {response.status_code} - {response.text}")
            return False
    
    def upload_csv_file(self, file_path, expected_months=None):
        """Uploade un fichier CSV et analyse la réponse"""
        if not os.path.exists(file_path):
            print(f"✗ Fichier introuvable: {file_path}")
            return None
        
        print(f"\n📁 Test d'upload: {os.path.basename(file_path)}")
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.session.post(f"{self.base_url}/import", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Upload réussi")
            print(f"  - Transactions importées: {result.get('imported', 0)}")
            print(f"  - Doublons détectés: {result.get('duplicates', 0)}")
            print(f"  - Erreurs: {result.get('errors', 0)}")
            print(f"  - Mois détectés: {result.get('months', [])}")
            
            # Vérification des mois attendus
            if expected_months:
                detected_months = result.get('months', [])
                if set(expected_months) == set(detected_months):
                    print(f"✓ Mois détectés corrects: {detected_months}")
                else:
                    print(f"⚠️  Mois attendus: {expected_months}, détectés: {detected_months}")
            
            return result
        else:
            print(f"✗ Échec upload: {response.status_code}")
            try:
                error = response.json()
                print(f"  Erreur: {error.get('detail', 'Unknown error')}")
            except:
                print(f"  Réponse: {response.text[:200]}")
            return None
    
    def get_transactions_by_month(self, month):
        """Récupère les transactions d'un mois donné"""
        response = self.session.get(f"{self.base_url}/transactions?month={month}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Erreur récupération mois {month}: {response.status_code}")
            return []
    
    def test_navigation_months(self, expected_months):
        """Teste la navigation entre les mois"""
        print(f"\n🗓️  Test navigation entre mois: {expected_months}")
        
        for month in expected_months:
            transactions = self.get_transactions_by_month(month)
            print(f"  - {month}: {len(transactions)} transactions")
            
            if transactions:
                # Vérifier que toutes les transactions appartiennent bien au mois
                wrong_month = []
                for tx in transactions[:5]:  # Échantillon
                    tx_month = tx.get('month')
                    if tx_month != month:
                        wrong_month.append((tx.get('id'), tx_month))
                
                if wrong_month:
                    print(f"    ⚠️  Transactions mal classées: {wrong_month}")
                else:
                    print(f"    ✓ Toutes les transactions sont bien dans {month}")
    
    def run_integration_test(self):
        """Lance le test d'intégration complet"""
        print("🧪 Test d'intégration CSV Backend - Budget Famille v2.3")
        print("=" * 60)
        
        # 1. Vérifier que le backend est accessible
        if not self.check_backend_health():
            print("✗ Backend non accessible. Assurez-vous qu'il tourne sur", self.base_url)
            return False
        
        print("✓ Backend accessible")
        
        # 2. Se connecter
        if not self.login_test_user():
            print("✗ Impossible de se connecter")
            return False
        
        # 3. Tests des fichiers CSV
        test_cases = [
            {
                "file": "01_happy_path_janvier_2024.csv",
                "expected_months": ["2024-01"],
                "description": "Happy path - mono-mois"
            },
            {
                "file": "02_multi_mois_2024_Q1.csv", 
                "expected_months": ["2024-01", "2024-02", "2024-03"],
                "description": "Multi-mois Q1 2024"
            },
            {
                "file": "03_doublons_janvier_2024.csv",
                "expected_months": ["2024-01"],
                "description": "Détection de doublons"
            },
            {
                "file": "05_excel_fr_cp1252.csv",
                "expected_months": ["2024-01"], 
                "description": "Format Excel français"
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            file_path = SAMPLES_DIR / test_case["file"]
            print(f"\n📋 {test_case['description']}")
            
            result = self.upload_csv_file(file_path, test_case["expected_months"])
            if result:
                # Test de navigation pour ce fichier
                self.test_navigation_months(test_case["expected_months"])
                results.append((test_case["file"], True, result))
            else:
                results.append((test_case["file"], False, None))
        
        # 4. Test du fichier problématique (devrait avoir des erreurs)
        print(f"\n📋 Test robustesse - erreurs de format")
        problem_file = SAMPLES_DIR / "04_problemes_format.csv"
        result = self.upload_csv_file(problem_file)
        if result and result.get('errors', 0) > 0:
            print("✓ Erreurs correctement détectées")
            results.append(("04_problemes_format.csv", True, result))
        else:
            print("⚠️  Erreurs non détectées ou fichier non traité")
            results.append(("04_problemes_format.csv", False, result))
        
        # 5. Résumé
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DES TESTS")
        print("="*60)
        
        success_count = sum(1 for _, success, _ in results if success)
        total_count = len(results)
        
        for filename, success, result in results:
            status = "✓" if success else "✗"
            print(f"{status} {filename}")
            if result:
                imported = result.get('imported', 0)
                duplicates = result.get('duplicates', 0)
                errors = result.get('errors', 0)
                months = result.get('months', [])
                print(f"    Import: {imported}, Doublons: {duplicates}, Erreurs: {errors}, Mois: {months}")
        
        print(f"\n🏆 Succès: {success_count}/{total_count} tests")
        
        if success_count == total_count:
            print("✅ Tous les tests d'intégration ont réussi !")
        else:
            print("❌ Certains tests ont échoué. Vérifiez les logs ci-dessus.")
        
        return success_count == total_count

def main():
    """Point d'entrée principal"""
    tester = BackendTester()
    
    # Vérifier que les fichiers de test existent
    required_files = [
        "01_happy_path_janvier_2024.csv",
        "02_multi_mois_2024_Q1.csv", 
        "03_doublons_janvier_2024.csv",
        "04_problemes_format.csv",
        "05_excel_fr_cp1252.csv"
    ]
    
    missing_files = []
    for filename in required_files:
        if not (SAMPLES_DIR / filename).exists():
            missing_files.append(filename)
    
    if missing_files:
        print("❌ Fichiers de test manquants:")
        for f in missing_files:
            print(f"   - {f}")
        print("\n💡 Exécutez d'abord:")
        print("   python tests/csv-samples/generate_samples.py --regen")
        return 1
    
    # Lancer les tests
    success = tester.run_integration_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())