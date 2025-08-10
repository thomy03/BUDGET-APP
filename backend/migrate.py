#!/usr/bin/env python3
"""
Script de migration automatique Budget Famille v2.3
Migre automatiquement vers l'architecture consolidée
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_banner():
    """Banner de migration"""
    print("\n" + "="*60)
    print("🔄 BUDGET FAMILLE v2.3 - MIGRATION AUTOMATIQUE")
    print("="*60)
    print("Migration vers architecture consolidée Ubuntu/WSL")
    print("="*60 + "\n")

def backup_current_setup():
    """Sauvegarde l'installation actuelle"""
    backup_name = f"budget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = Path(f"../{backup_name}")
    
    logger.info("💾 Création sauvegarde sécurisée...")
    
    try:
        shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        logger.info(f"✅ Sauvegarde créée: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"❌ Erreur création sauvegarde: {e}")
        return None

def check_prerequisites():
    """Vérifie les prérequis système"""
    logger.info("🔍 Vérification des prérequis...")
    
    # Vérifier Python version
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8+ requis")
        return False
    
    # Vérifier OS Ubuntu/WSL
    try:
        with open('/etc/os-release', 'r') as f:
            content = f.read().lower()
            if 'ubuntu' not in content and 'wsl' not in content:
                logger.warning("⚠️  OS non-Ubuntu détecté - continuez à vos risques")
    except FileNotFoundError:
        logger.warning("⚠️  Impossible de détecter l'OS")
    
    logger.info("✅ Prérequis vérifiés")
    return True

def install_system_dependencies():
    """Installe les dépendances système"""
    logger.info("📦 Installation dépendances système Ubuntu...")
    
    try:
        # Mettre à jour les paquets
        subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)
        
        # Installer les dépendances
        deps = ['libmagic1', 'libmagic-dev', 'python3-dev', 'build-essential']
        cmd = ['sudo', 'apt', 'install', '-y'] + deps
        subprocess.run(cmd, check=True)
        
        logger.info("✅ Dépendances système installées")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur installation dépendances: {e}")
        return False
    except FileNotFoundError:
        logger.warning("⚠️  apt non trouvé - ignorez si pas sur Ubuntu")
        return True

def migrate_configuration():
    """Migre la configuration"""
    logger.info("⚙️  Migration configuration...")
    
    # Créer .env s'il n'existe pas
    if not Path('.env').exists():
        if Path('.env.example').exists():
            shutil.copy('.env.example', '.env')
            logger.info("✅ Configuration .env créée")
        else:
            logger.warning("⚠️  .env.example introuvable")
    
    return True

def install_python_dependencies():
    """Installe les dépendances Python"""
    logger.info("🐍 Installation dépendances Python...")
    
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("✅ Dépendances Python installées")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur installation dépendances Python: {e}")
        return False

def test_migration():
    """Test la migration"""
    logger.info("🧪 Test de la migration...")
    
    try:
        # Test d'import
        sys.path.insert(0, '.')
        import app
        logger.info("✅ Application importable")
        
        # Test health endpoint
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        response = client.get("/health")
        if response.status_code == 200:
            logger.info("✅ Health endpoint fonctionnel")
        else:
            logger.warning("⚠️  Health endpoint non accessible")
        
        return True
    except Exception as e:
        logger.error(f"❌ Test migration échoué: {e}")
        return False

def cleanup_old_files():
    """Nettoie les anciens fichiers si demandé"""
    old_files = [
        'app_simple.py', 'app_windows.py', 'app_windows_optimized.py', 'app_minimal_csv.py',
        'start_complete.py', 'start_degraded.py', 'start_secure.py', 'start_windows.py'
    ]
    
    # Chercher requirements anciens
    old_files.extend(Path('.').glob('requirements_*.txt'))
    
    existing_old_files = [f for f in old_files if Path(f).exists()]
    
    if not existing_old_files:
        logger.info("✅ Aucun ancien fichier à nettoyer")
        return True
    
    logger.info(f"🧹 {len(existing_old_files)} anciens fichiers trouvés")
    
    cleanup = input("🗑️  Supprimer les anciens fichiers ? (o/N): ")
    if cleanup.lower() in ['o', 'oui', 'y', 'yes']:
        for file in existing_old_files:
            try:
                Path(file).unlink()
                logger.info(f"🗑️  Supprimé: {file}")
            except Exception as e:
                logger.warning(f"⚠️  Impossible de supprimer {file}: {e}")
    
    return True

def show_post_migration_info():
    """Affiche les informations post-migration"""
    print("\n" + "="*60)
    print("🎉 MIGRATION TERMINÉE AVEC SUCCÈS!")
    print("="*60)
    print()
    print("📋 PROCHAINES ÉTAPES:")
    print("1. Personnalisez .env selon vos besoins")
    print("2. Lancez: python3 start.py")
    print("3. Accédez à: http://127.0.0.1:8000/docs")
    print()
    print("🔗 LIENS UTILES:")
    print("- API Health: http://127.0.0.1:8000/health")
    print("- Documentation: http://127.0.0.1:8000/docs")
    print("- Guide: CONSOLIDATION_MIGRATION_GUIDE.md")
    print()
    print("🆘 EN CAS DE PROBLÈME:")
    print("- Consultez les logs ci-dessus")
    print("- Vérifiez CONSOLIDATION_MIGRATION_GUIDE.md")
    print("- Restaurez depuis la sauvegarde si nécessaire")
    print("="*60 + "\n")

def main():
    """Point d'entrée principal"""
    print_banner()
    
    # Vérification prérequis
    if not check_prerequisites():
        logger.error("❌ Prérequis non satisfaits")
        return 1
    
    # Création sauvegarde
    backup_path = backup_current_setup()
    if not backup_path:
        return 1
    
    # Confirmation utilisateur
    print("⚠️  ATTENTION: Cette migration va modifier votre installation.")
    print(f"📁 Sauvegarde créée dans: {backup_path}")
    confirm = input("\n🔄 Continuer la migration ? (o/N): ")
    if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
        logger.info("❌ Migration annulée par l'utilisateur")
        return 0
    
    # Étapes de migration
    steps = [
        ("Installation dépendances système", install_system_dependencies),
        ("Migration configuration", migrate_configuration),
        ("Installation dépendances Python", install_python_dependencies),
        ("Test migration", test_migration),
        ("Nettoyage fichiers obsolètes", cleanup_old_files)
    ]
    
    for step_name, step_func in steps:
        logger.info(f"🔄 {step_name}...")
        if not step_func():
            logger.error(f"❌ Échec: {step_name}")
            print(f"\n💡 Restaurez depuis: {backup_path}")
            return 1
    
    show_post_migration_info()
    return 0

if __name__ == "__main__":
    sys.exit(main())