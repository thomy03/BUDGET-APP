#!/usr/bin/env python3
"""Test direct de l'authentification"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash stocké dans la base
stored_hash = "$2b$12$N1BHKdi0fjTPgk3/aYYOCuBCjYY3hpq/7cmPnoMLXJ5wYafUpZP/u"

# Test avec le mot de passe "secret"
password = "secret"

result = pwd_context.verify(password, stored_hash)
print(f"Vérification du mot de passe 'secret': {result}")

# Créer un nouveau hash pour "secret"
new_hash = pwd_context.hash("secret")
print(f"\nNouveau hash pour 'secret': {new_hash}")
print(f"Vérification du nouveau hash: {pwd_context.verify('secret', new_hash)}")