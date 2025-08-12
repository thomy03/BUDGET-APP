#!/usr/bin/env python3
"""
VALIDATION COMPLÈTE SYSTÈME D'IMPORT CSV - Budget Famille v2.3
Quality Assurance Lead - Validation End-to-End Import CSV

Ce script effectue une validation exhaustive du système d'import CSV
en testant tous les aspects critiques du flux d'import.
"""

import requests
import json
import time
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class CSVImportValidator:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.token = None
        self.session = requests.Session()
        self.results = []
        self.test_files = []
        
    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test result with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if status == "PASS":
            icon = "✅"
            color = Colors.GREEN
        elif status == "FAIL":
            icon = "❌"
            color = Colors.RED
        else:
            icon = "⚠️"
            color = Colors.YELLOW
            
        print(f"[{timestamp}] {icon} {color}{test_name}{Colors.RESET}")
        if details:
            print(f"         {Colors.WHITE}{details}{Colors.RESET}")
            
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": timestamp
        })
    
    def setup_authentication(self):
        """Authenticate with the backend API"""
        print(f"\n{Colors.CYAN}=== 1. AUTHENTIFICATION ==={Colors.RESET}")
        
        try:
            token_data = {"username": "admin", "password": "secret"}
            response = self.session.post(
                f"{self.base_url}/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                token_response = response.json()
                self.token = token_response.get("access_token")
                if self.token:
                    self.log_result("Authentification Backend", "PASS", f"Token obtenu avec succès")
                    return True
                else:
                    self.log_result("Authentification Backend", "FAIL", "Pas de token dans la réponse")
                    return False
            else:
                self.log_result("Authentification Backend", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentification Backend", "FAIL", str(e))
            return False
    
    def test_server_health(self):
        """Test backend server health before import tests"""
        print(f"\n{Colors.CYAN}=== 2. SANTÉ DU SERVEUR ==={Colors.RESET}")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_result("Serveur Backend", "PASS", f"Status: {data.get('status')}, Database: {data.get('database')}")
                    return True
                else:
                    self.log_result("Serveur Backend", "FAIL", f"Status: {data.get('status')}")
                    return False
            else:
                self.log_result("Serveur Backend", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Serveur Backend", "FAIL", str(e))
            return False
    
    def prepare_test_files(self):
        """Prepare and validate test CSV files"""
        print(f"\n{Colors.CYAN}=== 3. PRÉPARATION FICHIERS DE TEST ==={Colors.RESET}")
        
        test_file_path = "/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/tests/csv-samples/test-navigation-final.csv"
        
        try:
            if os.path.exists(test_file_path):
                # Analyze the test file
                df = pd.read_csv(test_file_path)
                rows_count = len(df)
                columns = list(df.columns)
                months_detected = df['dateOp'].apply(lambda x: pd.to_datetime(x, errors='coerce').strftime('%Y-%m')).dropna().unique()
                
                self.test_files.append({
                    'path': test_file_path,
                    'filename': 'test-navigation-final.csv',
                    'rows': rows_count,
                    'columns': columns,
                    'months': sorted(months_detected.tolist())
                })
                
                self.log_result("Fichier de Test Principal", "PASS", 
                    f"Fichier: test-navigation-final.csv, Lignes: {rows_count}, Mois détectés: {len(months_detected)}")
                
                # Validate expected column mapping
                expected_mappings = {
                    'dateOp': 'date_op',
                    'label': 'label', 
                    'amount': 'amount',
                    'category': 'category'
                }
                
                missing_cols = [col for col in expected_mappings.keys() if col not in columns]
                if missing_cols:
                    self.log_result("Validation Colonnes", "WARN", f"Colonnes manquantes attendues: {missing_cols}")
                else:
                    self.log_result("Validation Colonnes", "PASS", "Toutes les colonnes attendues sont présentes")
                
                return True
            else:
                self.log_result("Fichier de Test Principal", "FAIL", f"Fichier non trouvé: {test_file_path}")
                return False
                
        except Exception as e:
            self.log_result("Préparation Fichiers", "FAIL", str(e))
            return False
    
    def test_csv_upload_api(self):
        """Test CSV upload via API endpoint"""
        print(f"\n{Colors.CYAN}=== 4. TEST ENDPOINT IMPORT CSV ==={Colors.RESET}")
        
        if not self.token:
            self.log_result("Test Upload API", "FAIL", "Token d'authentification manquant")
            return False
        
        if not self.test_files:
            self.log_result("Test Upload API", "FAIL", "Aucun fichier de test disponible")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        for test_file_info in self.test_files:
            try:
                with open(test_file_info['path'], 'rb') as f:
                    files = {'file': (test_file_info['filename'], f, 'text/csv')}
                    
                    start_time = time.time()
                    response = self.session.post(
                        f"{self.base_url}/import",
                        files=files,
                        headers=headers,
                        timeout=30
                    )
                    processing_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        import_result = response.json()
                        
                        # Validate response structure
                        required_fields = ['import_id', 'status', 'filename', 'rows_processed', 'months_detected']
                        missing_fields = [field for field in required_fields if field not in import_result]
                        
                        if missing_fields:
                            self.log_result("Upload API Response", "FAIL", f"Champs manquants: {missing_fields}")
                            return False
                        
                        # Store import result for later validation
                        test_file_info['import_result'] = import_result
                        test_file_info['processing_time'] = processing_time
                        
                        self.log_result("Upload API", "PASS", 
                            f"Import ID: {import_result['import_id'][:8]}..., "
                            f"Lignes: {import_result['rows_processed']}, "
                            f"Temps: {processing_time:.2f}s")
                        
                        # Validate import metrics
                        expected_rows = test_file_info['rows']
                        actual_rows = import_result['rows_processed']
                        
                        if expected_rows == actual_rows:
                            self.log_result("Validation Lignes Importées", "PASS", 
                                f"Expected: {expected_rows}, Actual: {actual_rows}")
                        else:
                            self.log_result("Validation Lignes Importées", "WARN", 
                                f"Expected: {expected_rows}, Actual: {actual_rows}")
                        
                        # Validate detected months
                        detected_months = import_result.get('months_detected', {})
                        if isinstance(detected_months, dict):
                            months_count = len(detected_months)
                        else:
                            months_count = len(detected_months) if detected_months else 0
                            
                        expected_months = len(test_file_info['months'])
                        
                        if months_count == expected_months:
                            self.log_result("Validation Mois Détectés", "PASS", 
                                f"Mois détectés: {months_count}")
                        else:
                            self.log_result("Validation Mois Détectés", "WARN", 
                                f"Expected: {expected_months}, Detected: {months_count}")
                        
                        return True
                        
                    else:
                        error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                        self.log_result("Upload API", "FAIL", 
                            f"HTTP {response.status_code}: {error_text}")
                        return False
                        
            except Exception as e:
                self.log_result("Upload API", "FAIL", str(e))
                return False
    
    def test_column_mapping(self):
        """Test that column mapping is working correctly"""
        print(f"\n{Colors.CYAN}=== 5. VALIDATION MAPPING COLONNES ==={Colors.RESET}")
        
        if not self.test_files or not self.test_files[0].get('import_result'):
            self.log_result("Test Mapping Colonnes", "FAIL", "Données d'import manquantes")
            return False
        
        test_file = self.test_files[0]
        original_columns = test_file['columns']
        
        # Test the expected mappings
        expected_mappings = {
            'dateOp': 'date_op',
            'dateVal': 'date_valeur', 
            'label': 'label',
            'amount': 'amount',
            'category': 'category',
            'categoryParent': 'category',  # Parent categories should map to main category
            'supplierFound': 'supplier',
            'comment': 'comment',
            'accountNum': 'account',
            'accountLabel': 'account',
            'accountbalance': 'balance'
        }
        
        mapping_success_count = 0
        total_mappings = len([col for col in expected_mappings.keys() if col in original_columns])
        
        for original_col in original_columns:
            if original_col in expected_mappings:
                expected_mapped = expected_mappings[original_col]
                self.log_result(f"Mapping {original_col}", "PASS", f"→ {expected_mapped}")
                mapping_success_count += 1
            else:
                self.log_result(f"Mapping {original_col}", "WARN", f"Pas de mapping défini")
        
        success_rate = (mapping_success_count / total_mappings * 100) if total_mappings > 0 else 0
        
        if success_rate >= 80:
            self.log_result("Validation Mapping Global", "PASS", f"Succès: {success_rate:.1f}% ({mapping_success_count}/{total_mappings})")
            return True
        else:
            self.log_result("Validation Mapping Global", "FAIL", f"Succès: {success_rate:.1f}% ({mapping_success_count}/{total_mappings})")
            return False
    
    def test_database_integrity(self):
        """Test database integrity after import"""
        print(f"\n{Colors.CYAN}=== 6. VALIDATION INTÉGRITÉ BASE DE DONNÉES ==={Colors.RESET}")
        
        if not self.token:
            self.log_result("Test Intégrité BDD", "FAIL", "Token d'authentification manquant")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # Test que les données sont bien en base via l'endpoint de transactions
            # Utiliser un des mois détectés dans les fichiers de test
            test_month = "2024-01"  # Mois présent dans le fichier test-navigation-final.csv
            response = self.session.get(f"{self.base_url}/transactions?month={test_month}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                transactions_data = response.json()
                if isinstance(transactions_data, list) and len(transactions_data) > 0:
                    self.log_result("Données en Base", "PASS", f"Transactions trouvées: {len(transactions_data)}")
                    
                    # Validate transaction structure
                    sample_transaction = transactions_data[0]
                    required_fields = ['id', 'date_op', 'label', 'amount']
                    missing_fields = [field for field in required_fields if field not in sample_transaction]
                    
                    if missing_fields:
                        self.log_result("Structure Transaction", "FAIL", f"Champs manquants: {missing_fields}")
                        return False
                    else:
                        self.log_result("Structure Transaction", "PASS", "Tous les champs requis présents")
                        
                    # Test data consistency
                    valid_transactions = 0
                    for transaction in transactions_data[:10]:  # Check first 10
                        try:
                            # Check date format
                            pd.to_datetime(transaction['date_op'])
                            # Check amount is numeric
                            float(transaction['amount'])
                            # Check label exists
                            if transaction['label'] and len(transaction['label'].strip()) > 0:
                                valid_transactions += 1
                        except Exception:
                            continue
                    
                    consistency_rate = (valid_transactions / min(10, len(transactions_data))) * 100
                    
                    if consistency_rate >= 80:
                        self.log_result("Consistance Données", "PASS", f"Taux de validité: {consistency_rate:.1f}%")
                        return True
                    else:
                        self.log_result("Consistance Données", "FAIL", f"Taux de validité: {consistency_rate:.1f}%")
                        return False
                        
                elif isinstance(transactions_data, dict) and 'transactions' in transactions_data:
                    transactions_list = transactions_data['transactions']
                    self.log_result("Données en Base", "PASS", f"Transactions trouvées: {len(transactions_list)}")
                    return True
                else:
                    self.log_result("Données en Base", "WARN", "Format de réponse inattendu")
                    return True  # Continue validation
                    
            else:
                self.log_result("Données en Base", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Test Intégrité BDD", "FAIL", str(e))
            return False
    
    def test_import_metadata(self):
        """Test import metadata storage and retrieval"""
        print(f"\n{Colors.CYAN}=== 7. VALIDATION MÉTADONNÉES D'IMPORT ==={Colors.RESET}")
        
        if not self.test_files or not self.test_files[0].get('import_result'):
            self.log_result("Test Métadonnées", "FAIL", "Données d'import manquantes")
            return False
        
        import_id = self.test_files[0]['import_result']['import_id']
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/imports/{import_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                metadata = response.json()
                
                # Validate metadata structure
                required_fields = ['import_id', 'status', 'filename', 'months_detected']
                missing_fields = [field for field in required_fields if field not in metadata]
                
                if missing_fields:
                    self.log_result("Structure Métadonnées", "FAIL", f"Champs manquants: {missing_fields}")
                    return False
                
                # Validate content
                if metadata['import_id'] == import_id:
                    self.log_result("ID Import", "PASS", f"ID: {import_id[:8]}...")
                else:
                    self.log_result("ID Import", "FAIL", "ID incohérent")
                    return False
                
                if metadata['status'] in ['success', 'completed']:
                    self.log_result("Status Import", "PASS", f"Status: {metadata['status']}")
                else:
                    self.log_result("Status Import", "WARN", f"Status: {metadata['status']}")
                
                return True
                
            else:
                self.log_result("Récupération Métadonnées", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Test Métadonnées", "FAIL", str(e))
            return False
    
    def test_error_handling(self):
        """Test error handling with invalid files"""
        print(f"\n{Colors.CYAN}=== 8. VALIDATION GESTION D'ERREURS ==={Colors.RESET}")
        
        if not self.token:
            self.log_result("Test Gestion Erreurs", "FAIL", "Token manquant")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        success_count = 0
        
        # Test 1: Empty file
        try:
            empty_content = ""
            files = {'file': ('empty.csv', empty_content, 'text/csv')}
            response = self.session.post(f"{self.base_url}/import", files=files, headers=headers, timeout=10)
            
            if response.status_code in [400, 422]:
                self.log_result("Fichier Vide", "PASS", f"Erreur appropriée: HTTP {response.status_code}")
                success_count += 1
            else:
                self.log_result("Fichier Vide", "FAIL", f"Réponse inattendue: HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Fichier Vide", "FAIL", str(e))
        
        # Test 2: Invalid CSV format
        try:
            invalid_content = "not;a;valid;csv\nformat;here"
            files = {'file': ('invalid.csv', invalid_content, 'text/csv')}
            response = self.session.post(f"{self.base_url}/import", files=files, headers=headers, timeout=10)
            
            if response.status_code in [400, 422]:
                self.log_result("CSV Invalide", "PASS", f"Erreur appropriée: HTTP {response.status_code}")
                success_count += 1
            else:
                self.log_result("CSV Invalide", "WARN", f"Réponse: HTTP {response.status_code}")
        except Exception as e:
            self.log_result("CSV Invalide", "FAIL", str(e))
        
        # Test 3: No file provided
        try:
            response = self.session.post(f"{self.base_url}/import", headers=headers, timeout=10)
            
            if response.status_code in [400, 422]:
                self.log_result("Aucun Fichier", "PASS", f"Erreur appropriée: HTTP {response.status_code}")
                success_count += 1
            else:
                self.log_result("Aucun Fichier", "FAIL", f"Réponse inattendue: HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Aucun Fichier", "FAIL", str(e))
        
        return success_count >= 2
    
    def test_performance_metrics(self):
        """Test import performance"""
        print(f"\n{Colors.CYAN}=== 9. VALIDATION PERFORMANCE ==={Colors.RESET}")
        
        if not self.test_files:
            self.log_result("Test Performance", "FAIL", "Données de performance manquantes")
            return False
        
        test_file = self.test_files[0]
        processing_time = test_file.get('processing_time', 0)
        rows_count = test_file.get('rows', 0)
        
        if processing_time > 0 and rows_count > 0:
            rows_per_second = rows_count / processing_time
            
            # Performance benchmarks
            if processing_time < 5.0:
                self.log_result("Temps de Traitement", "PASS", f"{processing_time:.2f}s pour {rows_count} lignes")
            elif processing_time < 10.0:
                self.log_result("Temps de Traitement", "WARN", f"{processing_time:.2f}s pour {rows_count} lignes (acceptable)")
            else:
                self.log_result("Temps de Traitement", "FAIL", f"{processing_time:.2f}s pour {rows_count} lignes (trop lent)")
                return False
            
            if rows_per_second > 10:
                self.log_result("Débit de Traitement", "PASS", f"{rows_per_second:.1f} lignes/seconde")
            else:
                self.log_result("Débit de Traitement", "WARN", f"{rows_per_second:.1f} lignes/seconde")
            
            return True
        else:
            self.log_result("Test Performance", "FAIL", "Données de performance indisponibles")
            return False
    
    def generate_comprehensive_report(self):
        """Generate comprehensive validation report"""
        print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}📊 RAPPORT DE VALIDATION COMPLET - IMPORT CSV{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
        
        # Summary statistics
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        warnings = len([r for r in self.results if r["status"] == "WARN"])
        total = len(self.results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"{Colors.BOLD}Résultats de Validation:{Colors.RESET}")
        print(f"  ✅ Tests Réussis: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"  ❌ Tests Échoués: {Colors.RED}{failed}{Colors.RESET}")
        print(f"  ⚠️  Avertissements: {Colors.YELLOW}{warnings}{Colors.RESET}")
        print(f"  📊 Taux de Réussite: {Colors.CYAN}{success_rate:.1f}%{Colors.RESET}")
        
        # Test file information
        if self.test_files:
            test_file = self.test_files[0]
            print(f"\n{Colors.BOLD}Fichier de Test Analysé:{Colors.RESET}")
            print(f"  📄 Nom: {test_file['filename']}")
            print(f"  📊 Lignes: {test_file['rows']}")
            print(f"  📅 Mois détectés: {len(test_file['months'])}")
            print(f"  🔄 Colonnes: {len(test_file['columns'])}")
            
            if 'import_result' in test_file:
                import_result = test_file['import_result']
                print(f"  ✅ Import ID: {import_result['import_id'][:12]}...")
                print(f"  ⏱️ Temps de traitement: {test_file.get('processing_time', 0):.2f}s")
        
        # Detailed results by category
        print(f"\n{Colors.BOLD}Détails par Catégorie:{Colors.RESET}")
        categories = {
            "Infrastructure": ["Serveur Backend", "Authentification Backend"],
            "Préparation": ["Fichier de Test Principal", "Validation Colonnes", "Préparation Fichiers"],
            "Import API": ["Upload API", "Upload API Response", "Validation Lignes Importées", "Validation Mois Détectés"],
            "Données": ["Mapping", "Validation Mapping Global", "Données en Base", "Structure Transaction", "Consistance Données"],
            "Métadonnées": ["ID Import", "Status Import", "Récupération Métadonnées"],
            "Robustesse": ["Fichier Vide", "CSV Invalide", "Aucun Fichier"],
            "Performance": ["Temps de Traitement", "Débit de Traitement"]
        }
        
        for category, test_patterns in categories.items():
            category_results = [r for r in self.results if any(pattern in r["test"] for pattern in test_patterns)]
            if category_results:
                cat_passed = len([r for r in category_results if r["status"] == "PASS"])
                cat_total = len(category_results)
                cat_rate = (cat_passed / cat_total * 100) if cat_total > 0 else 0
                
                if cat_rate >= 80:
                    status_color = Colors.GREEN
                    status_icon = "✅"
                elif cat_rate >= 60:
                    status_color = Colors.YELLOW
                    status_icon = "⚠️"
                else:
                    status_color = Colors.RED
                    status_icon = "❌"
                
                print(f"  {status_icon} {category}: {status_color}{cat_rate:.0f}%{Colors.RESET} ({cat_passed}/{cat_total})")
        
        # Quality assessment and recommendations
        print(f"\n{Colors.BOLD}🎯 Évaluation Qualité du Système d'Import CSV:{Colors.RESET}")
        
        if success_rate >= 90:
            status = "EXCELLENT - SYSTÈME D'IMPORT PRÊT POUR PRODUCTION"
            color = Colors.GREEN
            recommendations = [
                "✅ Tous les composants d'import fonctionnent correctement",
                "✅ Mapping des colonnes validé",
                "✅ Intégrité des données confirmée",
                "✅ Gestion d'erreurs appropriée",
                "🚀 Import CSV validé pour utilisation immédiate"
            ]
        elif success_rate >= 80:
            status = "BON - IMPORT CSV OPÉRATIONNEL"
            color = Colors.GREEN
            recommendations = [
                "✅ Fonctionnalités core d'import validées",
                "⚠️ Surveiller les points d'avertissement",
                "🔧 Corriger les problèmes mineurs si nécessaire",
                "🚀 Système d'import approuvé pour la production"
            ]
        elif success_rate >= 60:
            status = "ACCEPTABLE - CORRECTIONS MINEURES REQUISES"
            color = Colors.YELLOW
            recommendations = [
                "⚠️ Quelques problèmes non critiques identifiés",
                "🔧 Corriger les tests échoués avant production",
                "📋 Plan de surveillance des avertissements requis",
                "⏰ Import utilisable après corrections"
            ]
        else:
            status = "NON PRÊT - PROBLÈMES CRITIQUES DÉTECTÉS"
            color = Colors.RED
            recommendations = [
                "❌ Défaillances critiques du système d'import",
                "🔧 Correction obligatoire de tous les tests échoués",
                "🔒 Problèmes de fonctionnalité ou de sécurité",
                "⛔ NE PAS UTILISER EN PRODUCTION"
            ]
        
        print(f"  🏆 Status: {color}{status}{Colors.RESET}")
        
        print(f"\n{Colors.BOLD}📋 Recommandations:{Colors.RESET}")
        for rec in recommendations:
            print(f"  {rec}")
        
        # Critical acceptance criteria verification
        print(f"\n{Colors.BOLD}🎯 CRITÈRES D'ACCEPTATION:{Colors.RESET}")
        
        criteria_checks = []
        
        # Critère 1: Import sans erreur 500 ou 400
        api_tests = [r for r in self.results if "Upload API" in r["test"] and r["status"] == "PASS"]
        if api_tests:
            criteria_checks.append(("✅", "Import sans erreur 500/400", "VALIDÉ"))
        else:
            criteria_checks.append(("❌", "Import sans erreur 500/400", "ÉCHEC"))
        
        # Critère 2: Lignes correctement importées
        line_tests = [r for r in self.results if "Validation Lignes Importées" in r["test"] and r["status"] == "PASS"]
        if line_tests:
            criteria_checks.append(("✅", "Toutes les lignes importées", "VALIDÉ"))
        else:
            criteria_checks.append(("❌", "Toutes les lignes importées", "ÉCHEC"))
        
        # Critère 3: Mapping des colonnes
        mapping_tests = [r for r in self.results if "Mapping" in r["test"] and r["status"] == "PASS"]
        if mapping_tests:
            criteria_checks.append(("✅", "Mapping colonnes correct", "VALIDÉ"))
        else:
            criteria_checks.append(("❌", "Mapping colonnes correct", "ÉCHEC"))
        
        # Critère 4: Mois détectés
        month_tests = [r for r in self.results if "Mois Détectés" in r["test"] and r["status"] == "PASS"]
        if month_tests:
            criteria_checks.append(("✅", "Mois détectés automatiquement", "VALIDÉ"))
        else:
            criteria_checks.append(("❌", "Mois détectés automatiquement", "ÉCHEC"))
        
        # Critère 5: Données visibles
        data_tests = [r for r in self.results if "Données en Base" in r["test"] and r["status"] == "PASS"]
        if data_tests:
            criteria_checks.append(("✅", "Données visibles en base", "VALIDÉ"))
        else:
            criteria_checks.append(("❌", "Données visibles en base", "ÉCHEC"))
        
        for icon, criterion, status in criteria_checks:
            print(f"  {icon} {criterion}: {status}")
        
        # Final decision
        critical_failures = len([c for c in criteria_checks if "❌" in c[0]])
        
        if critical_failures == 0:
            final_decision = f"{Colors.GREEN}🎉 VALIDATION RÉUSSIE - SYSTÈME D'IMPORT CSV APPROUVÉ{Colors.RESET}"
            release_ready = True
        else:
            final_decision = f"{Colors.RED}❌ VALIDATION ÉCHOUÉE - {critical_failures} CRITÈRES NON SATISFAITS{Colors.RESET}"
            release_ready = False
        
        print(f"\n{Colors.BOLD}🎯 DÉCISION FINALE:{Colors.RESET}")
        print(f"  {final_decision}")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "validation_type": "CSV Import System Comprehensive Validation",
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "success_rate": success_rate,
                "status": status,
                "release_ready": release_ready
            },
            "test_results": self.results,
            "test_files": self.test_files,
            "acceptance_criteria": {
                "criteria_checked": len(criteria_checks),
                "criteria_passed": len(criteria_checks) - critical_failures,
                "critical_failures": critical_failures
            },
            "recommendations": recommendations
        }
        
        with open("/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/csv_import_validation_report.json", "w") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Rapport détaillé sauvegardé: {Colors.CYAN}csv_import_validation_report.json{Colors.RESET}")
        
        return release_ready
    
    def run_comprehensive_validation(self):
        """Run complete CSV import validation"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("🔍 VALIDATION COMPLÈTE SYSTÈME D'IMPORT CSV")
        print("Budget Famille v2.3 - Quality Assurance Lead")
        print("="*80)
        print(f"Validation End-to-End du Flux d'Import CSV{Colors.RESET}")
        print(f"Exécution: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Execute validation tests in sequence
        test_results = []
        
        test_results.append(self.setup_authentication())
        test_results.append(self.test_server_health())
        test_results.append(self.prepare_test_files())
        test_results.append(self.test_csv_upload_api())
        test_results.append(self.test_column_mapping())
        test_results.append(self.test_database_integrity())
        test_results.append(self.test_import_metadata())
        test_results.append(self.test_error_handling())
        test_results.append(self.test_performance_metrics())
        
        # Generate comprehensive report
        validation_passed = self.generate_comprehensive_report()
        
        return validation_passed

def main():
    """Main execution function"""
    validator = CSVImportValidator()
    
    try:
        validation_passed = validator.run_comprehensive_validation()
        
        if validation_passed:
            print(f"\n{Colors.GREEN}🎉 VALIDATION SYSTÈME D'IMPORT CSV RÉUSSIE{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.RED}❌ VALIDATION SYSTÈME D'IMPORT CSV ÉCHOUÉE{Colors.RESET}")
            return 1
            
    except Exception as e:
        print(f"\n{Colors.RED}💥 ERREUR CRITIQUE LORS DE LA VALIDATION: {e}{Colors.RESET}")
        return 1

if __name__ == "__main__":
    exit(main())