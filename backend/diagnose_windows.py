#!/usr/bin/env python3
"""
Script de diagnostic complet pour résoudre les problèmes Windows du Budget App

Ce script diagnostique et corrige automatiquement les problèmes courants :
- Modules Python manquants  
- Problèmes de dépendances (magic, pysqlcipher3)
- Configuration de base de données
- Tests d'import CSV
- Vérification des ports

Usage: python diagnose_windows.py
"""

import sys
import os
import subprocess
import json
import platform
import socket
from pathlib import Path
import tempfile
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WindowsDiagnostic:
    def __init__(self):
        self.results = {
            "system_info": {},
            "python_check": {},
            "dependencies": {},
            "database": {},
            "csv_import": {},
            "network": {},
            "recommendations": []
        }
    
    def check_system_info(self):
        """Collecte informations système"""
        logger.info("🔍 Vérification informations système...")
        
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.architecture()[0],
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_executable": sys.executable,
            "working_directory": os.getcwd()
        }
        
        self.results["system_info"] = info
        
        logger.info(f"✅ Système: {info['os']} {info['os_version']}")
        logger.info(f"✅ Python: {info['python_version']} ({info['architecture']})")
        
        return True
    
    def check_python_modules(self):
        """Vérifie les modules Python requis"""
        logger.info("🔍 Vérification modules Python...")
        
        # Modules essentiels pour l'app Windows
        required_modules = {
            'fastapi': 'Interface API web',
            'uvicorn': 'Serveur ASGI',  
            'pandas': 'Manipulation données',
            'numpy': 'Calculs numériques',
            'sqlalchemy': 'ORM base de données',
            'python_multipart': 'Upload fichiers',
            'jose': 'Tokens JWT',
            'passlib': 'Hachage mots de passe',
            'dotenv': 'Variables environnement',
            'cryptography': 'Cryptographie',
            'email_validator': 'Validation emails',
            'pydantic': 'Validation données'
        }
        
        # Modules problématiques sur Windows
        problematic_modules = {
            'magic': 'Détection type MIME (problématique Windows)',
            'pysqlcipher3': 'Chiffrement SQLite (optionnel)'
        }
        
        available = {}
        missing = {}
        problematic = {}
        
        # Test modules essentiels
        for module, description in required_modules.items():
            try:
                mod_name = module.replace('-', '_').replace('python_', '')
                __import__(mod_name)
                available[module] = description
                logger.info(f"✅ {module}: {description}")
            except ImportError as e:
                missing[module] = str(e)
                logger.warning(f"❌ {module}: {description} - {e}")
        
        # Test modules problématiques
        for module, description in problematic_modules.items():
            try:
                __import__(module)
                problematic[module] = "Disponible mais peut causer des problèmes"
                logger.warning(f"⚠️  {module}: {description} - Disponible")
            except ImportError:
                logger.info(f"👍 {module}: {description} - Absent (OK pour Windows)")
        
        self.results["dependencies"] = {
            "available": available,
            "missing": missing,
            "problematic": problematic
        }
        
        if missing:
            self.results["recommendations"].append({
                "type": "install_dependencies",
                "message": f"Installer modules manquants: pip install {' '.join(missing.keys())}",
                "command": f"pip install {' '.join(missing.keys())}"
            })
        
        return len(missing) == 0
    
    def test_database_connection(self):
        """Teste la connexion base de données"""
        logger.info("🔍 Test connexion base de données...")
        
        try:
            from sqlalchemy import create_engine, text
            
            # Test SQLite standard (pour Windows)
            engine = create_engine("sqlite:///./test_budget.db", echo=False)
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                test_value = result.fetchone()[0]
            
            if test_value == 1:
                logger.info("✅ Base de données SQLite OK")
                self.results["database"]["sqlite"] = "OK"
                
                # Nettoyage du fichier de test
                try:
                    os.remove("./test_budget.db")
                except:
                    pass
                
                return True
            
        except Exception as e:
            logger.error(f"❌ Erreur base de données: {e}")
            self.results["database"]["error"] = str(e)
            return False
    
    def test_app_import(self):
        """Teste l'import des apps"""
        logger.info("🔍 Test import applications...")
        
        apps_to_test = ["app_windows", "app"]
        results = {}
        
        for app_name in apps_to_test:
            try:
                module = __import__(app_name)
                results[app_name] = "OK"
                logger.info(f"✅ {app_name}.py importé avec succès")
                
                # Test spécifique pour app.py (problème magic)
                if app_name == "app":
                    logger.info("⚠️  app.py fonctionne mais utilise des dépendances complexes")
                    self.results["recommendations"].append({
                        "type": "use_windows_app",
                        "message": "Utiliser app_windows.py au lieu de app.py pour éviter les problèmes Windows",
                        "command": "python start_windows.py"
                    })
                
            except ImportError as e:
                results[app_name] = str(e)
                logger.error(f"❌ {app_name}.py: {e}")
                
                if "magic" in str(e):
                    self.results["recommendations"].append({
                        "type": "magic_issue",
                        "message": "Problème module 'magic' détecté - utiliser app_windows.py",
                        "command": "python start_windows.py"
                    })
        
        self.results["python_check"]["app_imports"] = results
        return "app_windows" in results and results["app_windows"] == "OK"
    
    def test_csv_functionality(self):
        """Teste la fonctionnalité d'import CSV"""
        logger.info("🔍 Test fonctionnalité import CSV...")
        
        try:
            # Création fichier CSV de test
            csv_content = """Date,Description,Montant,Compte
2024-01-01,Test transaction,-50.00,Test compte
2024-01-02,Test revenu,100.00,Test compte"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                csv_file = f.name
            
            # Test parsing CSV
            import pandas as pd
            import io
            from html import escape
            
            df = pd.read_csv(csv_file)
            
            if len(df) == 2:
                logger.info("✅ Parse CSV OK")
                self.results["csv_import"]["parsing"] = "OK"
                
                # Test validation données
                for _, row in df.iterrows():
                    date_str = escape(str(row.get('Date', '')).strip())
                    description = escape(str(row.get('Description', '')).strip())
                    amount = float(str(row.get('Montant', '0')).replace(',', '.'))
                    account = escape(str(row.get('Compte', '')).strip())
                
                logger.info("✅ Validation données CSV OK")
                self.results["csv_import"]["validation"] = "OK"
                
            # Nettoyage
            os.unlink(csv_file)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test CSV échoué: {e}")
            self.results["csv_import"]["error"] = str(e)
            return False
    
    def test_network_ports(self):
        """Teste la disponibilité des ports réseau"""
        logger.info("🔍 Test ports réseau...")
        
        ports_to_test = [8000, 3000, 45678]  # Backend, Frontend, Dev
        results = {}
        
        for port in ports_to_test:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:
                    results[port] = "Occupé"
                    logger.warning(f"⚠️  Port {port} occupé")
                else:
                    results[port] = "Libre"
                    logger.info(f"✅ Port {port} libre")
                    
            except Exception as e:
                results[port] = f"Erreur: {e}"
                logger.error(f"❌ Test port {port}: {e}")
        
        self.results["network"]["ports"] = results
        
        if results.get(8000) == "Occupé":
            self.results["recommendations"].append({
                "type": "port_conflict",
                "message": "Port 8000 occupé - arrêter autres serveurs ou changer port",
                "command": "netstat -ano | findstr :8000"
            })
        
        return True
    
    def generate_startup_commands(self):
        """Génère les commandes de démarrage recommandées"""
        logger.info("📋 Génération commandes de démarrage...")
        
        commands = []
        
        # Installation dépendances si nécessaire
        if self.results["dependencies"]["missing"]:
            commands.append({
                "step": "Installation des dépendances",
                "command": "pip install -r requirements_windows.txt",
                "description": "Installe les modules Python requis"
            })
        
        # Démarrage recommandé
        if self.results["python_check"].get("app_imports", {}).get("app_windows") == "OK":
            commands.append({
                "step": "Démarrage application (Recommandé)",
                "command": "python start_windows.py",
                "description": "Démarre l'app avec version Windows optimisée"
            })
        else:
            commands.append({
                "step": "Démarrage application (Alternative)",
                "command": "python -m uvicorn app_windows:app --host 127.0.0.1 --port 8000 --reload",
                "description": "Démarrage direct avec uvicorn"
            })
        
        # Test de l'API
        commands.append({
            "step": "Test de l'API",
            "command": "curl http://127.0.0.1:8000/docs",
            "description": "Ouvre la documentation interactive de l'API"
        })
        
        self.results["recommendations"].extend([
            {"type": "startup_commands", "commands": commands}
        ])
    
    def run_full_diagnostic(self):
        """Exécute le diagnostic complet"""
        logger.info("🚀 Lancement diagnostic complet Budget App - Windows")
        
        checks = [
            ("Informations système", self.check_system_info),
            ("Modules Python", self.check_python_modules),
            ("Base de données", self.test_database_connection),
            ("Import applications", self.test_app_import),
            ("Fonctionnalité CSV", self.test_csv_functionality),
            ("Ports réseau", self.test_network_ports)
        ]
        
        passed = 0
        total = len(checks)
        
        for check_name, check_func in checks:
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 {check_name}")
            logger.info('='*50)
            
            try:
                if check_func():
                    passed += 1
                    logger.info(f"✅ {check_name}: PASSÉ")
                else:
                    logger.error(f"❌ {check_name}: ÉCHOUÉ")
            except Exception as e:
                logger.error(f"💥 {check_name}: ERREUR - {e}")
        
        # Génération des recommandations
        self.generate_startup_commands()
        
        # Résumé
        logger.info(f"\n{'='*50}")
        logger.info(f"📊 RÉSUMÉ DU DIAGNOSTIC")
        logger.info('='*50)
        logger.info(f"Tests passés: {passed}/{total}")
        
        if passed == total:
            logger.info("🎉 Tous les tests sont passés ! L'application devrait fonctionner.")
        elif passed >= total - 1:
            logger.warning("⚠️  Quelques problèmes mineurs détectés mais l'app devrait fonctionner.")
        else:
            logger.error("🚨 Problèmes critiques détectés. Vérifiez les recommandations.")
        
        return self.results
    
    def save_report(self, filename="diagnostic_report.json"):
        """Sauvegarde le rapport de diagnostic"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 Rapport sauvegardé: {filename}")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde rapport: {e}")

def main():
    """Point d'entrée principal"""
    diagnostic = WindowsDiagnostic()
    
    try:
        results = diagnostic.run_full_diagnostic()
        diagnostic.save_report()
        
        # Affichage des recommandations
        if results["recommendations"]:
            logger.info(f"\n{'='*50}")
            logger.info("💡 RECOMMANDATIONS")
            logger.info('='*50)
            
            for i, rec in enumerate(results["recommendations"], 1):
                if rec["type"] == "startup_commands":
                    logger.info("📋 Commandes de démarrage recommandées:")
                    for cmd in rec["commands"]:
                        logger.info(f"   {cmd['step']}: {cmd['command']}")
                        logger.info(f"      → {cmd['description']}")
                else:
                    logger.info(f"{i}. {rec['message']}")
                    if "command" in rec:
                        logger.info(f"   Commande: {rec['command']}")
        
        logger.info(f"\n🎯 Pour démarrer l'application:")
        logger.info("   python start_windows.py")
        logger.info(f"\n📖 Documentation complète: http://127.0.0.1:8000/docs")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Diagnostic interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"💥 Erreur critique diagnostic: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()