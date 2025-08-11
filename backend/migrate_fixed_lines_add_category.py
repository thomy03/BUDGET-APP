#!/usr/bin/env python3
"""
Script de migration pour ajouter le champ 'category' à la table fixed_lines
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Ajouter le chemin du backend
sys.path.append('/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend')

from app import FixedLine, Base

def migrate_fixed_lines_add_category():
    """Ajoute le champ category à la table fixed_lines si nécessaire"""
    
    # Connexion à la base
    DATABASE_URL = "sqlite:///budget.db"
    engine = create_engine(DATABASE_URL)
    
    # Vérifier si la colonne existe déjà
    inspector = inspect(engine)
    columns = inspector.get_columns('fixed_lines')
    column_names = [col['name'] for col in columns]
    
    print("🔍 Colonnes actuelles de fixed_lines:")
    for col_name in column_names:
        print(f"   • {col_name}")
    
    if 'category' in column_names:
        print("✅ La colonne 'category' existe déjà")
        return True
    
    print("\n🔧 Ajout de la colonne 'category'...")
    
    try:
        # Ajouter la colonne category avec une valeur par défaut
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE fixed_lines ADD COLUMN category VARCHAR DEFAULT 'autres'"))
            conn.commit()
            
        print("✅ Colonne 'category' ajoutée avec succès")
        
        # Vérification
        inspector = inspect(engine)
        columns = inspector.get_columns('fixed_lines')
        column_names = [col['name'] for col in columns]
        
        if 'category' in column_names:
            print("✅ Migration confirmée")
            
            # Mise à jour des lignes existantes avec des catégories logiques
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()
            
            try:
                # Récupérer toutes les lignes
                lines = db.query(FixedLine).all()
                print(f"\n📝 Mise à jour de {len(lines)} lignes existantes...")
                
                # Mapper automatiquement selon le libellé
                category_mapping = {
                    'électricité': 'logement',
                    'gaz': 'logement',
                    'eau': 'logement',
                    'internet': 'services',
                    'téléphone': 'services',
                    'assurance auto': 'transport',
                    'assurance voiture': 'transport',
                    'essence': 'transport',
                    'carburant': 'transport',
                    'assurance habitation': 'logement',
                    'mutuelle': 'santé',
                    'santé': 'santé',
                    'gym': 'loisirs',
                    'sport': 'loisirs',
                    'netflix': 'loisirs',
                    'spotify': 'loisirs'
                }
                
                for line in lines:
                    if line.category == 'autres':  # Uniquement si pas encore catégorisé
                        label_lower = (line.label or '').lower()
                        found_category = 'autres'
                        
                        for keyword, category in category_mapping.items():
                            if keyword in label_lower:
                                found_category = category
                                break
                        
                        line.category = found_category
                        print(f"   • '{line.label}' → {found_category}")
                
                db.commit()
                print("✅ Catégorisation automatique terminée")
                
            finally:
                db.close()
                
            return True
        else:
            print("❌ Échec de la migration")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        return False

def verify_fixed_lines_structure():
    """Vérifie la structure de la table fixed_lines"""
    DATABASE_URL = "sqlite:///budget.db"
    engine = create_engine(DATABASE_URL)
    
    inspector = inspect(engine)
    
    if 'fixed_lines' not in inspector.get_table_names():
        print("❌ Table fixed_lines n'existe pas")
        return False
    
    columns = inspector.get_columns('fixed_lines')
    print("\n📋 Structure complète de fixed_lines:")
    
    for col in columns:
        default_info = f"DEFAULT: {col['default']}" if col['default'] else ""
        print(f"   • {col['name']:15} {str(col['type']):15} {default_info}")
    
    return True

if __name__ == "__main__":
    print("🚀 Migration fixed_lines - Ajout du champ 'category'")
    print("=" * 50)
    
    # Vérifier la structure actuelle
    if verify_fixed_lines_structure():
        # Effectuer la migration
        success = migrate_fixed_lines_add_category()
        
        if success:
            print("\n✅ Migration réussie!")
            print("\nCatégories disponibles:")
            print("   • logement (électricité, gaz, eau, assurance habitation)")
            print("   • transport (assurance auto, essence, réparations)")  
            print("   • services (internet, téléphone, banque)")
            print("   • loisirs (Netflix, sport, sorties)")
            print("   • santé (mutuelle, médecin, pharmacie)")
            print("   • autres (divers)")
        else:
            print("\n❌ Migration échouée")
            sys.exit(1)
    else:
        print("\n❌ Impossible de vérifier la structure de la table")
        sys.exit(1)