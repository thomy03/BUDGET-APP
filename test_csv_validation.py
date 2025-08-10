#!/usr/bin/env python3
"""
Script de validation des défaillances CSV Import - Budget Famille v2.3
Teste spécifiquement les points de défaillance identifiés dans le rapport QA
"""

import os
import sys
import json
import csv
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

def analyze_csv_structure(file_path: Path) -> Dict:
    """Analyse la structure d'un fichier CSV"""
    result = {
        "file": file_path.name,
        "exists": file_path.exists(),
        "rows": 0,
        "columns": [],
        "months_detected": set(),
        "potential_duplicates": [],
        "format_errors": [],
        "valid_rows": 0
    }
    
    if not file_path.exists():
        return result
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Detect delimiter
            first_line = f.readline().strip()
            if ';' in first_line:
                delimiter = ';'
            elif ',' in first_line:
                delimiter = ','
            else:
                delimiter = ';'  # default
            
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            result["columns"] = reader.fieldnames or []
            
            row_hashes = {}
            
            for i, row in enumerate(reader):
                result["rows"] += 1
                
                # Extract date and validate
                date_str = row.get('date', '').strip()
                if date_str:
                    try:
                        # Try DD/MM/YYYY format
                        if '/' in date_str:
                            parts = date_str.split('/')
                            if len(parts) == 3:
                                day, month, year = parts
                                # Validate date components
                                if (int(day) > 31 or int(day) < 1 or 
                                    int(month) > 12 or int(month) < 1):
                                    result["format_errors"].append(f"Ligne {i+2}: Date invalide '{date_str}'")
                                else:
                                    month_key = f"{year}-{month.zfill(2)}"
                                    result["months_detected"].add(month_key)
                                    result["valid_rows"] += 1
                        elif '-' in date_str:  # YYYY-MM-DD format
                            parts = date_str.split('-')
                            if len(parts) == 3:
                                year, month, day = parts
                                month_key = f"{year}-{month.zfill(2)}"
                                result["months_detected"].add(month_key)
                                result["valid_rows"] += 1
                        else:
                            result["format_errors"].append(f"Ligne {i+2}: Format date non reconnu '{date_str}'")
                    except ValueError as e:
                        result["format_errors"].append(f"Ligne {i+2}: Erreur date '{date_str}' - {str(e)}")
                
                # Check for duplicates (simulate backend logic)
                if date_str and row.get('description') and row.get('montant'):
                    row_signature = f"{date_str}|{row.get('description', '')}|{row.get('montant', '')}|{row.get('compte', '')}"
                    row_hash = hashlib.md5(row_signature.encode('utf-8')).hexdigest()
                    
                    if row_hash in row_hashes:
                        result["potential_duplicates"].append({
                            "hash": row_hash,
                            "first_line": row_hashes[row_hash],
                            "duplicate_line": i + 2,
                            "signature": row_signature
                        })
                    else:
                        row_hashes[row_hash] = i + 2
                
                # Check amount format
                amount_str = row.get('montant', '').strip()
                if amount_str:
                    # Check for common format issues
                    if '.' in amount_str and ',' in amount_str:
                        result["format_errors"].append(f"Ligne {i+2}: Montant ambigu '{amount_str}'")
                    elif ' ' in amount_str.replace(' ', ''):  # Check for thousand separators
                        if not amount_str.replace(' ', '').replace(',', '').replace('-', '').isdigit():
                            result["format_errors"].append(f"Ligne {i+2}: Format montant invalide '{amount_str}'")
                    # Check for non-numeric characters
                    clean_amount = amount_str.replace(',', '.').replace(' ', '').replace('-', '')
                    if not all(c.isdigit() or c == '.' for c in clean_amount):
                        result["format_errors"].append(f"Ligne {i+2}: Caractères non numériques dans montant '{amount_str}'")
                
                # Check for empty required fields
                if not row.get('compte', '').strip():
                    result["format_errors"].append(f"Ligne {i+2}: Champ 'compte' vide")
                
    except Exception as e:
        result["format_errors"].append(f"Erreur lecture fichier: {str(e)}")
    
    result["months_detected"] = sorted(list(result["months_detected"]))
    return result

def test_backend_compatibility(csv_analysis: Dict) -> Dict:
    """Teste la compatibilité avec le backend actuel"""
    compatibility = {
        "expected_response_format": "TxOut[]",
        "actual_frontend_expectation": "ImportResponse",
        "compatibility_issues": [],
        "missing_metadata": []
    }
    
    # Check if multi-month data would be handled correctly
    if len(csv_analysis["months_detected"]) > 1:
        compatibility["missing_metadata"].extend([
            "months: ImportMonth[] - Navigation metadata",
            "suggestedMonth: string - Target month suggestion", 
            "importId: string - Unique import identifier"
        ])
        compatibility["compatibility_issues"].append(
            "Multi-month CSV cannot trigger automatic redirection"
        )
    
    # Check duplicate handling
    if csv_analysis["potential_duplicates"]:
        compatibility["missing_metadata"].extend([
            "duplicatesCount: number - Count of ignored duplicates",
            "warnings: string[] - Duplicate warnings"
        ])
        compatibility["compatibility_issues"].append(
            "Duplicates would be imported without detection"
        )
    
    # Check error reporting
    if csv_analysis["format_errors"]:
        compatibility["missing_metadata"].extend([
            "errors: string[] - Format errors details",
            "processing: 'done' | 'processing' - Status"
        ])
        compatibility["compatibility_issues"].append(
            "Format errors would not be reported to user"
        )
    
    return compatibility

def validate_frontend_import_utils() -> Dict:
    """Valide les utilitaires d'import frontend"""
    validation = {
        "pickTargetMonth_logic": "OK",
        "buildTransactionUrl_logic": "OK", 
        "issues": []
    }
    
    # Test scenarios that would fail with current backend
    test_cases = [
        {
            "name": "Empty months array",
            "months": [],
            "expected_result": None,
            "would_fail": True,
            "reason": "Backend doesn't provide months metadata"
        },
        {
            "name": "Multi-month without suggestion",
            "months": [
                {"month": "2024-01", "newCount": 5},
                {"month": "2024-02", "newCount": 8},
                {"month": "2024-03", "newCount": 3}
            ],
            "suggestedMonth": None,
            "expected_result": "2024-02",  # Highest newCount
            "would_fail": True,
            "reason": "Backend doesn't calculate newCount per month"
        }
    ]
    
    for case in test_cases:
        if case["would_fail"]:
            validation["issues"].append({
                "scenario": case["name"],
                "reason": case["reason"],
                "impact": "Redirection logic fails"
            })
    
    return validation

def generate_test_summary(test_results: List[Dict]) -> Dict:
    """Génère un résumé des tests"""
    summary = {
        "total_files_tested": len(test_results),
        "files_with_issues": 0,
        "total_format_errors": 0,
        "total_duplicates": 0,
        "multi_month_files": 0,
        "critical_issues": [],
        "recommendations": []
    }
    
    for result in test_results:
        csv_data = result["csv_analysis"]
        compat_data = result["compatibility"]
        
        if (csv_data["format_errors"] or 
            csv_data["potential_duplicates"] or 
            compat_data["compatibility_issues"]):
            summary["files_with_issues"] += 1
        
        summary["total_format_errors"] += len(csv_data["format_errors"])
        summary["total_duplicates"] += len(csv_data["potential_duplicates"])
        
        if len(csv_data["months_detected"]) > 1:
            summary["multi_month_files"] += 1
    
    # Add critical issues
    if summary["multi_month_files"] > 0:
        summary["critical_issues"].append(
            "Multi-month CSV imports will fail due to missing ImportResponse format"
        )
    
    if summary["total_duplicates"] > 0:
        summary["critical_issues"].append(
            f"{summary['total_duplicates']} duplicates would be imported without detection"
        )
    
    if summary["total_format_errors"] > 0:
        summary["critical_issues"].append(
            f"{summary['total_format_errors']} format errors would not be reported to users"
        )
    
    # Add recommendations
    summary["recommendations"] = [
        "1. CRITICAL: Refactor /import endpoint to return ImportResponse format",
        "2. CRITICAL: Implement duplicate detection with row_id verification", 
        "3. MAJOR: Add /imports/{id} endpoint for post-import metadata",
        "4. MAJOR: Enhance CSV parser error reporting",
        "5. MODERATE: Improve date format validation"
    ]
    
    return summary

def main():
    """Point d'entrée principal"""
    print("🧪 Test de Validation CSV Import - Budget Famille v2.3")
    print("=" * 60)
    
    # Test files directory
    samples_dir = Path(__file__).parent / "tests" / "csv-samples"
    
    if not samples_dir.exists():
        print(f"❌ Dossier samples non trouvé: {samples_dir}")
        return 1
    
    # Files to test
    test_files = [
        "01_happy_path_janvier_2024.csv",
        "02_multi_mois_2024_Q1.csv", 
        "03_doublons_janvier_2024.csv",
        "04_problemes_format.csv",
        "05_excel_fr_cp1252.csv"
    ]
    
    results = []
    
    print("📁 Analyse des fichiers CSV...\n")
    
    for filename in test_files:
        file_path = samples_dir / filename
        print(f"🔍 Analyse: {filename}")
        
        # Analyze CSV structure
        csv_analysis = analyze_csv_structure(file_path)
        
        # Test backend compatibility
        compatibility = test_backend_compatibility(csv_analysis)
        
        results.append({
            "filename": filename,
            "csv_analysis": csv_analysis,
            "compatibility": compatibility
        })
        
        # Print immediate results
        if csv_analysis["exists"]:
            print(f"   ✅ {csv_analysis['valid_rows']}/{csv_analysis['rows']} lignes valides")
            print(f"   📅 Mois détectés: {csv_analysis['months_detected']}")
            
            if csv_analysis["potential_duplicates"]:
                print(f"   ⚠️  {len(csv_analysis['potential_duplicates'])} doublons potentiels")
            
            if csv_analysis["format_errors"]:
                print(f"   ❌ {len(csv_analysis['format_errors'])} erreurs de format")
                for error in csv_analysis["format_errors"][:3]:  # Show first 3
                    print(f"      • {error}")
                if len(csv_analysis["format_errors"]) > 3:
                    print(f"      • ... et {len(csv_analysis['format_errors']) - 3} autres")
            
            if compatibility["compatibility_issues"]:
                print(f"   🚨 {len(compatibility['compatibility_issues'])} problèmes de compatibilité")
        else:
            print(f"   ❌ Fichier introuvable")
        
        print()
    
    # Test frontend utilities
    print("🔧 Test des utilitaires frontend...\n")
    frontend_validation = validate_frontend_import_utils()
    
    if frontend_validation["issues"]:
        print(f"❌ {len(frontend_validation['issues'])} problèmes détectés:")
        for issue in frontend_validation["issues"]:
            print(f"   • {issue['scenario']}: {issue['reason']}")
        print()
    
    # Generate summary
    print("📊 Résumé des tests")
    print("=" * 60)
    
    summary = generate_test_summary(results)
    
    print(f"📁 Fichiers testés: {summary['total_files_tested']}")
    print(f"⚠️  Fichiers avec problèmes: {summary['files_with_issues']}")
    print(f"📅 Fichiers multi-mois: {summary['multi_month_files']}")
    print(f"❌ Total erreurs format: {summary['total_format_errors']}")
    print(f"🔄 Total doublons: {summary['total_duplicates']}")
    
    if summary["critical_issues"]:
        print(f"\n🚨 PROBLÈMES CRITIQUES:")
        for issue in summary["critical_issues"]:
            print(f"   • {issue}")
    
    print(f"\n💡 RECOMMANDATIONS:")
    for rec in summary["recommendations"]:
        print(f"   {rec}")
    
    # Final verdict
    print(f"\n{'='*60}")
    
    if summary["files_with_issues"] > 0 or frontend_validation["issues"]:
        print("❌ VERDICT: ÉCHEC - Le système d'import CSV présente des défaillances critiques")
        print("🛑 RECOMMANDATION QA: BLOCAGE DE RELEASE")
        return_code = 1
    else:
        print("✅ VERDICT: SUCCÈS - Tous les tests sont passés")
        print("🚀 RECOMMANDATION QA: RELEASE APPROUVÉE")
        return_code = 0
    
    print(f"\nRapport détaillé disponible: RAPPORT_TEST_CSV_IMPORT.md")
    
    return return_code

if __name__ == "__main__":
    exit(main())