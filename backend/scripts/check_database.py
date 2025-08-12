#!/usr/bin/env python3
"""
Script de vérification de la base de données SQLite
"""
import sqlite3
import sys
import hashlib

def check_database():
    try:
        conn = sqlite3.connect('budget.db')
        cursor = conn.cursor()
        
        print("=== ANALYSE DE LA BASE DE DONNÉES ===\n")
        
        # Lister toutes les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("📋 Tables disponibles:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Vérifier si une table d'utilisateurs existe
        user_tables = [t[0] for t in tables if 'user' in t[0].lower()]
        if user_tables:
            print(f"\n👤 Tables utilisateurs trouvées: {user_tables}")
            for table_name in user_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} enregistrements")
                
                # Afficher la structure de la table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"    Colonnes: {[col[1] for col in columns]}")
        else:
            print("👤 Aucune table utilisateur trouvée dans la base")
        
        # Vérifier la configuration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config';")
        config_table = cursor.fetchone()
        if config_table:
            print("\n⚙️  Table de configuration trouvée:")
            cursor.execute("SELECT * FROM config")
            configs = cursor.fetchall()
            print(f"  - {len(configs)} configurations")
        
        # Afficher les autres tables importantes
        print("\n📊 Autres tables:")
        for table in tables:
            table_name = table[0]
            if table_name not in ['sqlite_sequence'] and 'user' not in table_name.lower():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} enregistrements")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse de la base: {e}")
        return False

def check_auth_config():
    """Vérifier la configuration d'authentification dans auth.py"""
    print("\n=== CONFIGURATION AUTHENTIFICATION ===\n")
    
    try:
        from auth import fake_users_db, pwd_context
        
        print("👥 Utilisateurs configurés dans fake_users_db:")
        for username, user_data in fake_users_db.items():
            print(f"  - Utilisateur: {username}")
            print(f"    Hash: {user_data['hashed_password'][:20]}...")
            
            # Tester la vérification du mot de passe
            test_password = "secret"
            is_valid = pwd_context.verify(test_password, user_data['hashed_password'])
            print(f"    Test mot de passe '{test_password}': {'✅ Valide' if is_valid else '❌ Invalide'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification de l'auth: {e}")
        return False

if __name__ == "__main__":
    success1 = check_database()
    success2 = check_auth_config()
    
    if success1 and success2:
        print("\n✅ Vérification terminée avec succès")
        sys.exit(0)
    else:
        print("\n❌ Vérification terminée avec des erreurs")
        sys.exit(1)