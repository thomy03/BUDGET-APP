#!/usr/bin/env python3
"""
Script de génération de hash bcrypt pour les mots de passe
"""

from passlib.context import CryptContext
import sys

def generate_hash(password):
    """Génère un hash bcrypt pour le mot de passe donné"""
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    return pwd_context.hash(password)

def verify_hash(password, hashed_password):
    """Vérifie un mot de passe contre son hash"""
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    return pwd_context.verify(password, hashed_password)

def main():
    print("🔐 GÉNÉRATEUR DE HASH BCRYPT")
    print("=" * 40)
    
    # Test du hash actuel
    current_hash = "$2b$12$4A9H9JK7bYMdk7oYEeO/a.2FqfkGRp2HPvrx4BKEjDpYdM/Zmyf0G"
    password = "secret"
    
    print(f"Mot de passe: {password}")
    print(f"Hash actuel:  {current_hash}")
    
    # Vérification du hash actuel
    is_valid = verify_hash(password, current_hash)
    print(f"Hash valide:  {'✅ OUI' if is_valid else '❌ NON'}")
    
    if not is_valid:
        print("\n🔧 Génération d'un nouveau hash...")
        new_hash = generate_hash(password)
        print(f"Nouveau hash: {new_hash}")
        
        # Vérification du nouveau hash
        new_is_valid = verify_hash(password, new_hash)
        print(f"Nouveau hash valide: {'✅ OUI' if new_is_valid else '❌ NON'}")
        
        if new_is_valid:
            print("\n📝 Code à utiliser dans auth.py:")
            print(f'    "hashed_password": "{new_hash}"')
    else:
        print("\n✅ Le hash actuel est correct, aucune modification nécessaire")
    
    print("\n" + "=" * 40)
    return 0 if is_valid else 1

if __name__ == "__main__":
    sys.exit(main())