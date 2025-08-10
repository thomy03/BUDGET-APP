#!/usr/bin/env python3
"""
SCRIPT DE MIGRATION BUDGET FAMILLE v2.3
Consolide l'architecture fragmentée vers une version unifiée pour Ubuntu/WSL
"""

import os
import sys
import shutil
import logging
from datetime import datetime
from pathlib import Path
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArchitectureConsolidator:
    """Classe principale pour la consolidation de l'architecture"""
    
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.base_path = Path(".")
        self.backup_path = Path("./migration_backup")
        self.migration_log = []
        
    def log_action(self, action_type, source, target=None, status="success"):
        """Log une action de migration"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': action_type,
            'source': str(source),
            'target': str(target) if target else None,
            'status': status
        }
        self.migration_log.append(entry)
        
        if status == "success":
            logger.info(f"✅ {action_type}: {source} -> {target if target else 'supprimé'}")
        else:
            logger.error(f"❌ {action_type}: {source} - {status}")

    def create_backup(self):
        """Crée un backup avant migration"""
        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)
        
        self.backup_path.mkdir()
        logger.info(f"📦 Backup créé dans: {self.backup_path}")
        
        # Lister les fichiers critiques à sauvegarder
        critical_files = [
            "budget.db",
            "app.py", "app_simple.py", "app_windows.py", "app_windows_optimized.py",
            "requirements.txt", "requirements_ubuntu.txt", "requirements_windows.txt",
            "auth.py", "database_encrypted.py", "audit_logger.py"
        ]
        
        for filename in critical_files:
            src_file = self.base_path / filename
            if src_file.exists():
                dest_file = self.backup_path / filename
                if not self.dry_run:
                    shutil.copy2(src_file, dest_file)
                self.log_action("backup", filename, dest_file)

    def identify_redundant_files(self):
        """Identifie les fichiers redondants à nettoyer"""
        
        # Applications redondantes (on garde app.py)
        redundant_apps = [
            "app_simple.py",
            "app_windows.py", 
            "app_windows_optimized.py",
            "app_minimal_csv.py"
        ]
        
        # Scripts de démarrage redondants
        redundant_scripts = [
            "start_windows.py",
            "start_degraded.py", 
            "start_secure.py",
            "start_complete.py"
        ]
        
        # Fichiers requirements redondants (on garde requirements.txt)
        redundant_requirements = [
            "requirements_windows.txt",
            "requirements_ubuntu.txt",
            "requirements_minimal.txt",
            "requirements_minimal_ubuntu.txt",
            "requirements_fallback.txt",
            "requirements_windows_minimal.txt"
        ]
        
        # Fichiers Windows spécifiques
        windows_files = [
            "Fix-WindowsDependencies.ps1",
            "fix_windows_dependencies.bat",
            "diagnose_windows.py",
            "diagnostic_windows.py",
            "test_windows_compatibility.py",
            "test_environment_windows.py",
            "test_windows_import.csv"
        ]
        
        # Documentation Windows redondante
        windows_docs = [
            "GUIDE_DEMARRAGE_WINDOWS.md",
            "GUIDE_DEPANNAGE_WINDOWS.md", 
            "README_WINDOWS.md",
            "README_WINDOWS_FIXES.md",
            "SOLUTION_WINDOWS.md"
        ]
        
        # Fichiers de test redondants/obsolètes
        redundant_tests = [
            "test_auth_simple.py",
            "test_auth_complete.py",
            "test_critical_fixes.py",
            "test_critical_fixes_minimal.py",
            "test_compatibility.py",
            "test_duplicates.py"
        ]
        
        # Configuration/diagnostic obsolètes
        obsolete_configs = [
            "degraded_startup_config.json",
            "diagnostic_report.json",
            "csv_critical_test_results.json",
            "token_response.json"
        ]
        
        return {
            'redundant_apps': redundant_apps,
            'redundant_scripts': redundant_scripts,
            'redundant_requirements': redundant_requirements,
            'windows_files': windows_files,
            'windows_docs': windows_docs,
            'redundant_tests': redundant_tests,
            'obsolete_configs': obsolete_configs
        }

    def organize_files(self):
        """Organise les fichiers selon la nouvelle structure"""
        
        # Créer les dossiers d'organisation
        folders = {
            'archive': self.base_path / 'archive_legacy',
            'tests': self.base_path / 'tests',
            'docs': self.base_path / 'docs_archive',
            'config': self.base_path / 'config_archive'
        }
        
        for folder in folders.values():
            if not self.dry_run:
                folder.mkdir(exist_ok=True)
            logger.info(f"📁 Dossier créé: {folder}")
        
        redundant = self.identify_redundant_files()
        
        # Déplacer les fichiers par catégorie
        moves = [
            (redundant['redundant_apps'], folders['archive']),
            (redundant['redundant_scripts'], folders['archive']),
            (redundant['redundant_requirements'], folders['archive']),
            (redundant['windows_files'], folders['archive']),
            (redundant['windows_docs'], folders['docs']),
            (redundant['redundant_tests'], folders['tests']),
            (redundant['obsolete_configs'], folders['config'])
        ]
        
        for file_list, target_folder in moves:
            for filename in file_list:
                src_file = self.base_path / filename
                if src_file.exists():
                    dest_file = target_folder / filename
                    if not self.dry_run:
                        try:
                            shutil.move(str(src_file), str(dest_file))
                            self.log_action("move", filename, dest_file)
                        except Exception as e:
                            self.log_action("move", filename, dest_file, f"error: {e}")
                    else:
                        self.log_action("move", filename, dest_file)

    def organize_backups(self):
        """Organise les backups de base de données"""
        if not self.dry_run:
            # Lancer le script d'organisation des backups
            os.system("python organize_db_backups.py --execute")
        else:
            logger.info("📋 SIMULATION: Organisation des backups DB")

    def create_startup_script(self):
        """Crée un script de démarrage unifié"""
        startup_content = '''#!/usr/bin/env python3
"""
Script de démarrage unifié Budget Famille v2.3 - Ubuntu/WSL
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Vérifie l'environnement avant démarrage"""
    # Vérifier Python version
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8+ requis")
        return False
    
    # Vérifier venv
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.warning("⚠️  Virtual environment recommandé")
    
    # Vérifier .env
    if not Path('.env').exists():
        logger.warning("⚠️  Fichier .env manquant - copiez .env.example")
    
    return True

def install_dependencies():
    """Installe les dépendances si nécessaires"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("✅ Dépendances installées")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur installation dépendances: {e}")
        return False

def start_server(host="127.0.0.1", port=8000, reload=True):
    """Démarre le serveur FastAPI"""
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", host, 
            "--port", str(port)
        ]
        
        if reload:
            cmd.append("--reload")
            
        logger.info(f"🚀 Démarrage serveur sur http://{host}:{port}")
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        logger.info("👋 Arrêt du serveur")
    except Exception as e:
        logger.error(f"❌ Erreur démarrage: {e}")

def main():
    """Point d'entrée principal"""
    print("🏠 Budget Famille v2.3 - Démarrage Ubuntu/WSL")
    print("=" * 50)
    
    if not check_environment():
        return 1
    
    # Arguments
    if "--install" in sys.argv:
        if not install_dependencies():
            return 1
    
    # Démarrage
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", 8000))
    reload = "--no-reload" not in sys.argv
    
    start_server(host, port, reload)
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        
        startup_file = self.base_path / "start.py"
        if not self.dry_run:
            with open(startup_file, 'w') as f:
                f.write(startup_content)
            startup_file.chmod(0o755)
        
        self.log_action("create", "start.py", startup_file)

    def save_migration_report(self):
        """Sauvegarde le rapport de migration"""
        report = {
            'migration_date': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'actions': self.migration_log,
            'summary': {
                'total_actions': len(self.migration_log),
                'successful': len([a for a in self.migration_log if a['status'] == 'success']),
                'errors': len([a for a in self.migration_log if a['status'] != 'success'])
            }
        }
        
        report_file = self.base_path / "migration_report.json"
        if not self.dry_run:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
        
        logger.info(f"📊 Rapport sauvegardé: {report_file}")
        return report

    def run_migration(self):
        """Exécute la migration complète"""
        logger.info("🚀 Début de la consolidation d'architecture")
        
        # Étapes de migration
        steps = [
            ("Création backup", self.create_backup),
            ("Organisation fichiers", self.organize_files), 
            ("Organisation backups DB", self.organize_backups),
            ("Création script démarrage", self.create_startup_script),
            ("Sauvegarde rapport", self.save_migration_report)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"📝 Étape: {step_name}")
            try:
                result = step_func()
                if step_name == "Sauvegarde rapport":
                    return result
            except Exception as e:
                logger.error(f"❌ Erreur lors de '{step_name}': {e}")
                return None

def main():
    """Point d'entrée principal"""
    print("\n" + "="*70)
    print("🏠 CONSOLIDATION ARCHITECTURE BUDGET FAMILLE v2.3")
    print("="*70)
    
    # Arguments
    dry_run = '--execute' not in sys.argv
    
    if dry_run:
        print("📋 MODE SIMULATION (ajoutez --execute pour appliquer)")
    else:
        print("🚀 MODE EXÉCUTION")
        confirm = input("\n⚠️  Confirmer la consolidation ? (oui/non): ")
        if confirm.lower() not in ['oui', 'o', 'yes', 'y']:
            print("❌ Migration annulée")
            return 1
    
    try:
        consolidator = ArchitectureConsolidator(dry_run=dry_run)
        report = consolidator.run_migration()
        
        if report:
            print(f"\n✅ Migration terminée!")
            print(f"📊 Actions: {report['summary']['successful']}/{report['summary']['total_actions']}")
            
            if dry_run:
                print("\n💡 Pour appliquer les changements:")
                print("   python migrate_to_consolidated.py --execute")
            else:
                print("\n🎉 Architecture consolidée avec succès!")
                print("📋 Prochaines étapes:")
                print("   1. cp .env.example .env")
                print("   2. python start.py --install")
                print("   3. python start.py")
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())