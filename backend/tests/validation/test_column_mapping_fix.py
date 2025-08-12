#!/usr/bin/env python3
"""
Test du mapping des colonnes CSV après correction
Vérifie que le mapping fonctionne pour les colonnes: dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance
"""
import pandas as pd
import sys
import os

# Ajout du path pour importer les modules locaux
sys.path.append(os.path.dirname(__file__))

from utils.core_functions import normalize_cols

def test_column_mapping():
    """Test le mapping des colonnes du CSV problématique"""
    print("🧪 Test du mapping des colonnes CSV")
    print("=" * 60)
    
    # Colonnes du CSV problématique
    csv_columns = [
        "dateOp", "dateVal", "label", "category", "categoryParent", 
        "supplierFound", "amount", "comment", "accountNum", "accountLabel", "accountbalance"
    ]
    
    print(f"📋 Colonnes originales du CSV: {csv_columns}")
    
    # Création d'un DataFrame de test
    test_data = {col: [f"test_{col}"] for col in csv_columns}
    df = pd.DataFrame(test_data)
    
    print(f"✅ DataFrame créé avec {len(df.columns)} colonnes")
    print(f"📊 Colonnes avant normalisation: {list(df.columns)}")
    
    # Application du mapping
    df_normalized = normalize_cols(df)
    
    print(f"🔧 Colonnes après normalisation: {list(df_normalized.columns)}")
    
    # Vérification des colonnes essentielles après mapping
    expected_mappings = {
        'dateop': 'date_op',        # dateOp -> date_op
        'label': 'label',           # label -> label (pas de changement)
        'amount': 'amount',         # amount -> amount (pas de changement)
        'accountlabel': 'account',  # accountLabel -> account
        'category': 'category'      # category -> category (pas de changement)
    }
    
    print("\n🔍 Vérification des mappings critiques:")
    for original_lower, expected in expected_mappings.items():
        if expected in df_normalized.columns:
            print(f"✅ {original_lower} -> {expected}: OK")
        else:
            print(f"❌ {original_lower} -> {expected}: MANQUÉ")
            print(f"   Colonnes disponibles: {list(df_normalized.columns)}")
    
    # Vérification des colonnes minimales requises
    minimum_required = ['date_op']
    missing_required = [col for col in minimum_required if col not in df_normalized.columns]
    
    if missing_required:
        print(f"\n❌ ERREUR: Colonnes requises manquantes: {missing_required}")
        return False
    else:
        print(f"\n✅ Toutes les colonnes requises sont présentes")
    
    # Vérification des colonnes importantes pour l'import
    important_columns = ['date_op', 'label', 'amount', 'account']
    available_important = [col for col in important_columns if col in df_normalized.columns]
    missing_important = [col for col in important_columns if col not in df_normalized.columns]
    
    print(f"\n📈 Colonnes importantes trouvées: {available_important}")
    if missing_important:
        print(f"⚠️ Colonnes importantes manquantes: {missing_important}")
    
    return len(missing_required) == 0

def test_specific_problem_case():
    """Test le cas spécifique mentionné dans la tâche"""
    print("\n" + "=" * 60)
    print("🎯 Test du cas spécifique: dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance")
    
    # Simulation d'un CSV avec ce format exact
    csv_content = "dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance\n2024-01-01;2024-01-02;Test transaction;Food;Groceries;SuperMarket;-50.00;Test comment;123456789;Compte Courant;1500.00"
    
    import io
    csv_buffer = io.StringIO(csv_content)
    df = pd.read_csv(csv_buffer, sep=';')
    
    print(f"📋 DataFrame chargé: {len(df)} lignes, {len(df.columns)} colonnes")
    print(f"📊 Colonnes: {list(df.columns)}")
    
    # Test du mapping
    df_normalized = normalize_cols(df)
    print(f"🔧 Après mapping: {list(df_normalized.columns)}")
    
    # Vérification que les colonnes clés sont présentes
    key_mappings = {
        'label': 'label',           # doit rester label
        'amount': 'amount',         # doit rester amount  
        'accountlabel': 'account'   # doit devenir account
    }
    
    success = True
    for original, expected in key_mappings.items():
        original_lower = original.lower()
        if expected in df_normalized.columns:
            print(f"✅ {original} -> {expected}: Trouvé")
        else:
            print(f"❌ {original} -> {expected}: MANQUÉ")
            success = False
    
    return success

if __name__ == "__main__":
    print("🧪 Test du mapping des colonnes CSV - Fix Validation")
    print("=" * 80)
    
    # Test 1: Mapping général
    result1 = test_column_mapping()
    
    # Test 2: Cas spécifique
    result2 = test_specific_problem_case()
    
    print("\n" + "=" * 80)
    if result1 and result2:
        print("✅ TOUS LES TESTS RÉUSSIS - Le mapping fonctionne correctement")
    else:
        print("❌ ÉCHEC - Le mapping nécessite des corrections")
        
    print("=" * 80)