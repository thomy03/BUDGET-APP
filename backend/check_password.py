#!/usr/bin/env python3
"""
Check what password matches the stored hash
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash from auth.py
stored_hash = "$2b$12$4A9H9JK7bYMdk7oYEeO/a.2FqfkGRp2HPvrx4BKEjDpYdM/Zmyf0G"

# Common passwords to test
passwords_to_test = [
    "secret",
    "admin",
    "admin123", 
    "password",
    "123456",
    "test",
    "changeme"
]

print("Testing passwords against stored hash...")
for password in passwords_to_test:
    if pwd_context.verify(password, stored_hash):
        print(f"✅ MATCH: Password '{password}' matches the hash")
    else:
        print(f"❌ NO MATCH: Password '{password}' does not match")

print(f"\nStored hash: {stored_hash}")