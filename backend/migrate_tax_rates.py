#!/usr/bin/env python3
"""
Script de migration pour ajouter les colonnes tax_rate1 et tax_rate2 à la table config
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database():
    """Ajoute les colonnes tax_rate1 et tax_rate2 à la table config si elles n'existent pas"""
    
    # Chemins possibles pour la base de données
    db_paths = [
        Path("budget.db"),
        Path("/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/budget.db"),
        Path("./backend/budget.db")
    ]
    
    # Trouver la base de données
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            print(f"✅ Base de données trouvée: {db_path}")
            break
    
    if not db_path:
        print("❌ Base de données introuvable!")
        sys.exit(1)
    
    try:
        # Se connecter à la base de données
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Vérifier les colonnes existantes
        cursor.execute("PRAGMA table_info(config)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Colonnes actuelles: {columns}")
        
        # Ajouter tax_rate1 si elle n'existe pas
        if 'tax_rate1' not in columns:
            print("➕ Ajout de la colonne tax_rate1...")
            cursor.execute("ALTER TABLE config ADD COLUMN tax_rate1 REAL DEFAULT 0.0")
            print("✅ Colonne tax_rate1 ajoutée")
        else:
            print("ℹ️ La colonne tax_rate1 existe déjà")
        
        # Ajouter tax_rate2 si elle n'existe pas
        if 'tax_rate2' not in columns:
            print("➕ Ajout de la colonne tax_rate2...")
            cursor.execute("ALTER TABLE config ADD COLUMN tax_rate2 REAL DEFAULT 0.0")
            print("✅ Colonne tax_rate2 ajoutée")
        else:
            print("ℹ️ La colonne tax_rate2 existe déjà")
        
        # Valider les changements
        conn.commit()
        
        # Vérifier les nouvelles colonnes
        cursor.execute("PRAGMA table_info(config)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Colonnes après migration: {new_columns}")
        
        # Vérifier les données existantes
        cursor.execute("SELECT id, member1, member2, rev1, rev2, tax_rate1, tax_rate2 FROM config LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"📊 Données de test: ID={row[0]}, {row[1]}={row[3]}€ (tax={row[5]}%), {row[2]}={row[4]}€ (tax={row[6]}%)")
        
        conn.close()
        print("✅ Migration terminée avec succès!")
        
    except sqlite3.Error as e:
        print(f"❌ Erreur SQLite: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_database()