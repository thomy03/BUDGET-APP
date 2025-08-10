#!/usr/bin/env python3
"""
Script d'organisation des backups de base de données
Organise les 17+ fichiers de backup dans une structure propre
"""

import os
import sys
import shutil
import logging
from datetime import datetime
from pathlib import Path
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_backup_structure():
    """Crée la structure de dossiers pour les backups"""
    base_dir = Path("./db_backups")
    
    # Créer les dossiers
    folders = {
        'daily': base_dir / 'daily',
        'archive': base_dir / 'archive', 
        'migration': base_dir / 'migration_history',
        'recovery': base_dir / 'recovery_points'
    }
    
    for name, path in folders.items():
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Dossier '{name}' créé: {path}")
    
    return folders

def parse_backup_filename(filename):
    """Parse les noms de fichiers backup pour extraire les métadonnées"""
    # Pattern: budget.db.backup_YYYYMMDD_HHMMSS_XXXXX
    pattern = r'budget\.db\.backup_(\d{8})_(\d{6})_(\d+)'
    match = re.match(pattern, filename)
    
    if match:
        date_str, time_str, pid = match.groups()
        try:
            backup_date = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            return {
                'date': backup_date,
                'pid': int(pid),
                'is_valid': True
            }
        except ValueError:
            pass
    
    return {'is_valid': False}

def organize_backups(dry_run=True):
    """Organise les fichiers de backup"""
    current_dir = Path(".")
    folders = setup_backup_structure()
    
    # Trouver tous les fichiers backup
    backup_files = list(current_dir.glob("budget.db.backup_*"))
    logger.info(f"🔍 Trouvé {len(backup_files)} fichiers de backup")
    
    if not backup_files:
        logger.warning("Aucun fichier de backup trouvé")
        return
    
    # Analyser et organiser
    organized = {'daily': [], 'archive': [], 'errors': []}
    today = datetime.now().date()
    
    for backup_file in backup_files:
        metadata = parse_backup_filename(backup_file.name)
        
        if not metadata['is_valid']:
            organized['errors'].append(backup_file)
            logger.warning(f"❌ Fichier backup invalide: {backup_file.name}")
            continue
        
        backup_date = metadata['date'].date()
        age_days = (today - backup_date).days
        
        # Logique d'organisation
        if age_days <= 7:
            # Backups récents (dernière semaine) -> daily
            target_folder = folders['daily']
            organized['daily'].append((backup_file, metadata))
        else:
            # Anciens backups -> archive
            target_folder = folders['archive']
            organized['archive'].append((backup_file, metadata))
        
        # Calculer le nouveau nom avec date lisible
        new_name = f"budget_backup_{metadata['date'].strftime('%Y%m%d_%H%M%S')}_pid{metadata['pid']}.db"
        target_path = target_folder / new_name
        
        if dry_run:
            logger.info(f"📋 SIMULATION: {backup_file.name} -> {target_path}")
        else:
            try:
                shutil.move(str(backup_file), str(target_path))
                logger.info(f"✅ Déplacé: {backup_file.name} -> {target_path}")
            except Exception as e:
                logger.error(f"❌ Erreur déplacement {backup_file.name}: {e}")
                organized['errors'].append(backup_file)
    
    # Résumé
    logger.info("\n" + "="*60)
    logger.info("📊 RÉSUMÉ DE L'ORGANISATION")
    logger.info("="*60)
    logger.info(f"🗂️  Backups daily (≤7 jours): {len(organized['daily'])}")
    logger.info(f"📦 Backups archive (>7 jours): {len(organized['archive'])}")
    logger.info(f"❌ Fichiers en erreur: {len(organized['errors'])}")
    
    if not dry_run:
        # Créer un index des backups organisés
        create_backup_index(folders, organized)
    
    return organized

def create_backup_index(folders, organized):
    """Crée un index des backups organisés"""
    index_file = folders['daily'].parent / "backup_index.txt"
    
    try:
        with open(index_file, 'w') as f:
            f.write("# INDEX DES BACKUPS BUDGET FAMILLE v2.3\n")
            f.write(f"# Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## BACKUPS RÉCENTS (daily/)\n")
            for backup_file, metadata in organized['daily']:
                f.write(f"- {backup_file.name} ({metadata['date'].strftime('%Y-%m-%d %H:%M:%S')})\n")
            
            f.write("\n## BACKUPS ARCHIVÉS (archive/)\n") 
            for backup_file, metadata in organized['archive']:
                f.write(f"- {backup_file.name} ({metadata['date'].strftime('%Y-%m-%d %H:%M:%S')})\n")
            
            if organized['errors']:
                f.write("\n## FICHIERS EN ERREUR\n")
                for error_file in organized['errors']:
                    f.write(f"- {error_file.name}\n")
        
        logger.info(f"📋 Index créé: {index_file}")
        
    except Exception as e:
        logger.error(f"❌ Erreur création index: {e}")

def cleanup_old_backups(folders, keep_daily=7, keep_archive=30):
    """Nettoie les anciens backups selon la politique de rétention"""
    logger.info(f"🧹 Nettoyage: garder {keep_daily} daily, {keep_archive} archive")
    
    today = datetime.now()
    
    # Nettoyage daily
    daily_files = list(folders['daily'].glob("budget_backup_*.db"))
    daily_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    for i, backup_file in enumerate(daily_files):
        if i >= keep_daily:
            logger.info(f"🗑️  Suppression daily: {backup_file.name}")
            backup_file.unlink()
    
    # Nettoyage archive
    archive_files = list(folders['archive'].glob("budget_backup_*.db"))
    for backup_file in archive_files:
        file_age = (today.timestamp() - backup_file.stat().st_mtime) / (24 * 3600)
        if file_age > keep_archive:
            logger.info(f"🗑️  Suppression archive: {backup_file.name}")
            backup_file.unlink()

def main():
    """Point d'entrée principal"""
    print("\n" + "="*60)
    print("🗂️  ORGANISATION DES BACKUPS BUDGET FAMILLE v2.3")
    print("="*60)
    
    # Arguments
    dry_run = '--execute' not in sys.argv
    cleanup = '--cleanup' in sys.argv
    
    if dry_run:
        print("📋 MODE SIMULATION (ajoutez --execute pour appliquer)")
    else:
        print("🚀 MODE EXÉCUTION")
    
    try:
        # Organisation des backups
        organized = organize_backups(dry_run=dry_run)
        
        if not dry_run and cleanup:
            folders = setup_backup_structure()
            cleanup_old_backups(folders)
        
        print("\n✅ Organisation terminée avec succès!")
        
        if dry_run:
            print("\n💡 Pour appliquer les changements:")
            print("   python organize_db_backups.py --execute")
            print("   python organize_db_backups.py --execute --cleanup")
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())