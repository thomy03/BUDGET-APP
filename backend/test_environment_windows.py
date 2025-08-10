#!/usr/bin/env python3
"""
Tests de validation d'environnement Windows
Vérifie la compatibilité et la configuration pour le backend
"""
import os
import sys
import json
import platform
import subprocess
import tempfile
import sqlite3
from typing import Dict, Any, List, Tuple
import traceback

class WindowsEnvironmentTester:
    """Testeur d'environnement Windows complet"""
    
    def __init__(self):
        self.results = {}
        self.critical_errors = []
        self.warnings = []
        
    def test_python_environment(self) -> Dict[str, Any]:
        """Test de l'environnement Python"""
        print("="*60)
        print("TEST ENVIRONNEMENT PYTHON")
        print("="*60)
        
        results = {}
        
        # Version Python
        py_version = sys.version_info
        results['python_version'] = {
            'major': py_version.major,
            'minor': py_version.minor,
            'micro': py_version.micro,
            'version_string': sys.version,
            'executable': sys.executable
        }
        
        # Vérifier version minimale (3.8+)
        if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
            self.critical_errors.append(f"Python {py_version.major}.{py_version.minor} trop ancien (requis: 3.8+)")
            results['version_compatible'] = False
        else:
            results['version_compatible'] = True
            
        print(f"Python: {py_version.major}.{py_version.minor}.{py_version.micro}")
        print(f"Exécutable: {sys.executable}")
        print(f"Compatible: {'✓' if results['version_compatible'] else '✗'}")
        
        # Variables d'environnement Python
        env_vars = ['PYTHONPATH', 'VIRTUAL_ENV', 'PYTHONHOME', 'PATH']
        results['environment'] = {}
        
        for var in env_vars:
            value = os.environ.get(var)
            results['environment'][var] = value
            print(f"{var}: {value if value else 'NON_DEFINI'}")
        
        return results
    
    def test_windows_specifics(self) -> Dict[str, Any]:
        """Test spécifique Windows"""
        print("\n" + "="*60)
        print("TEST SPÉCIFICITÉS WINDOWS")
        print("="*60)
        
        results = {}
        
        # Informations système
        results['platform'] = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture()
        }
        
        # Test WSL
        try:
            wsl_check = os.path.exists('/proc/version')
            if wsl_check:
                with open('/proc/version', 'r') as f:
                    version_info = f.read()
                    is_wsl = 'microsoft' in version_info.lower() or 'wsl' in version_info.lower()
                    results['wsl'] = {'detected': is_wsl, 'version_info': version_info.strip()}
            else:
                results['wsl'] = {'detected': False}
        except:
            results['wsl'] = {'detected': False, 'error': 'Cannot detect WSL'}
        
        # Test permissions répertoire
        current_dir = os.getcwd()
        results['directory_permissions'] = self._test_directory_permissions(current_dir)
        
        # Test encodage
        results['encoding'] = {
            'default': sys.getdefaultencoding(),
            'filesystem': sys.getfilesystemencoding(),
            'stdin': sys.stdin.encoding,
            'stdout': sys.stdout.encoding
        }
        
        for key, value in results['platform'].items():
            print(f"{key}: {value}")
            
        if results['wsl']['detected']:
            print("✓ WSL détecté")
        
        print(f"Permissions répertoire: {'✓' if results['directory_permissions']['writable'] else '✗'}")
        print(f"Encodage par défaut: {results['encoding']['default']}")
        
        return results
    
    def _test_directory_permissions(self, directory: str) -> Dict[str, Any]:
        """Test des permissions de répertoire"""
        results = {'readable': False, 'writable': False, 'executable': False}
        
        try:
            # Test lecture
            files = os.listdir(directory)
            results['readable'] = True
        except:
            pass
            
        try:
            # Test écriture
            test_file = os.path.join(directory, 'test_write_permissions.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            results['writable'] = True
        except:
            pass
            
        try:
            # Test exécution (créer un script temporaire)
            test_script = os.path.join(directory, 'test_exec.py')
            with open(test_script, 'w') as f:
                f.write('print("test")')
            subprocess.run([sys.executable, test_script], capture_output=True, check=True)
            os.remove(test_script)
            results['executable'] = True
        except:
            pass
            
        return results
    
    def test_required_packages(self) -> Dict[str, Any]:
        """Test des packages requis avec détection Windows"""
        print("\n" + "="*60)
        print("TEST PACKAGES REQUIS")
        print("="*60)
        
        # Packages avec alternatives Windows
        packages_to_test = [
            # Packages de base
            ('fastapi', 'import fastapi', True),
            ('uvicorn', 'import uvicorn', True),
            ('pandas', 'import pandas', True),
            ('numpy', 'import numpy', True),
            ('sqlalchemy', 'import sqlalchemy', True),
            
            # Packages de sécurité/crypto
            ('cryptography', 'import cryptography', True),
            ('passlib', 'import passlib', True),
            ('jose', 'from jose import jwt', True),
            
            # Packages spécialisés
            ('pysqlcipher3', 'import pysqlcipher3', False),  # Problématique sur Windows
            ('magic', 'import magic', False),  # Nécessite libmagic
            
            # Packages de validation
            ('pydantic', 'import pydantic', True),
            ('email_validator', 'import email_validator', True),
            
            # Utilitaires
            ('python_dotenv', 'import dotenv', True),
            ('python_multipart', 'import multipart', True),
        ]
        
        results = {}
        
        for name, import_cmd, is_critical in packages_to_test:
            try:
                exec(import_cmd)
                results[name] = {'status': 'OK', 'critical': is_critical}
                print(f"✓ {name}: OK")
            except ImportError as e:
                results[name] = {'status': 'MISSING', 'error': str(e), 'critical': is_critical}
                status_symbol = "✗" if is_critical else "⚠"
                print(f"{status_symbol} {name}: MANQUANT - {e}")
                
                if is_critical:
                    self.critical_errors.append(f"Package critique manquant: {name}")
                else:
                    self.warnings.append(f"Package optionnel manquant: {name}")
                    
                # Suggestions d'alternatives Windows
                if name == 'pysqlcipher3':
                    print("  SUGGESTION: Utiliser SQLite standard pour les tests")
                elif name == 'magic':
                    print("  SUGGESTION: Utiliser python-magic-bin pour Windows")
            except Exception as e:
                results[name] = {'status': 'ERROR', 'error': str(e), 'critical': is_critical}
                print(f"✗ {name}: ERREUR - {e}")
        
        return results
    
    def test_database_options(self) -> Dict[str, Any]:
        """Test des options de base de données"""
        print("\n" + "="*60)
        print("TEST OPTIONS BASE DE DONNÉES")
        print("="*60)
        
        results = {}
        
        # Test SQLite standard
        try:
            conn = sqlite3.connect(':memory:')
            conn.execute('CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)')
            conn.execute('INSERT INTO test_table (name) VALUES (?)', ('test',))
            result = conn.execute('SELECT * FROM test_table').fetchall()
            conn.close()
            
            results['sqlite_standard'] = {'status': 'OK', 'test_result': len(result)}
            print("✓ SQLite standard: OK")
        except Exception as e:
            results['sqlite_standard'] = {'status': 'ERROR', 'error': str(e)}
            print(f"✗ SQLite standard: {e}")
        
        # Test pysqlcipher3 (avec fallback)
        try:
            import pysqlcipher3.dbapi2 as sqlite_cipher
            conn = sqlite_cipher.connect(':memory:')
            conn.execute('PRAGMA key="test_key"')
            conn.execute('CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)')
            conn.close()
            
            results['pysqlcipher3'] = {'status': 'OK'}
            print("✓ pysqlcipher3: OK")
        except ImportError:
            results['pysqlcipher3'] = {'status': 'NOT_AVAILABLE', 'fallback': 'sqlite_standard'}
            print("⚠ pysqlcipher3: NON DISPONIBLE (fallback: SQLite standard)")
        except Exception as e:
            results['pysqlcipher3'] = {'status': 'ERROR', 'error': str(e)}
            print(f"✗ pysqlcipher3: {e}")
        
        # Test fichiers de base existants
        db_files = ['budget.db', 'budget_encrypted.db']
        for db_file in db_files:
            if os.path.exists(db_file):
                try:
                    size = os.path.getsize(db_file)
                    # Test de lecture
                    conn = sqlite3.connect(db_file)
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    conn.close()
                    
                    results[f'file_{db_file}'] = {
                        'exists': True,
                        'size': size,
                        'tables': [t[0] for t in tables],
                        'status': 'OK'
                    }
                    print(f"✓ {db_file}: OK ({size} bytes, {len(tables)} tables)")
                except Exception as e:
                    results[f'file_{db_file}'] = {
                        'exists': True,
                        'size': os.path.getsize(db_file),
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    print(f"⚠ {db_file}: Existe mais erreur lecture - {e}")
            else:
                results[f'file_{db_file}'] = {'exists': False}
                print(f"ⓘ {db_file}: N'existe pas")
        
        return results
    
    def test_csv_functionality(self) -> Dict[str, Any]:
        """Test de la fonctionnalité CSV critique"""
        print("\n" + "="*60)
        print("TEST FONCTIONNALITÉ CSV")
        print("="*60)
        
        results = {}
        
        # Test imports nécessaires pour CSV
        csv_imports = [
            ('csv', 'import csv'),
            ('io', 'import io'),
            ('pandas', 'import pandas as pd'),
            ('tempfile', 'import tempfile'),
        ]
        
        import_results = {}
        for name, import_cmd in csv_imports:
            try:
                exec(import_cmd)
                import_results[name] = 'OK'
                print(f"✓ Import {name}: OK")
            except Exception as e:
                import_results[name] = f'ERROR: {e}'
                print(f"✗ Import {name}: {e}")
        
        results['imports'] = import_results
        
        # Test création et lecture CSV
        if all(result == 'OK' for result in import_results.values()):
            try:
                import csv
                import io
                import pandas as pd
                
                # Créer un CSV de test
                test_data = [
                    ['Date', 'Description', 'Amount', 'Category'],
                    ['2024-01-01', 'Test Transaction 1', '100.50', 'Food'],
                    ['2024-01-02', 'Test Transaction 2', '-50.25', 'Transport'],
                    ['2024-01-03', 'Test Transaction 3', '75.00', 'Entertainment'],
                ]
                
                # Test avec module csv standard
                csv_content = io.StringIO()
                writer = csv.writer(csv_content)
                for row in test_data:
                    writer.writerow(row)
                csv_string = csv_content.getvalue()
                
                # Test lecture avec pandas
                df = pd.read_csv(io.StringIO(csv_string))
                
                results['csv_processing'] = {
                    'status': 'OK',
                    'rows_created': len(test_data),
                    'rows_read': len(df),
                    'columns': list(df.columns),
                    'sample_data': df.head(2).to_dict('records')
                }
                
                print(f"✓ Création CSV: {len(test_data)} lignes")
                print(f"✓ Lecture pandas: {len(df)} lignes, colonnes: {list(df.columns)}")
                
                # Test sauvegarde temporaire
                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                    f.write(csv_string)
                    temp_file = f.name
                
                # Test lecture depuis fichier
                df_from_file = pd.read_csv(temp_file)
                os.unlink(temp_file)
                
                results['file_io'] = {
                    'status': 'OK',
                    'temp_file_created': True,
                    'file_read_success': len(df_from_file) == len(df)
                }
                print("✓ Sauvegarde/lecture fichier CSV: OK")
                
            except Exception as e:
                results['csv_processing'] = {'status': 'ERROR', 'error': str(e)}
                print(f"✗ Test CSV: {e}")
                traceback.print_exc()
        else:
            results['csv_processing'] = {'status': 'SKIPPED', 'reason': 'Imports manquants'}
            print("⚠ Test CSV ignoré (imports manquants)")
        
        return results
    
    def test_network_connectivity(self) -> Dict[str, Any]:
        """Test de connectivité réseau (pour uvicorn)"""
        print("\n" + "="*60)
        print("TEST CONNECTIVITÉ RÉSEAU")
        print("="*60)
        
        results = {}
        
        # Test bind sur localhost
        import socket
        
        ports_to_test = [8000, 8001, 8080]
        results['port_availability'] = {}
        
        for port in ports_to_test:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    results['port_availability'][port] = 'OCCUPIED'
                    print(f"⚠ Port {port}: OCCUPÉ")
                else:
                    results['port_availability'][port] = 'AVAILABLE'
                    print(f"✓ Port {port}: DISPONIBLE")
                    
            except Exception as e:
                results['port_availability'][port] = f'ERROR: {e}'
                print(f"✗ Port {port}: ERREUR - {e}")
        
        return results
    
    def generate_recommendations(self) -> List[str]:
        """Génère des recommandations basées sur les tests"""
        recommendations = []
        
        # Recommandations basées sur les erreurs critiques
        if self.critical_errors:
            recommendations.append("ACTIONS CRITIQUES REQUISES:")
            for error in self.critical_errors:
                recommendations.append(f"  - {error}")
        
        # Recommandations pour les warnings
        if self.warnings:
            recommendations.append("AMÉLIORATIONS RECOMMANDÉES:")
            for warning in self.warnings:
                recommendations.append(f"  - {warning}")
        
        # Recommandations spécifiques Windows
        recommendations.extend([
            "RECOMMANDATIONS WINDOWS:",
            "  - Installer python-magic-bin au lieu de python-magic",
            "  - Utiliser SQLite standard si pysqlcipher3 pose problème",
            "  - Vérifier les permissions d'exécution dans le répertoire",
            "  - Considérer l'utilisation de WSL pour un environnement plus compatible"
        ])
        
        return recommendations
    
    def run_complete_test(self) -> Dict[str, Any]:
        """Lance tous les tests d'environnement"""
        print("DÉBUT TESTS ENVIRONNEMENT WINDOWS")
        print("="*80)
        
        test_results = {}
        
        try:
            test_results['python_env'] = self.test_python_environment()
            test_results['windows_specifics'] = self.test_windows_specifics()
            test_results['packages'] = self.test_required_packages()
            test_results['database'] = self.test_database_options()
            test_results['csv_functionality'] = self.test_csv_functionality()
            test_results['network'] = self.test_network_connectivity()
            
            # Génération des recommandations
            recommendations = self.generate_recommendations()
            test_results['recommendations'] = recommendations
            
            # Résumé final
            print("\n" + "="*80)
            print("RÉSUMÉ ET RECOMMANDATIONS")
            print("="*80)
            
            print(f"Erreurs critiques: {len(self.critical_errors)}")
            print(f"Avertissements: {len(self.warnings)}")
            
            for rec in recommendations:
                print(rec)
            
            # Statut global
            if self.critical_errors:
                test_results['overall_status'] = 'CRITICAL_ISSUES'
                print("\n❌ STATUT: PROBLÈMES CRITIQUES DÉTECTÉS")
            elif self.warnings:
                test_results['overall_status'] = 'WARNINGS'
                print("\n⚠️ STATUT: AVERTISSEMENTS (FONCTIONNEL AVEC LIMITATIONS)")
            else:
                test_results['overall_status'] = 'OK'
                print("\n✅ STATUT: ENVIRONNEMENT OK")
            
        except Exception as e:
            print(f"ERREUR CRITIQUE LORS DES TESTS: {e}")
            traceback.print_exc()
            test_results['critical_error'] = str(e)
        
        # Sauvegarde
        try:
            with open('environment_test_report.json', 'w', encoding='utf-8') as f:
                json.dump(test_results, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Rapport sauvegardé: environment_test_report.json")
        except Exception as e:
            print(f"✗ Erreur sauvegarde: {e}")
        
        return test_results

if __name__ == "__main__":
    tester = WindowsEnvironmentTester()
    try:
        results = tester.run_complete_test()
        print(f"\nTest terminé. Consultez environment_test_report.json pour les détails.")
    except KeyboardInterrupt:
        print("\nTest interrompu par l'utilisateur")
    except Exception as e:
        print(f"Erreur critique: {e}")
        traceback.print_exc()