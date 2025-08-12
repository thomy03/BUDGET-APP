#!/usr/bin/env python3
"""
Script de diagnostic pour l'erreur 400 sur /import
Reproduit l'erreur étape par étape pour identifier la cause
"""
import logging
import pandas as pd
import io
from typing import List, Dict
from utils.core_functions import (
    validate_file_security, robust_read_csv, detect_months_with_metadata,
    check_duplicate_transactions, validate_csv_data, normalize_cols, parse_number
)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockUploadFile:
    """Mock UploadFile pour tester"""
    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.file = io.BytesIO(content.encode('utf-8'))
        self.size = len(content)

class MockDB:
    """Mock database pour tester"""
    def query(self, model):
        return MockQuery()
    
    def add(self, obj):
        pass
    
    def commit(self):
        pass

class MockQuery:
    """Mock query pour tester"""
    def filter(self, *args):
        return self
    
    def first(self):
        return None

def create_test_csv() -> str:
    """Crée un CSV de test similaire au fichier problématique"""
    csv_content = """Date Opération;Date Valeur;Libellé;Montant;Catégorie
09/08/2025;09/08/2025;VIREMENT SALAIRE ENTREPRISE X;2500,00;Revenus
10/08/2025;10/08/2025;PRELEVEMENT EDF;-45,32;Services
11/08/2025;11/08/2025;CB CARREFOUR;-78,90;Alimentation
12/08/2025;12/08/2025;CB STATION SERVICE;-65,00;Transport
13/08/2025;13/08/2025;VIREMENT LOYER;-850,00;Logement
"""
    return csv_content

def test_step_by_step():
    """Test étape par étape du processus d'import"""
    print("=== DIAGNOSTIC ERREUR 400 IMPORT ===\n")
    
    # Créer un fichier de test
    csv_content = create_test_csv()
    mock_file = MockUploadFile("export-operations-09-08-2025_13-12-18.csv", csv_content)
    mock_db = MockDB()
    
    print("1. Test validation sécurité fichier...")
    try:
        security_valid = validate_file_security(mock_file)
        print(f"   ✅ Sécurité: {security_valid}")
    except Exception as e:
        print(f"   ❌ Erreur sécurité: {e}")
        return
    
    print("\n2. Test lecture CSV robuste...")
    try:
        df = robust_read_csv(mock_file)
        print(f"   ✅ CSV lu: {len(df)} lignes, {len(df.columns)} colonnes")
        print(f"   Colonnes détectées: {list(df.columns)}")
        print(f"   Premières lignes:")
        print(df.head().to_string())
    except Exception as e:
        print(f"   ❌ Erreur lecture CSV: {e}")
        return
    
    print("\n3. Test normalisation colonnes...")
    try:
        df_normalized = normalize_cols(df.copy())
        print(f"   ✅ Colonnes normalisées: {list(df_normalized.columns)}")
        print(f"   Premières lignes normalisées:")
        print(df_normalized.head().to_string())
    except Exception as e:
        print(f"   ❌ Erreur normalisation: {e}")
    
    print("\n4. Test détection mois...")
    try:
        months_data = detect_months_with_metadata(df)
        print(f"   ✅ Mois détectés: {len(months_data)}")
        for month in months_data:
            print(f"      - {month['month']}: {month['transaction_count']} transactions")
        
        if not months_data:
            print("   ❌ ERREUR: Aucun mois détecté - CAUSE POSSIBLE DE L'ERREUR 400!")
            
            # Diagnostic approfondi
            print("\n   DIAGNOSTIC APPROFONDI:")
            df_test = normalize_cols(df.copy())
            print(f"   - Colonnes après normalisation: {list(df_test.columns)}")
            
            if 'date_op' not in df_test.columns:
                print("   - ❌ Colonne 'date_op' manquante après normalisation!")
                print("   - Colonnes originales:", list(df.columns))
                
                # Test de conversion manuelle
                for col in df.columns:
                    if 'date' in col.lower():
                        print(f"   - Tentative conversion '{col}' vers 'date_op'")
                        try:
                            df_test_manual = df.copy()
                            df_test_manual.columns = [c.lower().strip() for c in df_test_manual.columns]
                            if col.lower() in ['date opération', 'date operation']:
                                df_test_manual = df_test_manual.rename(columns={col.lower(): 'date_op'})
                                print(f"     - Colonnes après rename: {list(df_test_manual.columns)}")
                                
                                # Test conversion date
                                df_test_manual['date_op'] = pd.to_datetime(df_test_manual['date_op'], errors='coerce')
                                valid_dates = df_test_manual['date_op'].notna().sum()
                                print(f"     - Dates valides: {valid_dates}/{len(df_test_manual)}")
                        except Exception as e:
                            print(f"     - Erreur: {e}")
            else:
                print("   - ✅ Colonne 'date_op' trouvée")
                try:
                    df_test['date_op'] = pd.to_datetime(df_test['date_op'], errors='coerce')
                    valid_dates = df_test['date_op'].notna().sum()
                    print(f"   - Dates valides: {valid_dates}/{len(df_test)}")
                    
                    if valid_dates == 0:
                        print("   - ❌ Aucune date valide - formats de date incompatibles!")
                        print("   - Échantillon de dates:", df_test['date_op'].head().tolist())
                except Exception as e:
                    print(f"   - Erreur conversion dates: {e}")
            
            return
            
    except Exception as e:
        print(f"   ❌ Erreur détection mois: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n5. Test vérification doublons...")
    try:
        duplicate_info = check_duplicate_transactions(df, mock_db)
        print(f"   ✅ Doublons vérifiés: {duplicate_info}")
    except Exception as e:
        print(f"   ❌ Erreur vérification doublons: {e}")
    
    print("\n6. Test validation données...")
    try:
        validation_errors = validate_csv_data(df)
        print(f"   Erreurs de validation: {len(validation_errors)}")
        if validation_errors:
            print("   ❌ ERREURS TROUVÉES - CAUSE POSSIBLE DE L'ERREUR 400!")
            for error in validation_errors:
                print(f"      - {error}")
        else:
            print("   ✅ Aucune erreur de validation")
    except Exception as e:
        print(f"   ❌ Erreur validation: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== FIN DIAGNOSTIC ===")

def test_column_mapping():
    """Test spécifique du mapping des colonnes"""
    print("\n=== TEST MAPPING COLONNES ===")
    
    # Tester différents formats de colonnes
    test_columns = [
        ["Date Opération", "Date Valeur", "Libellé", "Montant", "Catégorie"],
        ["date opération", "date valeur", "libellé", "montant", "catégorie"],
        ["Date", "Description", "Montant", "Compte"],
        ["date", "description", "amount", "balance"]
    ]
    
    for i, columns in enumerate(test_columns):
        print(f"\nTest {i+1}: {columns}")
        
        # Créer un DataFrame de test avec le bon nombre de colonnes
        if len(columns) == 5:
            data = [["01/01/2025", "01/01/2025", "Test", "100,50", "Compte"]]
        else:
            data = [["01/01/2025", "Test", "100,50", "Compte"]]
        df = pd.DataFrame(data, columns=columns)
        
        print(f"   Avant normalisation: {list(df.columns)}")
        
        try:
            df_normalized = normalize_cols(df)
            print(f"   Après normalisation: {list(df_normalized.columns)}")
            
            # Vérifier si date_op existe
            if 'date_op' in df_normalized.columns:
                print("   ✅ date_op trouvée")
            else:
                print("   ❌ date_op manquante")
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")

if __name__ == "__main__":
    test_step_by_step()
    test_column_mapping()