#!/usr/bin/env python3
"""
Script de debug pour vérifier les utilisateurs et générer un token
"""
import sqlite3
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os

# Configuration JWT
SECRET_KEY = "ktHAFqwWuGhkPJiPRXgN0STKjETO0Q9g-1I1zqiKvPM"
ALGORITHM = "HS256"

def check_users():
    """Vérifier les utilisateurs existants"""
    try:
        conn = sqlite3.connect("budget.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, is_active, is_admin FROM users")
        users = cursor.fetchall()
        
        if users:
            print("Utilisateurs trouvés :")
            for user in users:
                print(f"- {user[0]} (actif: {user[1]}, admin: {user[2]})")
        else:
            print("Aucun utilisateur trouvé dans la base")
        
        conn.close()
        return users
    except Exception as e:
        print(f"Erreur lors de la vérification des utilisateurs : {e}")
        return []

def create_test_user():
    """Créer un utilisateur de test"""
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("admin123")
        
        conn = sqlite3.connect("budget.db")
        cursor = conn.cursor()
        
        # Créer la table si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE,
                full_name VARCHAR(100),
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                last_login DATETIME,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                created_by VARCHAR(50)
            )
        """)
        
        # Insérer un utilisateur de test
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (username, hashed_password, is_active, is_admin, full_name)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", hashed_password, 1, 1, "Administrateur Test"))
        
        conn.commit()
        conn.close()
        print("Utilisateur 'admin' créé avec mot de passe 'admin123'")
        
    except Exception as e:
        print(f"Erreur lors de la création de l'utilisateur : {e}")

def generate_token(username):
    """Générer un token JWT pour un utilisateur"""
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

if __name__ == "__main__":
    print("=== Debug Authentification ===")
    
    # Vérifier les utilisateurs existants
    users = check_users()
    
    # Si pas d'utilisateur, en créer un
    if not users:
        print("\nCréation d'un utilisateur de test...")
        create_test_user()
        users = check_users()
    
    # Générer un token pour admin
    if users:
        admin_user = next((u for u in users if u[0] == "admin"), None)
        if admin_user:
            token = generate_token("admin")
            print(f"\nToken généré pour admin:")
            print(f"Authorization: Bearer {token}")
        else:
            print("\nUtilisateur 'admin' non trouvé")