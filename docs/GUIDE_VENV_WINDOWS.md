# 🐍 Guide Environnement Virtuel .venv - Budget Famille v2.3

## 🎯 Solution Recommandée DevOps

Cette solution respecte les bonnes pratiques DevOps avec un environnement virtuel Python isolé à la racine du projet.

## 📋 Prérequis

- **Python 3.11+** installé avec "Add to PATH" activé
- **Node.js 18+** pour le frontend
- **PowerShell** avec droits d'exécution de scripts

## 🚀 Installation Rapide

### 1. Création de l'environnement virtuel

```powershell
# Exécuter ce script une seule fois
.\SETUP_VENV_WINDOWS.ps1
```

### 2. Démarrage de l'application

```powershell
# Exécuter à chaque session de travail
.\START_WITH_VENV.ps1
```

## 🔧 Commandes Manuelles

### Activation de l'environnement virtuel

```powershell
# À faire dans chaque nouvelle session PowerShell
.\.venv\Scripts\Activate.ps1
```

### Démarrage Backend (Option A - depuis la racine)

```powershell
# Depuis la racine du projet, avec .venv activé
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Démarrage Backend (Option B - depuis backend/)

```powershell
# Se placer dans le dossier backend
cd backend
uvicorn app.main:app --reload --port 8000
```

### Démarrage Frontend

```powershell
cd frontend
npm ci                    # Installation dépendances (une fois)
npm run dev              # Démarrage serveur de développement
```

## 🌐 URLs d'Accès

- **Frontend**: http://localhost:3000
- **Backend API**: http://127.0.0.1:8000
- **Documentation API**: http://127.0.0.1:8000/docs

## 🔑 Identifiants de Test

- **Utilisateur**: `admin`
- **Mot de passe**: `secret`

## 📦 Gestion des Packages

### Installation de nouveaux packages

```powershell
# Toujours utiliser python -m pip dans l'environnement virtuel
python -m pip install <nom_package>

# Mettre à jour le fichier requirements.txt
python -m pip freeze > backend\requirements.txt
```

### Mise à jour des dépendances

```powershell
# Mise à jour de pip
python -m pip install --upgrade pip

# Réinstallation des dépendances
python -m pip install -r backend\requirements.txt --upgrade
```

## 🔍 Diagnostic et Dépannage

### Vérifier l'environnement virtuel

```powershell
# Vérifier que Python pointe vers .venv
Get-Command python
# Doit afficher un chemin contenant ".venv\Scripts\python.exe"

# Vérifier la version Python
python -V

# Tester les imports critiques
python -c "import fastapi, uvicorn, pandas; print('OK')"
```

### Problèmes courants

#### Erreur "n'est pas reconnu comme commande"

```powershell
# Solution: Autoriser l'exécution de scripts
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

#### Erreur "ModuleNotFoundError"

```powershell
# Solution: Réinstaller les dépendances
python -m pip install -r backend\requirements.txt
```

#### Python ne pointe pas vers .venv

```powershell
# Solution: Réactiver l'environnement virtuel
.\.venv\Scripts\Activate.ps1
```

## 🏗️ Structure du Projet

```
budget-app-starter-v2.3/
├── .venv/                    # Environnement virtuel Python (créé par setup)
├── backend/
│   ├── requirements.txt      # Dépendances Python
│   ├── app.py               # Application FastAPI
│   └── ...
├── frontend/
│   ├── package.json         # Dépendances Node.js
│   └── ...
├── SETUP_VENV_WINDOWS.ps1   # Script de création .venv
├── START_WITH_VENV.ps1      # Script de démarrage avec .venv
└── GUIDE_VENV_WINDOWS.md    # Ce guide
```

## ✅ Avantages de cette Solution

- **🔒 Isolation**: Environnement Python séparé pour chaque projet
- **🔄 Reproductibilité**: Mêmes versions sur tous les environnements
- **🧹 Propreté**: Pas de pollution de l'installation Python système
- **📋 Conformité DevOps**: Respect des bonnes pratiques
- **🐛 Facilité de debug**: Environnement maîtrisé et contrôlé

## 🚨 Notes Importantes

- **Activation obligatoire**: L'environnement virtuel doit être activé à chaque nouvelle session PowerShell
- **Racine du projet**: Le .venv est créé à la racine, pas dans backend/
- **Ne pas commiter**: Le dossier .venv ne doit pas être ajouté à Git (déjà dans .gitignore)
- **Scripts PowerShell**: Utilisez les scripts fournis pour éviter les erreurs manuelles

## 🎯 Workflow Quotidien

1. **Ouvrir PowerShell** dans la racine du projet
2. **Activer .venv**: `.\.venv\Scripts\Activate.ps1`
3. **Démarrer l'application**: `.\START_WITH_VENV.ps1`
4. **Développer** et tester
5. **Commiter** les changements (sans .venv)

Cette solution garantit un environnement de développement robuste et conforme aux standards DevOps.