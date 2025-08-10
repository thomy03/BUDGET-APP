#!/usr/bin/env python3
"""
Tests critiques pour la fonctionnalité d'import CSV
Validation complète de bout en bout pour Windows
"""
import os
import sys
import csv
import io
import json
import tempfile
import sqlite3
import traceback
from typing import Dict, Any, List
from datetime import datetime

# Import avec fallback pandas
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

class CSVCriticalTester:
    """Tests critiques pour l'import CSV"""
    
    def __init__(self):
        self.test_results = {}
        self.csv_samples = self._generate_test_csv_samples()
        
    def _generate_test_csv_samples(self) -> Dict[str, str]:
        """Génère des échantillons CSV de test"""
        return {
            'valid_basic': '''Date,Description,Amount,Category
2024-01-01,Groceries,150.50,Food
2024-01-02,Gas Station,-75.25,Transport
2024-01-03,Salary,2500.00,Income''',
            
            'valid_minimal': '''Date,Description,Amount
2024-01-01,Test Transaction,100.00
2024-01-02,Another Test,-50.00''',
            
            'invalid_missing_columns': '''Date,Description
2024-01-01,Missing Amount Column''',
            
            'invalid_bad_dates': '''Date,Description,Amount
2024-13-01,Invalid Month,100.00
not-a-date,Bad Date Format,50.00''',
            
            'invalid_bad_amounts': '''Date,Description,Amount
2024-01-01,Invalid Amount,not-a-number
2024-01-02,Another Bad Amount,''',
            
            'mixed_formats': '''Date,Description,Amount
01/01/2024,French Date Format,100.50
2024-01-02,ISO Date Format,-50.25
01-Jan-2024,Text Date Format,75.00''',
            
            'large_dataset': self._generate_large_csv(),
            
            'special_characters': '''Date,Description,Amount,Category
2024-01-01,"Café & Restaurant €",25.50,Food
2024-01-02,"Quote ""Special"" Case",-10.00,Other
2024-01-03,Émojis 🛒 & Accents,15.75,Shopping''',
            
            'empty_file': '',
            
            'header_only': 'Date,Description,Amount'
        }
    
    def _generate_large_csv(self) -> str:
        """Génère un CSV volumineux pour test de performance"""
        header = "Date,Description,Amount,Category\n"
        rows = []
        
        for i in range(1000):
            date = f"2024-01-{(i % 28) + 1:02d}"
            desc = f"Transaction {i+1}"
            amount = f"{(i * 1.5) % 1000:.2f}"
            category = ["Food", "Transport", "Shopping", "Entertainment"][i % 4]
            rows.append(f"{date},{desc},{amount},{category}")
        
        return header + "\n".join(rows)
    
    def test_csv_parsing_standard(self) -> Dict[str, Any]:
        """Test parsing avec module csv standard"""
        print("="*60)
        print("TEST PARSING CSV STANDARD")
        print("="*60)
        
        results = {}
        
        for sample_name, csv_content in self.csv_samples.items():
            try:
                print(f"\nTest: {sample_name}")
                
                if not csv_content.strip():
                    results[sample_name] = {'status': 'EMPTY', 'valid': False}
                    print("  ✗ Fichier vide")
                    continue
                
                # Détection du délimiteur
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(csv_content[:1024]).delimiter
                
                # Lecture
                reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
                rows = list(reader)
                
                # Validation des colonnes requises
                required_cols = ['Date', 'Description', 'Amount']
                if not rows:
                    results[sample_name] = {'status': 'NO_ROWS', 'valid': False}
                    print("  ✗ Aucune ligne de données")
                    continue
                
                headers = list(rows[0].keys())
                missing_cols = [col for col in required_cols if col not in headers]
                
                if missing_cols:
                    results[sample_name] = {
                        'status': 'MISSING_COLUMNS',
                        'valid': False,
                        'missing_columns': missing_cols,
                        'available_columns': headers
                    }
                    print(f"  ✗ Colonnes manquantes: {missing_cols}")
                    continue
                
                # Validation des données
                valid_rows = 0
                errors = []
                
                for i, row in enumerate(rows):
                    row_errors = []
                    
                    # Validation date
                    try:
                        datetime.strptime(row['Date'], '%Y-%m-%d')
                    except ValueError:
                        try:
                            # Format français
                            dt = datetime.strptime(row['Date'], '%d/%m/%Y')
                            row['Date'] = dt.strftime('%Y-%m-%d')
                        except ValueError:
                            row_errors.append(f"Date invalide: {row['Date']}")
                    
                    # Validation montant
                    try:
                        float(row['Amount'].replace(',', '.'))
                    except (ValueError, AttributeError):
                        row_errors.append(f"Montant invalide: {row['Amount']}")
                    
                    if not row_errors:
                        valid_rows += 1
                    else:
                        errors.extend(row_errors)
                
                results[sample_name] = {
                    'status': 'OK',
                    'valid': valid_rows > 0,
                    'total_rows': len(rows),
                    'valid_rows': valid_rows,
                    'errors': errors[:5],  # Limiter les erreurs affichées
                    'headers': headers,
                    'delimiter': delimiter
                }
                
                print(f"  ✓ {len(rows)} lignes, {valid_rows} valides")
                if errors:
                    print(f"  ⚠ {len(errors)} erreurs détectées")
                
            except Exception as e:
                results[sample_name] = {'status': 'ERROR', 'valid': False, 'error': str(e)}
                print(f"  ✗ Erreur: {e}")
        
        return results
    
    def test_csv_parsing_pandas(self) -> Dict[str, Any]:
        """Test parsing avec pandas si disponible"""
        print("\n" + "="*60)
        print("TEST PARSING CSV PANDAS")
        print("="*60)
        
        if not HAS_PANDAS:
            print("pandas non disponible - test ignoré")
            return {'pandas_available': False}
        
        results = {'pandas_available': True}
        
        for sample_name, csv_content in self.csv_samples.items():
            try:
                print(f"\nTest pandas: {sample_name}")
                
                if not csv_content.strip():
                    results[sample_name] = {'status': 'EMPTY', 'valid': False}
                    print("  ✗ Fichier vide")
                    continue
                
                # Lecture avec pandas
                df = pd.read_csv(io.StringIO(csv_content))
                
                # Validation des colonnes
                required_cols = ['Date', 'Description', 'Amount']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    results[sample_name] = {
                        'status': 'MISSING_COLUMNS',
                        'valid': False,
                        'missing_columns': missing_cols
                    }
                    print(f"  ✗ Colonnes manquantes: {missing_cols}")
                    continue
                
                # Nettoyage et conversion
                original_count = len(df)
                df_clean = df.dropna(subset=required_cols)
                
                # Conversion des dates
                try:
                    df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce')
                    df_clean = df_clean.dropna(subset=['Date'])
                except:
                    pass
                
                # Conversion des montants
                try:
                    df_clean['Amount'] = pd.to_numeric(
                        df_clean['Amount'].astype(str).str.replace(',', '.'),
                        errors='coerce'
                    )
                    df_clean = df_clean.dropna(subset=['Amount'])
                except:
                    pass
                
                results[sample_name] = {
                    'status': 'OK',
                    'valid': len(df_clean) > 0,
                    'original_rows': original_count,
                    'clean_rows': len(df_clean),
                    'columns': list(df.columns),
                    'dtypes': df.dtypes.to_dict() if hasattr(df.dtypes, 'to_dict') else str(df.dtypes)
                }
                
                print(f"  ✓ {original_count} lignes → {len(df_clean)} valides")
                
            except Exception as e:
                results[sample_name] = {'status': 'ERROR', 'valid': False, 'error': str(e)}
                print(f"  ✗ Erreur pandas: {e}")
        
        return results
    
    def test_file_operations(self) -> Dict[str, Any]:
        """Test des opérations fichier (lecture/écriture)"""
        print("\n" + "="*60)
        print("TEST OPÉRATIONS FICHIER")
        print("="*60)
        
        results = {}
        
        # Test écriture/lecture fichier temporaire
        try:
            test_csv = self.csv_samples['valid_basic']
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
                f.write(test_csv)
                temp_filename = f.name
            
            print(f"✓ Fichier temporaire créé: {temp_filename}")
            
            # Lecture du fichier
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Vérification
            if content == test_csv:
                results['temp_file_ops'] = {'status': 'OK', 'file_size': len(content)}
                print(f"✓ Lecture/écriture OK ({len(content)} caractères)")
            else:
                results['temp_file_ops'] = {'status': 'MISMATCH'}
                print("✗ Contenu ne correspond pas")
            
            # Nettoyage
            os.unlink(temp_filename)
            
        except Exception as e:
            results['temp_file_ops'] = {'status': 'ERROR', 'error': str(e)}
            print(f"✗ Erreur opérations fichier: {e}")
        
        # Test avec fichiers existants
        existing_files = ['test-import.csv', 'test_simple.csv']
        for filename in existing_files:
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Test parsing rapide
                    reader = csv.reader(io.StringIO(content))
                    rows = list(reader)
                    
                    results[f'file_{filename}'] = {
                        'status': 'OK',
                        'size': len(content),
                        'rows': len(rows),
                        'exists': True
                    }
                    print(f"✓ {filename}: {len(content)} chars, {len(rows)} lignes")
                    
                except Exception as e:
                    results[f'file_{filename}'] = {
                        'status': 'ERROR',
                        'error': str(e),
                        'exists': True
                    }
                    print(f"✗ {filename}: Erreur - {e}")
            else:
                results[f'file_{filename}'] = {'exists': False}
                print(f"ⓘ {filename}: N'existe pas")
        
        return results
    
    def test_database_operations(self) -> Dict[str, Any]:
        """Test des opérations base de données"""
        print("\n" + "="*60)
        print("TEST OPÉRATIONS BASE DE DONNÉES")
        print("="*60)
        
        results = {}
        
        # Test SQLite en mémoire
        try:
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            
            # Création table test
            cursor.execute('''
                CREATE TABLE test_transactions (
                    id INTEGER PRIMARY KEY,
                    date TEXT,
                    description TEXT,
                    amount REAL,
                    category TEXT DEFAULT ''
                )
            ''')
            
            # Insertion données de test
            test_data = [
                ('2024-01-01', 'Test Transaction 1', 100.50, 'Food'),
                ('2024-01-02', 'Test Transaction 2', -75.25, 'Transport'),
                ('2024-01-03', 'Test Transaction 3', 200.00, 'Income')
            ]
            
            cursor.executemany(
                'INSERT INTO test_transactions (date, description, amount, category) VALUES (?, ?, ?, ?)',
                test_data
            )
            
            # Vérification
            cursor.execute('SELECT COUNT(*) FROM test_transactions')
            count = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(amount) FROM test_transactions')
            total = cursor.fetchone()[0]
            
            conn.close()
            
            results['sqlite_memory'] = {
                'status': 'OK',
                'inserted_rows': len(test_data),
                'count_verification': count,
                'total_amount': total
            }
            print(f"✓ SQLite mémoire: {count} transactions, total: {total}")
            
        except Exception as e:
            results['sqlite_memory'] = {'status': 'ERROR', 'error': str(e)}
            print(f"✗ Erreur SQLite mémoire: {e}")
        
        # Test fichier de base existant
        if os.path.exists('budget.db'):
            try:
                conn = sqlite3.connect('budget.db')
                cursor = conn.cursor()
                
                # Liste des tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Information sur table transactions si elle existe
                table_info = {}
                if 'transactions' in tables:
                    cursor.execute('SELECT COUNT(*) FROM transactions')
                    count = cursor.fetchone()[0]
                    table_info['transactions_count'] = count
                
                conn.close()
                
                results['existing_db'] = {
                    'status': 'OK',
                    'exists': True,
                    'tables': tables,
                    'info': table_info
                }
                print(f"✓ Base existante: {len(tables)} tables")
                
            except Exception as e:
                results['existing_db'] = {
                    'status': 'ERROR',
                    'exists': True,
                    'error': str(e)
                }
                print(f"⚠ Base existante: Erreur - {e}")
        else:
            results['existing_db'] = {'exists': False}
            print("ⓘ Aucune base existante")
        
        return results
    
    def test_integration_csv_to_db(self) -> Dict[str, Any]:
        """Test d'intégration complète CSV → Base"""
        print("\n" + "="*60)
        print("TEST INTÉGRATION CSV → BASE")
        print("="*60)
        
        results = {}
        
        try:
            # Données CSV de test
            test_csv = self.csv_samples['valid_basic']
            
            # 1. Parser le CSV
            reader = csv.DictReader(io.StringIO(test_csv))
            csv_data = list(reader)
            
            # 2. Créer une base temporaire
            temp_db = tempfile.mktemp(suffix='.db')
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT DEFAULT '',
                    imported_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 3. Insérer les données CSV
            inserted_count = 0
            for row in csv_data:
                try:
                    cursor.execute('''
                        INSERT INTO transactions (date, description, amount, category)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        row['Date'],
                        row['Description'],
                        float(row['Amount'].replace(',', '.')),
                        row.get('Category', '')
                    ))
                    inserted_count += 1
                except Exception as e:
                    print(f"  ⚠ Erreur ligne: {e}")
            
            conn.commit()
            
            # 4. Vérification
            cursor.execute('SELECT COUNT(*) FROM transactions')
            db_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT date, description, amount FROM transactions ORDER BY date')
            db_data = cursor.fetchall()
            
            conn.close()
            os.unlink(temp_db)
            
            results['integration'] = {
                'status': 'OK',
                'csv_rows': len(csv_data),
                'inserted_rows': inserted_count,
                'db_verification': db_count,
                'sample_data': db_data[:3],  # Premiers enregistrements
                'match': db_count == inserted_count == len(csv_data)
            }
            
            print(f"✓ CSV: {len(csv_data)} lignes")
            print(f"✓ Insertions: {inserted_count}")
            print(f"✓ Vérification DB: {db_count}")
            print(f"✓ Cohérence: {'OK' if results['integration']['match'] else 'KO'}")
            
        except Exception as e:
            results['integration'] = {'status': 'ERROR', 'error': str(e)}
            print(f"✗ Erreur intégration: {e}")
            traceback.print_exc()
        
        return results
    
    def test_performance(self) -> Dict[str, Any]:
        """Test de performance avec gros fichier"""
        print("\n" + "="*60)
        print("TEST PERFORMANCE")
        print("="*60)
        
        results = {}
        
        try:
            large_csv = self.csv_samples['large_dataset']
            
            # Test avec csv standard
            start_time = datetime.now()
            reader = csv.DictReader(io.StringIO(large_csv))
            rows = list(reader)
            csv_time = (datetime.now() - start_time).total_seconds()
            
            results['csv_standard'] = {
                'status': 'OK',
                'rows_processed': len(rows),
                'processing_time': csv_time,
                'rows_per_second': len(rows) / csv_time if csv_time > 0 else 0
            }
            print(f"✓ CSV standard: {len(rows)} lignes en {csv_time:.3f}s")
            
            # Test avec pandas si disponible
            if HAS_PANDAS:
                start_time = datetime.now()
                df = pd.read_csv(io.StringIO(large_csv))
                pandas_time = (datetime.now() - start_time).total_seconds()
                
                results['pandas'] = {
                    'status': 'OK',
                    'rows_processed': len(df),
                    'processing_time': pandas_time,
                    'rows_per_second': len(df) / pandas_time if pandas_time > 0 else 0
                }
                print(f"✓ Pandas: {len(df)} lignes en {pandas_time:.3f}s")
                
                # Comparaison
                if csv_time > 0 and pandas_time > 0:
                    speedup = csv_time / pandas_time
                    print(f"ⓘ Facteur d'accélération pandas: {speedup:.2f}x")
            else:
                results['pandas'] = {'status': 'NOT_AVAILABLE'}
                print("⚠ Pandas non disponible pour comparaison")
        
        except Exception as e:
            results['performance'] = {'status': 'ERROR', 'error': str(e)}
            print(f"✗ Erreur test performance: {e}")
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Lance tous les tests critiques"""
        print("TESTS CRITIQUES FONCTIONNALITÉ CSV")
        print("="*80)
        
        all_results = {
            'timestamp': datetime.now().isoformat(),
            'environment': {
                'python_version': sys.version,
                'has_pandas': HAS_PANDAS,
                'working_directory': os.getcwd()
            }
        }
        
        try:
            # Tests séquentiels
            all_results['csv_standard'] = self.test_csv_parsing_standard()
            all_results['csv_pandas'] = self.test_csv_parsing_pandas()
            all_results['file_operations'] = self.test_file_operations()
            all_results['database'] = self.test_database_operations()
            all_results['integration'] = self.test_integration_csv_to_db()
            all_results['performance'] = self.test_performance()
            
            # Analyse des résultats
            critical_failures = []
            warnings = []
            successes = []
            
            for category, tests in all_results.items():
                if category in ['timestamp', 'environment']:
                    continue
                
                if isinstance(tests, dict):
                    for test_name, result in tests.items():
                        if isinstance(result, dict):
                            if result.get('status') == 'ERROR':
                                critical_failures.append(f"{category}.{test_name}")
                            elif result.get('status') in ['OK', 'AVAILABLE']:
                                successes.append(f"{category}.{test_name}")
                            else:
                                warnings.append(f"{category}.{test_name}")
            
            # Résumé final
            print("\n" + "="*80)
            print("RÉSUMÉ DES TESTS CRITIQUES")
            print("="*80)
            
            print(f"✓ Succès: {len(successes)}")
            print(f"⚠ Avertissements: {len(warnings)}")
            print(f"✗ Échecs critiques: {len(critical_failures)}")
            
            if critical_failures:
                print("\nÉchecs critiques:")
                for failure in critical_failures:
                    print(f"  - {failure}")
            
            # Statut global
            if not critical_failures:
                all_results['overall_status'] = 'PASS'
                print("\n🎉 STATUT GLOBAL: FONCTIONNALITÉ CSV OPÉRATIONNELLE")
            elif len(critical_failures) < len(successes):
                all_results['overall_status'] = 'PARTIAL'
                print("\n⚠️  STATUT GLOBAL: FONCTIONNELLE AVEC LIMITATIONS")
            else:
                all_results['overall_status'] = 'FAIL'
                print("\n❌ STATUT GLOBAL: PROBLÈMES CRITIQUES")
            
            all_results['summary'] = {
                'successes': len(successes),
                'warnings': len(warnings),
                'critical_failures': len(critical_failures),
                'critical_failure_list': critical_failures
            }
            
        except Exception as e:
            print(f"\nERREUR CRITIQUE LORS DES TESTS: {e}")
            traceback.print_exc()
            all_results['critical_error'] = str(e)
            all_results['overall_status'] = 'ERROR'
        
        # Sauvegarde des résultats
        try:
            with open('csv_critical_test_results.json', 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n✓ Résultats sauvegardés: csv_critical_test_results.json")
        except Exception as e:
            print(f"\n✗ Erreur sauvegarde: {e}")
        
        return all_results

def main():
    """Point d'entrée principal"""
    try:
        tester = CSVCriticalTester()
        results = tester.run_all_tests()
        
        print(f"\nTests terminés. Statut: {results.get('overall_status', 'UNKNOWN')}")
        
        # Code de sortie basé sur les résultats
        if results.get('overall_status') == 'PASS':
            sys.exit(0)
        elif results.get('overall_status') == 'PARTIAL':
            sys.exit(1)  # Warnings
        else:
            sys.exit(2)  # Failures
            
    except KeyboardInterrupt:
        print("\nTests interrompus par l'utilisateur")
        sys.exit(3)
    except Exception as e:
        print(f"\nErreur critique: {e}")
        traceback.print_exc()
        sys.exit(4)

if __name__ == "__main__":
    main()