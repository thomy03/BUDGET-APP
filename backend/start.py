#!/usr/bin/env python3
"""
Script de démarrage unifié Budget Famille v2.3 - Ubuntu/WSL
Version consolidée pour remplacer tous les scripts redondants
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_banner():
    """Affiche le banner de démarrage"""
    print("\n" + "="*60)
    print("🏠 BUDGET FAMILLE v2.3 - BACKEND CONSOLIDÉ")
    print("="*60)
    print("🐧 Environment: Ubuntu/WSL")
    print("🐍 Python:", sys.version.split()[0])
    print("📁 Working Directory:", os.getcwd())
    print("="*60)

def check_environment():
    """Vérifie l'environnement avant démarrage"""
    logger.info("🔍 Vérification de l'environnement...")
    
    # Vérifier Python version
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8+ requis (actuel: %s)", sys.version.split()[0])
        return False
    
    logger.info("✅ Python version: %s", sys.version.split()[0])
    
    # Vérifier virtual environment
    in_venv = (hasattr(sys, 'real_prefix') or 
               (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
    
    if not in_venv:
        logger.warning("⚠️  Virtual environment non détecté - recommandé pour isolation")
    else:
        logger.info("✅ Virtual environment actif")
    
    # Vérifier fichiers critiques
    critical_files = ['app.py', 'requirements.txt']
    for file in critical_files:
        if not Path(file).exists():
            logger.error("❌ Fichier critique manquant: %s", file)
            return False
    
    logger.info("✅ Fichiers critiques présents")
    
    # Vérifier .env
    if not Path('.env').exists():
        if Path('.env.example').exists():
            logger.warning("⚠️  Fichier .env manquant - copiez .env.example vers .env")
            logger.info("💡 Commande: cp .env.example .env")
        else:
            logger.warning("⚠️  Configuration .env non trouvée")
    else:
        logger.info("✅ Configuration .env présente")
    
    return True

def check_dependencies():
    """Vérifie les dépendances Python"""
    logger.info("📦 Vérification des dépendances...")
    
    try:
        import fastapi
        import uvicorn
        import pandas
        import numpy
        import sqlalchemy
        logger.info("✅ Dépendances principales disponibles")
        return True
    except ImportError as e:
        logger.error("❌ Dépendances manquantes: %s", e)
        return False

def install_dependencies():
    """Installe les dépendances si nécessaires"""
    logger.info("🔧 Installation des dépendances...")
    
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("✅ Dépendances installées avec succès")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("❌ Erreur installation dépendances:")
        logger.error("STDOUT: %s", e.stdout)
        logger.error("STDERR: %s", e.stderr)
        return False

def test_app():
    """Test rapide de l'application"""
    logger.info("🧪 Test de l'application...")
    
    try:
        # Test d'import de l'app
        sys.path.insert(0, '.')
        import app
        logger.info("✅ Application importée avec succès")
        return True
    except Exception as e:
        logger.error("❌ Erreur test application: %s", e)
        return False

def start_server(host="127.0.0.1", port=8000, reload=True, log_level="info"):
    """Démarre le serveur FastAPI"""
    logger.info("🚀 Démarrage du serveur FastAPI...")
    
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", host, 
            "--port", str(port),
            "--log-level", log_level
        ]
        
        if reload:
            cmd.append("--reload")
        
        logger.info("🌐 Serveur disponible sur: http://%s:%s", host, port)
        logger.info("📋 Health check: http://%s:%s/health", host, port)
        logger.info("📖 Documentation API: http://%s:%s/docs", host, port)
        logger.info("⏹️  Ctrl+C pour arrêter le serveur")
        
        print("\n" + "="*60)
        print("🎉 SERVEUR DÉMARRÉ AVEC SUCCÈS!")
        print("="*60)
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n")
        logger.info("👋 Arrêt du serveur demandé par l'utilisateur")
    except FileNotFoundError:
        logger.error("❌ uvicorn non trouvé - installez avec: pip install uvicorn")
        return False
    except Exception as e:
        logger.error("❌ Erreur démarrage serveur: %s", e)
        return False
    
    return True

def show_help():
    """Affiche l'aide"""
    print("""
🏠 Budget Famille v2.3 - Script de Démarrage Unifié

UTILISATION:
    python3 start.py [OPTIONS]

OPTIONS:
    --help, -h          Affiche cette aide
    --install           Force l'installation des dépendances
    --check             Vérifie seulement l'environnement (sans démarrer)
    --test              Test l'application (sans démarrer le serveur)
    --host HOST         Host du serveur (défaut: 127.0.0.1)
    --port PORT         Port du serveur (défaut: 8000)
    --no-reload         Désactive le rechargement automatique
    --log-level LEVEL   Niveau de log uvicorn (debug, info, warning, error)

VARIABLES D'ENVIRONNEMENT:
    SERVER_HOST         Host par défaut (défaut: 127.0.0.1)
    SERVER_PORT         Port par défaut (défaut: 8000)
    LOG_LEVEL           Niveau de log (défaut: info)

EXEMPLES:
    python3 start.py                    # Démarrage standard
    python3 start.py --install          # Installe les deps et démarre
    python3 start.py --check            # Vérifie l'environnement
    python3 start.py --port 8080        # Démarre sur le port 8080
    python3 start.py --no-reload        # Production (sans reload)
    
PREMIÈRE UTILISATION:
    1. cp .env.example .env
    2. python3 start.py --install
    3. Configurer .env selon vos besoins
    """)

def main():
    """Point d'entrée principal"""
    # Parse arguments simples
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        show_help()
        return 0
    
    print_banner()
    
    # Mode check uniquement
    if '--check' in args:
        success = check_environment() and check_dependencies()
        return 0 if success else 1
    
    # Mode test uniquement
    if '--test' in args:
        success = check_environment() and check_dependencies() and test_app()
        return 0 if success else 1
    
    # Vérification environnement
    if not check_environment():
        logger.error("❌ Problème d'environnement - arrêt")
        return 1
    
    # Installation forcée
    if '--install' in args:
        if not install_dependencies():
            logger.error("❌ Échec installation - arrêt")
            return 1
    
    # Vérification dépendances
    if not check_dependencies():
        logger.warning("⚠️  Dépendances manquantes")
        install = input("📦 Installer les dépendances ? (o/N): ")
        if install.lower() in ['o', 'oui', 'y', 'yes']:
            if not install_dependencies():
                return 1
        else:
            logger.error("❌ Dépendances requises pour démarrer")
            return 1
    
    # Test application
    if not test_app():
        logger.error("❌ Test application échoué - vérifiez la configuration")
        return 1
    
    # Configuration serveur
    host = next((args[args.index('--host')+1] for arg in args if '--host' in args), 
                os.getenv('SERVER_HOST', '127.0.0.1'))
    port = int(next((args[args.index('--port')+1] for arg in args if '--port' in args),
                    os.getenv('SERVER_PORT', 8000)))
    reload = '--no-reload' not in args
    log_level = next((args[args.index('--log-level')+1] for arg in args if '--log-level' in args),
                     os.getenv('LOG_LEVEL', 'info').lower())
    
    # Démarrage serveur
    success = start_server(host, port, reload, log_level)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())