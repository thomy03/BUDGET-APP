# 🚀 Guide d'Installation Complet - Budget Famille v2.3

## 📋 Vue d'ensemble

Ce guide présente toutes les méthodes d'installation pour Budget Famille v2.3, avec une **solution recommandée Docker** pour résoudre les problèmes de compatibilité WSL2/Next.js.

## 🎯 Solutions d'Installation

### 🏆 SOLUTION RECOMMANDÉE : Docker (Windows/WSL2)

**Avantages** :
- ✅ Résout le problème WSL2 + Next.js 14
- ✅ Performance optimale (démarrage en 2 secondes)
- ✅ Environnement reproductible
- ✅ Hot-reload fonctionnel
- ✅ Isolation complète des dépendances

#### Prérequis Docker
- Docker Desktop installé et fonctionnel
- WSL2 configuré (recommandé)
- 4GB RAM minimum pour les containers

#### Installation Docker

**1. Backend (WSL2 natif - Performance optimale)**
```bash
cd backend

# Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Démarrer le serveur
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**2. Frontend (Docker container - Contourne le problème WSL2)**
```bash
cd frontend

# Rendre le script exécutable
chmod +x dev-docker.sh

# Démarrer le container (build automatique)
./dev-docker.sh start
```

**3. Vérification**
- Backend : http://0.0.0.0:8000
- Frontend : http://localhost:45678
- API Docs : http://0.0.0.0:8000/docs

#### Gestion quotidienne Docker
```bash
# Démarrer
./dev-docker.sh start

# Arrêter
./dev-docker.sh stop

# Redémarrer
./dev-docker.sh restart

# Voir les logs
./dev-docker.sh logs

# Accéder au container
./dev-docker.sh shell

# Rebuild complet
./dev-docker.sh rebuild
```

### 📋 Solution Alternative : Windows Natif

**Pour utilisateurs sans Docker ou préférant l'installation native.**

#### Prérequis Windows
- Python 3.8+ installé
- Node.js 18+ installé
- Git Bash (recommandé)

#### Installation Windows

**1. Backend**
```bash
cd backend

# Créer environnement virtuel
python -m venv .venv

# Activer (PowerShell)
.venv\Scripts\Activate.ps1

# Ou activer (CMD)
.venv\Scripts\activate.bat

# Installer dépendances
pip install -r requirements.txt

# Démarrer
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

**2. Frontend**
```bash
cd frontend

# Installer dépendances
npm install

# Démarrer (peut être lent en WSL2)
npm run dev
```

**3. Scripts automatisés**
```bash
# Utiliser les scripts dans /scripts
scripts/start_backend.bat
scripts/start_frontend.bat
```

### 🔧 Solution Linux/Mac Native

**Pour environnements Unix purs.**

#### Installation Unix

**1. Backend**
```bash
cd backend

# Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Dépendances
pip install -r requirements.txt

# Démarrer
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**2. Frontend**
```bash
cd frontend

# Dépendances
npm install

# Démarrage
npm run dev
```

## 🐛 Résolution de Problèmes

### Problème WSL2 + Next.js

**Symptômes** :
- Next.js se bloque au "Starting..."
- Erreurs SIGBUS lors du build
- Performance très dégradée

**Solution** : Utiliser la méthode Docker recommandée ci-dessus.

### Erreurs de Dépendances Python

**Windows - Erreur bcrypt** :
```bash
# Installer Visual Studio Build Tools
# Ou utiliser la version simplifiée
pip install -r requirements.txt --no-deps
```

**Linux - Erreurs de compilation** :
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev build-essential

# CentOS/RHEL
sudo yum install python3-devel gcc
```

### Problèmes de Port

**Port 8000 occupé** :
```bash
# Trouver le processus
netstat -ano | findstr :8000
# Windows : taskkill /PID <PID> /F
# Linux : kill -9 <PID>

# Ou utiliser un autre port
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

**Port 45678 occupé** :
```bash
# Modifier le port dans frontend/package.json
# Ou modifier docker-compose.yml si utilisation Docker
```

### Erreurs d'Authentification

**Token JWT invalide** :
```bash
# Supprimer les tokens existants
rm backend/budget.db
python backend/start.py  # Recrée la DB
```

### Performance Lente

**WSL2 lent** :
- Solution Docker recommandée
- Ou installer Windows natif

**Build Node.js lent** :
```bash
# Nettoyer le cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

## ⚙️ Configuration Avancée

### Variables d'Environnement

**Backend (.env)** :
```
DATABASE_URL=sqlite:///./budget.db
SECRET_KEY=your-secret-key
CORS_ORIGINS=["http://localhost:45678"]
DEBUG=true
```

**Frontend (.env.local)** :
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
NODE_ENV=development
```

### Configuration Docker

**Docker Compose (optionnel)** :
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    
  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "45678:45678"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### Base de Données

**Initialisation** :
```bash
cd backend
python start.py  # Crée la DB et utilisateur admin
```

**Backup** :
```bash
# Backup automatique (système inclus)
python organize_db_backups.py

# Backup manuel
cp budget.db budget.db.backup.$(date +%Y%m%d_%H%M%S)
```

## 🧪 Validation de l'Installation

### Tests de Base

**1. Backend**
```bash
curl http://localhost:8000/health
# Réponse attendue : {"status": "healthy"}
```

**2. Frontend**
```bash
curl http://localhost:45678
# Doit retourner du HTML Next.js
```

**3. Authentification**
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"
# Doit retourner un token JWT
```

### Tests Fonctionnels

**Utiliser les données de test** :
1. Se connecter avec `admin`/`secret`
2. Importer `tests/csv-samples/01_happy_path_janvier_2024.csv`
3. Vérifier la navigation et les calculs

### Tests de Performance

```bash
# Backend
time curl http://localhost:8000/transactions?month=2024-01
# Doit être < 1 seconde

# Frontend
# Ouvrir DevTools Network, recharger la page
# Time to Interactive doit être < 3 secondes
```

## 📞 Support

### Logs Utiles

**Backend** :
```bash
# Logs en temps réel
tail -f backend/app.log
```

**Frontend Docker** :
```bash
# Logs container
./dev-docker.sh logs

# Logs en temps réel
docker logs -f budget-frontend
```

### Diagnostic Automatique

```bash
# Script de diagnostic inclus
python backend/diagnostic_windows.py
```

### Contacts Support

- **Documentation** : `/docs` dans le projet
- **Issues** : Logs + étapes de reproduction
- **Guides spécialisés** : 
  - `docs/troubleshooting/` - Résolution problèmes
  - `backend/GUIDE_DEMARRAGE_WINDOWS.md` - Spécifique Windows
  - `frontend/README-DOCKER.md` - Solution Docker détaillée

---

**Version du guide** : v2.3.3  
**Dernière mise à jour** : 2025-08-10  
**Solutions testées** : Windows 11 WSL2, Ubuntu 20.04, Docker Desktop