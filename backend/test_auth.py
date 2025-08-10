#!/usr/bin/env python3

from auth import verify_password, get_password_hash, authenticate_user, fake_users_db

# Test 1: Vérifier que le hash "secret" fonctionne
secret_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p02FZZE4b5qedxCUt8WQ.95."
print("Test 1 - Vérification du hash 'secret':")
print(f"verify_password('secret', hash): {verify_password('secret', secret_hash)}")
print()

# Test 2: Créer un nouveau hash et le tester
print("Test 2 - Création nouveau hash:")
new_hash = get_password_hash("secret")
print(f"Nouveau hash: {new_hash}")
print(f"verify_password('secret', nouveau_hash): {verify_password('secret', new_hash)}")
print()

# Test 3: Test de l'authentification complète
print("Test 3 - Authentification complète:")
print(f"fake_users_db admin: {fake_users_db.get('admin')}")
user = authenticate_user(fake_users_db, "admin", "secret")
print(f"authenticate_user result: {user}")
print()

# Test 4: Essayer avec un hash simple (pour debug)
print("Test 4 - Diagnostics:")
stored_hash = fake_users_db["admin"]["hashed_password"]
print(f"Hash stocké: {stored_hash}")
print(f"Longueur hash: {len(stored_hash)}")
print(f"Commence par $2b$: {stored_hash.startswith('$2b$')}")