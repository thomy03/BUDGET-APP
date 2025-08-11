# Budget Famille v2.3 - Application de Gestion Budgétaire

## 📋 Description

Application web sécurisée de gestion de budget familial permettant de :
- Gérer les transactions financières de deux membres
- Calculer automatiquement la répartition des dépenses
- Importer des données via CSV
- Analyser les dépenses par catégories
- Configurer les revenus et modes de partage

## 🏗️ Architecture

### Backend (FastAPI + SQLite)
- **API RESTful** avec authentification JWT
- **Base de données SQLite** pour le stockage des données
- **Sécurisation** : CORS configuré, validation des entrées, hash des mots de passe
- **Endpoints** : Gestion transactions, configuration, import CSV, analytics

### Frontend (Next.js 14 + TypeScript)
- **Interface moderne** avec Tailwind CSS
- **Authentification** : Système de login/logout sécurisé
- **Pages** : Dashboard, Analytics, Settings, Upload
- **Responsive** : Compatible mobile et desktop

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.8+
- Node.js 18+ (ou Docker pour WSL2)
- Docker Desktop (recommandé pour Windows/WSL2)

### Installation Recommandée (Docker)

**Solution optimisée pour Windows/WSL2** avec résolution du problème Next.js :

1. **Backend (WSL2 natif)** :
```bash
cd backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. **Frontend (Docker container)** :
```bash
cd frontend
./dev-docker.sh start
```

3. **Accès** :
- Interface : http://localhost:45678
- API : http://0.0.0.0:8000
- Documentation API : http://0.0.0.0:8000/docs

### Installation Alternative (Windows natif)

1. **Backend** :
```bash
# Utiliser les scripts dans /scripts
scripts/start_backend.bat
```

2. **Frontend** :
```bash
scripts/start_frontend.bat
```

### Identifiants de test
- **Utilisateur** : `admin`
- **Mot de passe** : `secret`

## 📊 Fonctionnalités

### ✅ Implémentées
- 🔐 **Authentification JWT** sécurisée
- 📊 **Dashboard** avec répartition automatique des dépenses
- 📈 **Analytics** par catégories avec graphiques
- ⚙️ **Configuration** des membres et modes de partage  
- 📄 **Import CSV** avec validation et parsing intelligent
- 🎨 **Interface moderne** responsive avec design professionnel

### 🔄 Navigation
- **MonthPicker** : Navigation entre les mois (bug corrigé)
- **Menu principal** : Accès rapide à toutes les sections
- **États de chargement** : Feedback utilisateur en temps réel
- **Post-import CSV** : Navigation automatique vers transactions (corrigé)

## 🧪 Tests

### Tests Utilisateur Validés ✅
- ✅ Authentification/déconnexion sécurisée
- ✅ Import de données CSV avec navigation corrigée
- ✅ Calculs de répartition automatiques
- ✅ Navigation fluide entre pages (bugs MonthPicker corrigés)
- ✅ Interface responsive moderne
- ✅ Performance < 2sec par action
- ✅ Compatibilité WSL2 via solution Docker
- ✅ Tests d'intégration complets (15+ scripts)

### Données de Test
Le fichier `test_data.csv` contient :
- Revenus : Diana (3200€), Thomas (2800€)
- Dépenses : Courses, restaurant, loyer, factures
- Période : Janvier 2024

## 🔒 Sécurité

### Mesures Implémentées
- **JWT** avec expiration automatique
- **CORS** restreint aux domaines autorisés
- **Validation** stricte des entrées utilisateur
- **Hash** des mots de passe avec salt
- **Protection** contre injection SQL/XSS
- **Upload sécurisé** avec validation MIME type

### Note Importante
Cette version utilise un hash SHA256 simple pour les mots de passe (compatible Windows).
Pour la production, utiliser bcrypt complet.

## 📁 Structure du Projet

```
budget-app-starter-v2.3/
├── backend/                 # API FastAPI
│   ├── app_simple.py       # Application principale
│   ├── requirements_*.txt  # Dépendances Python
│   └── start_backend_*.bat # Scripts de démarrage
├── frontend/               # Interface Next.js
│   ├── app/               # Pages (App Router)
│   ├── components/        # Composants réutilisables
│   ├── lib/              # Services et utilitaires
│   └── styles/           # Styles CSS globaux
├── .claude/              # Configuration Claude
├── docs/                 # Documentation
└── scripts/              # Scripts de démarrage
```

## 🎯 Roadmap

### Phase 1 - Foundation (🚀 95% Terminée)
- ✅ Sécurisation complète avec audit
- ✅ Interface fonctionnelle avec corrections majeures
- ✅ Tests utilisateur validés et étendus
- ✅ Solution Docker pour problème WSL2/Next.js
- ✅ Architecture backend consolidée
- ✅ Système de backup automatisé
- 🔄 Documentation finale (en cours)

### Phase 2 - Intelligence (À venir)
- Catégorisation automatique par IA
- Prédictions budgétaires
- Alertes intelligentes

### Phase 3 - Avancé (À venir)
- Multi-devises
- Export PDF/Excel avancé
- API mobile

### Phase 4 - Enterprise (À venir)
- Multi-foyers
- Synchronisation cloud
- Audit complet

## 🛠️ Développement

### Structure de Commit
Les commits suivent la convention :
```
type(scope): description

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

### Environnement de Développement
- **Backend** : FastAPI avec rechargement automatique (WSL2 natif)
- **Frontend** : Next.js avec Hot Reload (Docker container)
- **Database** : SQLite avec migrations automatiques et backup
- **Styling** : Tailwind CSS avec design system
- **Solutions** : Docker pour contourner limitations WSL2
- **Scripts** : Automatisation complète du workflow

## 📞 Support

### Documentation Complète
- `docs/installation/` - Guides d'installation détaillés
- `docs/troubleshooting/` - Solutions problèmes courants
- `docs/reports/` - Rapports de validation et tests
- `frontend/README-DOCKER.md` - Solution Docker WSL2
- `ROADMAP_MASTER_V3.md` - État complet du projet
- `backend/CONSOLIDATION_GUIDE.md` - Guide migration architecture

### Démarrage Alternatif
Si les scripts `.bat` ne fonctionnent pas :
1. Suivre `INSTRUCTIONS_MANUELLES.txt`
2. Ou utiliser `SOLUTION_SANS_VENV.bat`

## ⚖️ Licence

Projet privé - Tous droits réservés
Application développée avec l'assistance de Claude Code (Anthropic)

---

**Version** : v2.3.3-WSL2-DOCKER-SOLUTION  
**Status** : 🚀 Phase 1 - 95% Complete (Prêt pour Phase 2)  
**Dernière mise à jour** : 2025-08-10  
**Breakthrough** : Problème WSL2 + Next.js résolu via Docker