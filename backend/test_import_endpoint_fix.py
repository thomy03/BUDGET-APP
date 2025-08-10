#!/usr/bin/env python3
"""
Test complet de l'endpoint /import avec les corrections CSV
"""
import os
import sys
import requests
import json
from datetime import datetime

# Configuration de test
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "secret123"

def get_auth_token():
    """Obtient un token d'authentification"""
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            data={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data["access_token"]
        else:
            print(f"❌ Échec authentification: {response.status_code}")
            print(f"Réponse: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erreur authentification: {e}")
        return None

def test_import_endpoint():
    """Test de l'endpoint /import avec le fichier CSV corrigé"""
    print("=" * 80)
    print("TEST ENDPOINT /import - CORRECTIONS CSV")
    print("=" * 80)
    
    # 1. Vérifier que le serveur est accessible
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Serveur FastAPI non accessible")
            return False
        print("✅ Serveur FastAPI accessible")
    except Exception as e:
        print(f"❌ Erreur connexion serveur: {e}")
        print("ℹ️  Assurez-vous que le serveur est démarré avec: python3 app.py")
        return False
    
    # 2. Authentification
    token = get_auth_token()
    if not token:
        return False
    print("✅ Authentification réussie")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 3. Test d'import avec le fichier CSV problématique
    test_file = "01_happy_path_janvier_2024.csv"
    
    if not os.path.exists(test_file):
        print(f"❌ Fichier de test {test_file} non trouvé")
        return False
    
    try:
        with open(test_file, 'rb') as f:
            files = {
                'file': (test_file, f, 'text/csv')
            }
            
            print(f"📤 Upload du fichier: {test_file}")
            response = requests.post(
                f"{BASE_URL}/import",
                files=files,
                headers=headers,
                timeout=30
            )
        
        print(f"📥 Statut de réponse: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Import réussi!")
            
            # Afficher les détails de l'import
            print(f"🆔 Import ID: {data.get('importId')}")
            print(f"📁 Fichier: {data.get('fileName')}")
            print(f"📊 Mois détectés: {len(data.get('months', []))}")
            print(f"🔄 Doublons: {data.get('duplicatesCount', 0)}")
            print(f"⚠️  Warnings: {len(data.get('warnings', []))}")
            print(f"⏱️  Temps de traitement: {data.get('processingMs', 0)}ms")
            
            if data.get('months'):
                for month in data['months']:
                    print(f"  📅 {month['month']}: {month['newCount']} nouvelles transactions")
            
            if data.get('suggestedMonth'):
                print(f"🎯 Mois suggéré: {data['suggestedMonth']}")
            
            return True
            
        elif response.status_code == 400:
            print("❌ Erreur de validation (400)")
            print(f"Détail: {response.text}")
            return False
            
        elif response.status_code == 401:
            print("❌ Erreur d'authentification (401)")
            return False
            
        elif response.status_code == 413:
            print("❌ Fichier trop volumineux (413)")
            return False
            
        else:
            print(f"❌ Erreur inattendue: {response.status_code}")
            print(f"Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_csv_formats():
    """Test avec différents formats CSV"""
    print("\n" + "=" * 80)
    print("TEST FORMATS CSV VARIÉS")
    print("=" * 80)
    
    # Obtenir le token
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test avec différents formats
    test_formats = {
        "semicolon.csv": "Date;Description;Montant\n2024-01-01;Test Semicolon;-50.00\n",
        "pipe_separated.csv": "Date|Description|Amount\n2024-01-01|Test Pipe|100.00\n",
        "tab_separated.csv": "Date\tDescription\tAmount\n2024-01-01\tTest Tab\t75.50\n"
    }
    
    results = {}
    
    for filename, content in test_formats.items():
        try:
            # Créer fichier temporaire
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Tester l'import
            with open(filename, 'rb') as f:
                files = {'file': (filename, f, 'text/csv')}
                response = requests.post(
                    f"{BASE_URL}/import",
                    files=files,
                    headers=headers,
                    timeout=15
                )
            
            results[filename] = response.status_code == 200
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {filename}: {response.status_code}")
            
            # Nettoyage
            if os.path.exists(filename):
                os.unlink(filename)
                
        except Exception as e:
            results[filename] = False
            print(f"❌ {filename}: Erreur - {e}")
    
    return all(results.values())

def main():
    """Fonction principale"""
    print("TESTS ENDPOINT /import - CORRECTIONS CSV")
    print("=" * 120)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL de test: {BASE_URL}")
    print(f"👤 Utilisateur: {TEST_USERNAME}")
    
    success = True
    
    # Test principal
    if not test_import_endpoint():
        success = False
    
    # Test formats variés
    if not test_different_csv_formats():
        success = False
    
    # Résumé final
    print("\n" + "=" * 120)
    print("RÉSUMÉ TESTS ENDPOINT")
    print("=" * 120)
    
    if success:
        print("🎉 TOUS LES TESTS D'IMPORT SONT PASSÉS!")
        print("✅ L'endpoint /import fonctionne correctement avec les fichiers CSV")
        print("✅ Les corrections de validation ont résolu le problème de signature binaire")
    else:
        print("⚠️  CERTAINS TESTS D'IMPORT ONT ÉCHOUÉ")
        print("❌ Vérifiez la configuration du serveur et l'authentification")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)