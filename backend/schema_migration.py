#!/usr/bin/env python3
"""
Migration du schéma de base de données - ajout des nouveaux champs au modèle Config
"""

import sqlite3
import os
from pathlib import Path

def migrate_config_schema():
    """Ajoute les nouveaux champs au modèle Config"""
    
    db_path = "budget.db"
    if not os.path.exists(db_path):
        print("❌ Base de données introuvable")
        return False
    
    print("🔄 Migration du schéma de la table config...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Vérifier les colonnes existantes
        cursor.execute("PRAGMA table_info(config)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Nouveaux champs à ajouter
        new_columns = [
            ('var_percent', 'FLOAT DEFAULT 30.0'),
            ('max_var', 'FLOAT DEFAULT 0.0'),
            ('min_fixed', 'FLOAT DEFAULT 0.0'),
            ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('updated_at', 'DATETIME')
        ]
        
        added_count = 0
        for col_name, col_def in new_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE config ADD COLUMN {col_name} {col_def}")
                    print(f"  ✅ Colonne '{col_name}' ajoutée")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    print(f"  ⚠️  Erreur ajout colonne '{col_name}': {e}")
            else:
                print(f"  ⏭️  Colonne '{col_name}' existe déjà")
        
        conn.commit()
        print(f"📊 {added_count} colonnes ajoutées avec succès")
        
    except Exception as e:
        print(f"❌ Erreur migration schéma: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()
    
    return True


def drop_obsolete_columns():
    """Supprime les colonnes obsolètes de la table config"""
    
    db_path = "budget.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🗑️  Suppression des colonnes obsolètes...")
        
        # SQLite ne permet pas de supprimer des colonnes directement
        # Il faut recréer la table
        
        # 1. Créer une nouvelle table avec uniquement les colonnes voulues
        new_table_sql = """
        CREATE TABLE config_new (
            id INTEGER PRIMARY KEY,
            member1 VARCHAR DEFAULT 'diana',
            member2 VARCHAR DEFAULT 'thomas', 
            rev1 FLOAT DEFAULT 0.0,
            rev2 FLOAT DEFAULT 0.0,
            split_mode VARCHAR DEFAULT 'revenus',
            split1 FLOAT DEFAULT 0.5,
            split2 FLOAT DEFAULT 0.5,
            other_split_mode VARCHAR DEFAULT 'clé',
            var_percent FLOAT DEFAULT 30.0,
            max_var FLOAT DEFAULT 0.0,
            min_fixed FLOAT DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
        """
        
        cursor.execute(new_table_sql)
        
        # 2. Copier les données
        copy_sql = """
        INSERT INTO config_new (
            id, member1, member2, rev1, rev2, split_mode, split1, split2, other_split_mode,
            var_percent, max_var, min_fixed
        )
        SELECT 
            id, member1, member2, rev1, rev2, split_mode, split1, split2, other_split_mode,
            COALESCE(var_percent, 30.0) as var_percent,
            COALESCE(max_var, 0.0) as max_var, 
            COALESCE(min_fixed, 0.0) as min_fixed
        FROM config
        """
        
        cursor.execute(copy_sql)
        
        # 3. Supprimer l'ancienne table et renommer
        cursor.execute("DROP TABLE config")
        cursor.execute("ALTER TABLE config_new RENAME TO config")
        
        conn.commit()
        print("✅ Colonnes obsolètes supprimées avec succès")
        
    except Exception as e:
        print(f"❌ Erreur suppression colonnes: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()
    
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop-obsolete":
        print("🗑️  Mode suppression des colonnes obsolètes")
        print("⚠️  ATTENTION: Cette opération supprimera définitivement les anciens champs!")
        response = input("Continuer? (oui/NON): ")
        
        if response.lower() == "oui":
            if drop_obsolete_columns():
                print("🎉 Migration de schéma terminée - colonnes obsolètes supprimées")
            else:
                print("❌ Échec suppression des colonnes obsolètes")
        else:
            print("❌ Opération annulée")
    else:
        if migrate_config_schema():
            print("🎉 Migration de schéma terminée - nouveaux champs ajoutés")
            print("💡 Pour supprimer les colonnes obsolètes: python schema_migration.py --drop-obsolete")
        else:
            print("❌ Échec de la migration de schéma")