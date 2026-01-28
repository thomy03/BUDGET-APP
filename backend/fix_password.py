"""
Script pour regenerer le hash du mot de passe admin
Compatible avec bcrypt 4.x et passlib
"""
import bcrypt

# Mot de passe en clair
password = "secret"

# Generer un nouveau hash avec bcrypt directement
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

print(f"Mot de passe: {password}")
print(f"Nouveau hash: {hashed.decode('utf-8')}")
print()
print("Copiez ce hash dans auth.py ligne 80:")
print(f'        "hashed_password": "{hashed.decode("utf-8")}"')
