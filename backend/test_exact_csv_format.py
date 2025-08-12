#!/usr/bin/env python3
"""
Test du format exact mentionné dans la tâche
CSV avec colonnes: dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance
"""
import logging
import pandas as pd
import io
from utils.core_functions import (
    validate_file_security, robust_read_csv, detect_months_with_metadata,
    check_duplicate_transactions, validate_csv_data, normalize_cols
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
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

class MockQuery:
    """Mock query pour tester"""
    def filter(self, *args):
        return self
    def first(self):
        return None

def test_exact_format():
    """Test avec le format exact mentionné dans la tâche"""
    print("=== TEST FORMAT EXACT CSV ===")
    print("Format: dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance")
    
    # Créer le CSV exact
    csv_content = """dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance
2024-01-15;2024-01-15;VIREMENT SALAIRE ENTREPRISE;Revenus;Salaires;Entreprise X;2500.00;Salaire mensuel;123456789;Compte Courant;1500.00
2024-01-16;2024-01-16;PRELEVEMENT EDF;Services;Energie;EDF;-45.32;Facture électricité;123456789;Compte Courant;1454.68
2024-01-17;2024-01-17;CB CARREFOUR;Alimentation;Courses;Carrefour;-78.90;Courses alimentaires;123456789;Compte Courant;1375.78"""
    
    print(f"\nContenu CSV créé:")
    print(csv_content)
    
    mock_file = MockUploadFile("test-exact-format.csv", csv_content)
    mock_db = MockDB()
    
    print("\n1. Test sécurité fichier...")
    try:
        security_valid = validate_file_security(mock_file)
        print(f"   ✅ Sécurité: {security_valid}")
    except Exception as e:
        print(f"   ❌ Erreur sécurité: {e}")
        return False
    
    print("\n2. Test lecture CSV...")
    try:
        df = robust_read_csv(mock_file)
        print(f"   ✅ CSV lu: {len(df)} lignes, {len(df.columns)} colonnes")
        print(f"   Colonnes originales: {list(df.columns)}")
    except Exception as e:
        print(f"   ❌ Erreur lecture CSV: {e}")
        return False
    
    print("\n3. Test normalisation colonnes...")
    try:
        df_normalized = normalize_cols(df.copy())
        print(f"   ✅ Colonnes normalisées: {list(df_normalized.columns)}")
        
        # Vérification des mappings critiques
        expected_columns = ['date_op', 'label', 'amount', 'account']
        found_columns = [col for col in expected_columns if col in df_normalized.columns]
        missing_columns = [col for col in expected_columns if col not in df_normalized.columns]
        
        print(f"   Colonnes critiques trouvées: {found_columns}")
        if missing_columns:
            print(f"   ❌ Colonnes critiques manquantes: {missing_columns}")
            return False
        else:
            print(f"   ✅ Toutes les colonnes critiques présentes")
        
    except Exception as e:
        print(f"   ❌ Erreur normalisation: {e}")
        return False
    
    print("\n4. Test détection mois...")
    try:
        months_data = detect_months_with_metadata(df)
        print(f"   ✅ Mois détectés: {len(months_data)}")
        if months_data:
            for month in months_data:
                print(f"      - {month['month']}: {month['transaction_count']} transactions")
        else:
            print(f"   ❌ Aucun mois détecté - PROBLÈME!")
            return False
    except Exception as e:
        print(f"   ❌ Erreur détection mois: {e}")
        return False
    
    print("\n5. Test validation données...")
    try:
        validation_errors = validate_csv_data(df)
        if validation_errors:
            print(f"   ❌ Erreurs de validation: {validation_errors}")
            return False
        else:
            print(f"   ✅ Aucune erreur de validation")
    except Exception as e:
        print(f"   ❌ Erreur validation: {e}")
        return False
    
    print("\n6. Test vérification doublons...")
    try:
        duplicate_info = check_duplicate_transactions(df, mock_db)
        print(f"   ✅ Doublons vérifiés: {duplicate_info}")
    except Exception as e:
        print(f"   ❌ Erreur vérification doublons: {e}")
        return False
    
    print("\n✅ TOUS LES TESTS RÉUSSIS - Le format CSV est compatible!")
    return True

def test_problematic_cases():
    """Test des cas potentiellement problématiques"""
    print("\n=== TEST CAS PROBLÉMATIQUES ===")
    
    problematic_cases = [
        {
            "name": "Colonnes minuscules", 
            "headers": "dateop;dateval;label;category;categoryparent;supplierfound;amount;comment;accountnum;accountlabel;accountbalance"
        },
        {
            "name": "Colonnes mixtes",
            "headers": "DateOp;DateVal;Label;Category;CategoryParent;SupplierFound;Amount;Comment;AccountNum;AccountLabel;AccountBalance"  
        },
        {
            "name": "Colonnes avec espaces",
            "headers": "date op;date val;label;category;category parent;supplier found;amount;comment;account num;account label;account balance"
        }
    ]
    
    for case in problematic_cases:
        print(f"\nTesting: {case['name']}")
        
        # Créer le CSV pour ce cas
        csv_content = f"""{case['headers']}
2024-01-15;2024-01-15;Test transaction;Food;Groceries;SuperMarket;-50.00;Test comment;123456789;Compte Courant;1500.00"""
        
        print(f"   Headers: {case['headers']}")
        
        try:
            csv_buffer = io.StringIO(csv_content)
            df = pd.read_csv(csv_buffer, sep=';')
            
            print(f"   Colonnes lues: {list(df.columns)}")
            
            df_normalized = normalize_cols(df)
            print(f"   Colonnes après mapping: {list(df_normalized.columns)}")
            
            # Vérifier colonnes essentielles
            essential = ['date_op', 'label', 'amount']
            found = [col for col in essential if col in df_normalized.columns]
            missing = [col for col in essential if col not in df_normalized.columns]
            
            if missing:
                print(f"   ❌ Manque: {missing}")
            else:
                print(f"   ✅ Toutes les colonnes essentielles trouvées")
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")

if __name__ == "__main__":
    success = test_exact_format()
    test_problematic_cases()
    
    if success:
        print("\n🎉 CONCLUSION: Le mapping des colonnes fonctionne correctement!")
        print("Si l'erreur persiste, elle vient probablement d'ailleurs dans le système.")
    else:
        print("\n❌ CONCLUSION: Des problèmes ont été détectés dans le mapping.")