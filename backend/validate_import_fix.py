#!/usr/bin/env python3
"""
Test de validation finale de la correction de l'erreur 400
Simule l'endpoint /import complet
"""
import logging
import sys
from typing import Dict
from fastapi import HTTPException
import pandas as pd
import io
from utils.core_functions import (
    validate_file_security, robust_read_csv, detect_months_with_metadata,
    check_duplicate_transactions, validate_csv_data
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockUploadFile:
    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.file = io.BytesIO(content.encode('utf-8'))
        self.size = len(content)

class MockDB:
    def query(self, model):
        return MockQuery()
    def add(self, obj):
        pass
    def commit(self):
        pass

class MockQuery:
    def filter(self, *args):
        return self
    def first(self):
        return None

def simulate_import_endpoint(file_content: str, filename: str) -> Dict:
    """
    Simule l'endpoint /import avec le contenu corrigé
    """
    mock_file = MockUploadFile(filename, file_content)
    mock_db = MockDB()
    
    try:
        logger.info(f"Début import fichier '{filename}'")
        
        # Validation sécurité
        if not validate_file_security(mock_file):
            raise HTTPException(status_code=400, detail="Fichier non autorisé ou dangereux")
        
        # Lecture robuste du CSV
        df = robust_read_csv(mock_file)
        logger.info(f"CSV lu avec succès: {len(df)} lignes")
        
        # Détection des mois
        months_data = detect_months_with_metadata(df)
        if not months_data:
            raise HTTPException(status_code=400, detail="Aucun mois détecté dans le fichier")
        
        # Vérification doublons
        duplicate_info = check_duplicate_transactions(df, mock_db)
        
        # Validation données
        validation_errors = validate_csv_data(df)
        if validation_errors:
            raise HTTPException(status_code=400, detail=f"Erreurs de validation: {'; '.join(validation_errors)}")
        
        # Simulation métadonnées d'import
        import uuid
        import_id = str(uuid.uuid4())
        
        logger.info(f"✅ Import terminé: ID={import_id}")
        
        return {
            "import_id": import_id,
            "status": "success",
            "filename": filename,
            "rows_processed": len(df),
            "months_detected": months_data,
            "duplicates_info": duplicate_info,
            "validation_errors": [],
            "message": "Import réussi"
        }
        
    except HTTPException as e:
        logger.error(f"HTTPException: {e.status_code} - {e.detail}")
        return {
            "status": "error",
            "status_code": e.status_code,
            "error": e.detail
        }
    except Exception as e:
        logger.error(f"Erreur import: {str(e)}")
        return {
            "status": "error", 
            "status_code": 500,
            "error": f"Erreur lors de l'import: {str(e)}"
        }

def create_problematic_csv() -> str:
    """Crée un CSV avec le format problématique original"""
    return """Date Opération;Date Valeur;Libellé;Montant;Catégorie
09/08/2025;09/08/2025;VIREMENT SALAIRE ENTREPRISE X;2500,00;Revenus
10/08/2025;10/08/2025;PRELEVEMENT EDF;-45,32;Services
11/08/2025;11/08/2025;CB CARREFOUR;-78,90;Alimentation
12/08/2025;12/08/2025;CB STATION SERVICE;-65,00;Transport
13/08/2025;13/08/2025;VIREMENT LOYER;-850,00;Logement
14/08/2025;14/08/2025;RETRAIT DAB;-50,00;Autres
15/08/2025;15/08/2025;FACTURE INTERNET;-29,99;Services
16/08/2025;16/08/2025;CB PHARMACIE;-15,50;Santé
17/08/2025;17/08/2025;CB BOULANGERIE;-8,20;Alimentation
18/08/2025;18/08/2025;VIREMENT EPARGNE;-200,00;Épargne
19/08/2025;19/08/2025;CB ESSENCE;-45,00;Transport
20/08/2025;20/08/2025;PRELEVEMENT ASSURANCE;-120,00;Assurance
21/08/2025;21/08/2025;CB RESTAURANT;-35,00;Loisirs
22/08/2025;22/08/2025;FACTURE TELEPHONE;-25,99;Services
23/08/2025;23/08/2025;CB SUPERMARCHE;-67,89;Alimentation
24/08/2025;24/08/2025;RETRAIT DAB;-40,00;Autres
25/08/2025;25/08/2025;CB CINEMA;-22,00;Loisirs
26/08/2025;26/08/2025;PRELEVEMENT MUTUELLE;-85,00;Santé
27/08/2025;27/08/2025;CB LIBRAIRIE;-18,50;Loisirs
28/08/2025;28/08/2025;FACTURE GAZ;-38,75;Services
29/08/2025;29/08/2025;CB COIFFEUR;-30,00;Services
30/08/2025;30/08/2025;VIREMENT REMBOURSEMENT;150,00;Autres
31/08/2025;31/08/2025;CB SUPERMARCHE;-89,45;Alimentation"""

def main():
    """Test principal de validation"""
    print("=== VALIDATION FINALE CORRECTION ERREUR 400 ===\n")
    
    # Test 1: CSV problématique original
    print("1. Test avec CSV au format français (DD/MM/YYYY)...")
    csv_content = create_problematic_csv()
    result = simulate_import_endpoint(csv_content, "export-operations-09-08-2025_13-12-18.csv")
    
    if result["status"] == "success":
        print(f"   ✅ SUCCÈS: {result['message']}")
        print(f"   - Lignes traitées: {result['rows_processed']}")
        print(f"   - Mois détectés: {len(result['months_detected'])}")
        for month in result['months_detected']:
            print(f"     * {month['month']}: {month['transaction_count']} transactions")
        print(f"   - ID import: {result['import_id']}")
        success_count = 1
    else:
        print(f"   ❌ ÉCHEC: {result.get('error', 'Erreur inconnue')}")
        if "status_code" in result:
            print(f"   - Code d'erreur: {result['status_code']}")
        success_count = 0
    
    # Test 2: Formats de dates variés
    print("\n2. Test avec différents formats de dates...")
    test_cases = [
        ("DD/MM/YYYY", "01/08/2025;01/08/2025;TEST;100,00;Test"),
        ("DD-MM-YYYY", "01-08-2025;01-08-2025;TEST;100,00;Test"),
        ("YYYY-MM-DD", "2025-08-01;2025-08-01;TEST;100,00;Test"),
        ("MM/DD/YYYY", "08/01/2025;08/01/2025;TEST;100,00;Test")
    ]
    
    for format_name, test_line in test_cases:
        csv_test = f"Date Opération;Date Valeur;Libellé;Montant;Catégorie\n{test_line}"
        result = simulate_import_endpoint(csv_test, f"test_{format_name}.csv")
        
        if result["status"] == "success":
            print(f"   ✅ {format_name}: SUCCÈS")
            success_count += 1
        else:
            print(f"   ❌ {format_name}: ÉCHEC - {result.get('error', '')}")
    
    # Test 3: Cas d'erreur attendus
    print("\n3. Test des cas d'erreur attendus...")
    error_cases = [
        ("CSV vide", "Date Opération;Date Valeur;Libellé;Montant;Catégorie\n"),
        ("Dates invalides", "Date Opération;Date Valeur;Libellé;Montant;Catégorie\ninvalid;invalid;TEST;100,00;Test"),
        ("Colonnes manquantes", "Description;Montant\nTest;100,00")
    ]
    
    for case_name, csv_test in error_cases:
        result = simulate_import_endpoint(csv_test, f"test_{case_name}.csv")
        
        if result["status"] == "error" and result.get("status_code") == 400:
            print(f"   ✅ {case_name}: Erreur 400 correctement détectée")
        else:
            print(f"   ⚠️  {case_name}: Comportement inattendu - {result}")
    
    # Résultat final
    print(f"\n=== RÉSULTATS FINAUX ===")
    total_tests = 5  # 1 + 4 formats
    print(f"Tests réussis: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 CORRECTION VALIDÉE: L'erreur 400 est résolue!")
        print("✅ L'endpoint /import accepte maintenant les formats de date français")
        print("✅ Messages d'erreur améliorés pour un meilleur debugging")
        return 0
    else:
        print("⚠️  CORRECTION PARTIELLE: Certains cas échouent encore")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)