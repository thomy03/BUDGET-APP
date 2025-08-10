#!/usr/bin/env python3
"""
Script de debug pour tester l'authentification
Teste les fonctions authenticate_user et verify_password
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from auth import (
    authenticate_user, verify_password, get_password_hash,
    fake_users_db, get_user
)

def test_password_verification():
    """Test de vérification du mot de passe"""
    print("=== Test de vérification du mot de passe ===")
    
    # Hash actuel dans fake_users_db
    stored_hash = fake_users_db["admin"]["hashed_password"]
    print(f"Hash stocké: {stored_hash}")
    
    # Test avec le mot de passe "secret"
    test_password = "secret"
    print(f"Test mot de passe: '{test_password}'")
    
    result = verify_password(test_password, stored_hash)
    print(f"Résultat verify_password: {result}")
    
    # Générons un nouveau hash pour comparaison
    new_hash = get_password_hash(test_password)
    print(f"Nouveau hash généré: {new_hash}")
    
    # Test avec le nouveau hash
    result_new = verify_password(test_password, new_hash)
    print(f"Résultat avec nouveau hash: {result_new}")
    
    return result

def test_user_authentication():
    """Test d'authentification complète"""
    print("\n=== Test d'authentification complète ===")
    
    # Test récupération utilisateur
    user = get_user(fake_users_db, "admin")
    print(f"Utilisateur récupéré: {user}")
    
    # Test authentification avec admin/secret
    auth_result = authenticate_user(fake_users_db, "admin", "secret")
    print(f"Résultat authenticate_user('admin', 'secret'): {auth_result}")
    
    # Test avec mauvais mot de passe
    auth_result_bad = authenticate_user(fake_users_db, "admin", "wrong")
    print(f"Résultat authenticate_user('admin', 'wrong'): {auth_result_bad}")
    
    return auth_result is not None

def regenerate_password_hash():
    """Régénère le hash du mot de passe 'secret'"""
    print("\n=== Régénération du hash ===")
    
    password = "secret"
    new_hash = get_password_hash(password)
    print(f"Nouveau hash pour 'secret': {new_hash}")
    
    # Vérifie que le nouveau hash fonctionne
    verification = verify_password(password, new_hash)
    print(f"Vérification nouveau hash: {verification}")
    
    return new_hash

if __name__ == "__main__":
    print("🔧 Script de debug de l'authentification")
    print("=" * 50)
    
    # Test 1: Vérification du mot de passe
    password_ok = test_password_verification()
    
    # Test 2: Authentification complète
    auth_ok = test_user_authentication()
    
    # Test 3: Régénération du hash
    new_hash = regenerate_password_hash()
    
    print("\n=== RÉSUMÉ ===")
    print(f"Vérification mot de passe: {'✅ OK' if password_ok else '❌ ERREUR'}")
    print(f"Authentification: {'✅ OK' if auth_ok else '❌ ERREUR'}")
    
    if not password_ok or not auth_ok:
        print("\n🔧 SOLUTION: Remplacer le hash dans fake_users_db")
        print(f"Nouveau hash à utiliser: {new_hash}")
        print("Modifiez auth.py ligne 58 avec ce nouveau hash")
    else:
        print("✅ L'authentification fonctionne correctement")