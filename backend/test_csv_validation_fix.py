#!/usr/bin/env python3
"""
Test de validation pour les corrections du système d'import CSV
"""
import os
import sys
import tempfile
from unittest.mock import MagicMock
from io import BytesIO

# Add the current directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import des fonctions à tester
from app import validate_file_security, sanitize_filename

def test_csv_validation():
    """Test de validation CSV avec les corrections"""
    print("=" * 60)
    print("TEST DE VALIDATION CSV - CORRECTIONS")
    print("=" * 60)
    
    # Test avec le fichier CSV créé
    test_file = "01_happy_path_janvier_2024.csv"
    
    if not os.path.exists(test_file):
        print(f"❌ Fichier de test {test_file} non trouvé")
        return False
    
    try:
        # Lire le contenu du fichier
        with open(test_file, 'rb') as f:
            content = f.read()
        
        # Créer un mock UploadFile
        class MockUploadFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.file = BytesIO(content)
                self.size = len(content)
        
        mock_file = MockUploadFile(test_file, content)
        
        print(f"📁 Test avec fichier: {test_file}")
        print(f"📏 Taille: {len(content)} bytes")
        
        # Tester la sanitisation du nom
        safe_filename = sanitize_filename(test_file)
        print(f"🔒 Nom sécurisé: {safe_filename}")
        
        # Tester la validation de sécurité
        is_valid = validate_file_security(mock_file)
        
        if is_valid:
            print("✅ Validation réussie!")
            
            # Test avec contenu CSV
            mock_file.file.seek(0)
            first_line = mock_file.file.read(100).decode('utf-8', errors='ignore')
            print(f"🔍 Première ligne: {repr(first_line[:50])}")
            
            return True
        else:
            print("❌ Validation échouée")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_various_csv_formats():
    """Test avec différents formats CSV"""
    print("\n" + "=" * 60)
    print("TEST FORMATS CSV VARIÉS")
    print("=" * 60)
    
    test_csvs = {
        "comma_separated.csv": b"Date,Description,Amount\n2024-01-01,Test,100.00\n",
        "semicolon_separated.csv": b"Date;Description;Amount\n2024-01-01;Test;100.00\n",
        "with_bom.csv": b"\xef\xbb\xbfDate,Description,Amount\n2024-01-01,Test,100.00\n",
        "simple_headers.csv": b"dateOp,label,montant\n2024-01-01,Test,100.00\n",
        "french_headers.csv": b"Date,Libelle,Montant,Compte\n01/01/2024,Test,100.00,Courant\n"
    }
    
    results = {}
    
    for filename, content in test_csvs.items():
        print(f"\n📄 Test: {filename}")
        
        try:
            class MockUploadFile:
                def __init__(self, filename, content):
                    self.filename = filename
                    self.file = BytesIO(content)
                    self.size = len(content)
            
            mock_file = MockUploadFile(filename, content)
            is_valid = validate_file_security(mock_file)
            
            results[filename] = is_valid
            status = "✅" if is_valid else "❌"
            print(f"{status} {filename}: {'VALIDE' if is_valid else 'INVALIDE'}")
            
        except Exception as e:
            results[filename] = False
            print(f"❌ {filename}: Erreur - {e}")
    
    return results

def test_magic_fallback():
    """Test du module magic_fallback"""
    print("\n" + "=" * 60)
    print("TEST MAGIC FALLBACK")
    print("=" * 60)
    
    try:
        import magic_fallback as magic
        
        test_data = [
            (b"Date,Description,Amount\n2024-01-01,Test,100.00", "text/csv"),
            (b"dateOp;libelle;montant\n2024-01-01;Test;100.00", "text/csv"),
            (b"\xef\xbb\xbfDate,Description,Amount\n", "text/csv"),
            (b"PK\x03\x04", "application/zip"),
            (b"Hello World", "text/plain"),
        ]
        
        for data, expected_type in test_data:
            detected = magic.from_buffer(data, mime=True)
            is_correct = expected_type in detected or detected == expected_type
            status = "✅" if is_correct else "❌"
            
            print(f"{status} {repr(data[:30])}")
            print(f"    Attendu: {expected_type}, Détecté: {detected}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur magic_fallback: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("TESTS DE VALIDATION CSV - CORRECTIONS APPLIQUÉES")
    print("=" * 80)
    
    all_success = True
    
    # Test principal
    if not test_csv_validation():
        all_success = False
    
    # Test formats variés
    format_results = test_various_csv_formats()
    if not all(format_results.values()):
        all_success = False
    
    # Test magic fallback
    if not test_magic_fallback():
        all_success = False
    
    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    if all_success:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ L'import CSV devrait maintenant fonctionner correctement")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("❌ Des corrections supplémentaires peuvent être nécessaires")
    
    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)