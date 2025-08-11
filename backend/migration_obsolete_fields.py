#!/usr/bin/env python3
"""
Migration des anciens champs obsolètes vers les nouveaux systèmes
- Provisions vacances → CustomProvision
- Crédits et charges fixes → FixedLine
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Ajouter le répertoire parent au path pour importer nos modèles
sys.path.append(str(Path(__file__).parent))

from app import Config, CustomProvision, FixedLine, Base

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./budget.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_vacation_provisions(db_session):
    """Migre les anciennes provisions vacances vers CustomProvision"""
    
    print("🔄 Migration des provisions vacances...")
    
    configs_with_vacation = db_session.query(Config).filter(
        (Config.vac_percent > 0) | (Config.vac_base.isnot(None))
    ).all()
    
    migrated_count = 0
    
    for config in configs_with_vacation:
        if not config.vac_percent or config.vac_percent <= 0:
            continue
            
        # Vérifier si une provision vacances existe déjà
        existing_provision = db_session.query(CustomProvision).filter(
            CustomProvision.created_by == "system",  # Assumons que les migrations sont créées par "system"
            CustomProvision.name == "Provision vacances (migrée)"
        ).first()
        
        if existing_provision:
            print(f"  ⚠️  Provision vacances déjà migrée pour la config {config.id}")
            continue
            
        # Calculer la base selon l'ancien système
        base_description = ""
        if config.vac_base == "2":
            base_description = "basée sur revenus combinés"
        elif config.vac_base == "1":
            base_description = "basée sur revenus membre 1"
        elif config.vac_base == "2nd":
            base_description = "basée sur revenus membre 2"
        else:
            base_description = "basée sur revenus combinés"
            
        # Créer la nouvelle provision personnalisable
        new_provision = CustomProvision(
            name="Provision vacances (migrée)",
            description=f"Ancienne provision vacances ({config.vac_percent}% {base_description})",
            percentage=config.vac_percent,
            base_calculation=config.vac_base or "2",  # Default à revenus combinés
            fixed_amount=None,
            target_amount=None,
            current_amount=0.0,
            category="savings",
            icon="🏖️",
            is_active=True,
            created_by="system",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            display_order=1,
            start_date=None,
            end_date=None
        )
        
        db_session.add(new_provision)
        migrated_count += 1
        
        print(f"  ✅ Provision vacances migrée: {config.vac_percent}% {base_description}")
    
    print(f"📊 Migration provisions: {migrated_count} éléments migrés")
    return migrated_count


def migrate_fixed_expenses(db_session):
    """Migre les anciens crédits et charges fixes vers FixedLine"""
    
    print("🔄 Migration des dépenses fixes...")
    
    configs_with_fixed = db_session.query(Config).all()
    migrated_count = 0
    
    for config in configs_with_fixed:
        
        # 1. Migration du crédit immobilier
        if config.loan_amount and config.loan_amount > 0:
            existing_loan = db_session.query(FixedLine).filter(
                FixedLine.label == "Crédit immobilier (migré)"
            ).first()
            
            if not existing_loan:
                split_mode = "50/50" if config.loan_equal else "clé"
                
                loan_line = FixedLine(
                    label="Crédit immobilier (migré)",
                    amount=config.loan_amount,
                    freq="mensuelle",
                    split_mode=split_mode,
                    split1=0.5,  # Sera recalculé selon la clé si nécessaire
                    split2=0.5,
                    category="logement",
                    active=True
                )
                
                db_session.add(loan_line)
                migrated_count += 1
                print(f"  ✅ Crédit immobilier migré: {config.loan_amount}€ ({split_mode})")
        
        # 2. Migration des autres charges fixes (mode simple)
        if config.other_fixed_simple and config.other_fixed_monthly and config.other_fixed_monthly > 0:
            existing_other = db_session.query(FixedLine).filter(
                FixedLine.label == "Autres charges fixes (migrées)"
            ).first()
            
            if not existing_other:
                split_mode = "50/50" if config.other_split_mode == "50/50" else "clé"
                
                other_line = FixedLine(
                    label="Autres charges fixes (migrées)",
                    amount=config.other_fixed_monthly,
                    freq="mensuelle",
                    split_mode=split_mode,
                    split1=0.5,
                    split2=0.5,
                    category="autres",
                    active=True
                )
                
                db_session.add(other_line)
                migrated_count += 1
                print(f"  ✅ Autres charges fixes migrées: {config.other_fixed_monthly}€ ({split_mode})")
        
        # 3. Migration de la taxe foncière (mode détaillé)
        if not config.other_fixed_simple and config.taxe_fonciere_ann and config.taxe_fonciere_ann > 0:
            existing_taxe = db_session.query(FixedLine).filter(
                FixedLine.label == "Taxe foncière (migrée)"
            ).first()
            
            if not existing_taxe:
                split_mode = "50/50" if config.other_split_mode == "50/50" else "clé"
                
                taxe_line = FixedLine(
                    label="Taxe foncière (migrée)",
                    amount=config.taxe_fonciere_ann,
                    freq="annuelle",
                    split_mode=split_mode,
                    split1=0.5,
                    split2=0.5,
                    category="logement",
                    active=True
                )
                
                db_session.add(taxe_line)
                migrated_count += 1
                print(f"  ✅ Taxe foncière migrée: {config.taxe_fonciere_ann}€/an ({split_mode})")
        
        # 4. Migration de la copropriété (mode détaillé)
        if not config.other_fixed_simple and config.copro_montant and config.copro_montant > 0:
            existing_copro = db_session.query(FixedLine).filter(
                FixedLine.label == "Copropriété (migrée)"
            ).first()
            
            if not existing_copro:
                split_mode = "50/50" if config.other_split_mode == "50/50" else "clé"
                freq = config.copro_freq or "mensuelle"
                
                copro_line = FixedLine(
                    label="Copropriété (migrée)",
                    amount=config.copro_montant,
                    freq=freq,
                    split_mode=split_mode,
                    split1=0.5,
                    split2=0.5,
                    category="logement",
                    active=True
                )
                
                db_session.add(copro_line)
                migrated_count += 1
                print(f"  ✅ Copropriété migrée: {config.copro_montant}€ {freq} ({split_mode})")
    
    print(f"📊 Migration dépenses fixes: {migrated_count} éléments migrés")
    return migrated_count


def backup_old_data(db_session):
    """Sauvegarde les anciennes données avant suppression"""
    
    print("💾 Sauvegarde des anciennes données...")
    
    # Créer une table de sauvegarde
    backup_sql = """
    CREATE TABLE IF NOT EXISTS config_obsolete_fields_backup AS 
    SELECT 
        id,
        vac_percent,
        vac_base,
        loan_amount,
        loan_equal,
        other_fixed_simple,
        other_fixed_monthly,
        taxe_fonciere_ann,
        copro_montant,
        copro_freq,
        datetime('now') as backup_date
    FROM config
    WHERE vac_percent > 0 
       OR loan_amount > 0 
       OR other_fixed_monthly > 0 
       OR taxe_fonciere_ann > 0 
       OR copro_montant > 0;
    """
    
    db_session.execute(text(backup_sql))
    
    # Compter les sauvegardes
    count_result = db_session.execute(text("SELECT COUNT(*) FROM config_obsolete_fields_backup")).fetchone()
    backup_count = count_result[0] if count_result else 0
    
    print(f"✅ {backup_count} configurations sauvegardées dans config_obsolete_fields_backup")
    return backup_count


def remove_obsolete_columns():
    """Supprime les colonnes obsolètes de la table config"""
    
    print("🗑️  Suppression des colonnes obsolètes...")
    
    # SQLite ne permet pas de supprimer des colonnes directement
    # On doit recréer la table
    
    migration_sql = """
    -- Créer la nouvelle table sans les colonnes obsolètes
    CREATE TABLE config_new AS 
    SELECT 
        id, member1, member2, rev1, rev2, other_split_mode, var_percent, max_var, min_fixed, created_at, updated_at
    FROM config;
    
    -- Supprimer l'ancienne table
    DROP TABLE config;
    
    -- Renommer la nouvelle table
    ALTER TABLE config_new RENAME TO config;
    """
    
    return migration_sql


def main():
    """Fonction principale de migration"""
    
    print("🚀 Début de la migration des champs obsolètes")
    print("=" * 60)
    
    db_session = SessionLocal()
    
    try:
        # 1. Sauvegarde des données
        backup_count = backup_old_data(db_session)
        
        # 2. Migration des provisions vacances
        vacation_count = migrate_vacation_provisions(db_session)
        
        # 3. Migration des dépenses fixes
        fixed_count = migrate_fixed_expenses(db_session)
        
        # 4. Commit des migrations
        db_session.commit()
        
        print("=" * 60)
        print("✅ Migration terminée avec succès!")
        print(f"📊 Résumé:")
        print(f"   - {backup_count} configurations sauvegardées")
        print(f"   - {vacation_count} provisions vacances migrées")
        print(f"   - {fixed_count} dépenses fixes migrées")
        print()
        print("⚠️  ATTENTION: Les colonnes obsolètes n'ont pas encore été supprimées.")
        print("   Vérifiez que tout fonctionne correctement avant d'exécuter la suppression.")
        print("   Pour supprimer les colonnes: python migration_obsolete_fields.py --drop-columns")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        db_session.rollback()
        return 1
        
    finally:
        db_session.close()
    
    return 0


if __name__ == "__main__":
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop-columns":
        print("🗑️  Mode suppression des colonnes obsolètes")
        print("⚠️  ATTENTION: Cette opération est irréversible!")
        response = input("Êtes-vous sûr de vouloir continuer? (oui/NON): ")
        
        if response.lower() != "oui":
            print("❌ Opération annulée")
            sys.exit(1)
            
        # TODO: Implémenter la suppression des colonnes
        print("🚧 Suppression des colonnes en cours de développement...")
        
    else:
        sys.exit(main())