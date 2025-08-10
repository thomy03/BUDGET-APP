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
- Node.js 18+

### Installation Windows

1. **Backend** :
```bash
# Double-cliquer sur le fichier :
start_backend_simple.bat
```

2. **Frontend** :
```bash  
# Double-cliquer sur le fichier :
start_frontend_direct.bat
```

3. **Accès** :
- Interface : http://localhost:45678
- API : http://127.0.0.1:8000
- Documentation API : http://127.0.0.1:8000/docs

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
- **MonthPicker** : Navigation entre les mois
- **Menu principal** : Accès rapide à toutes les sections
- **États de chargement** : Feedback utilisateur en temps réel

## 🧪 Tests

### Tests Utilisateur Validés ✅
- ✅ Authentification/déconnexion
- ✅ Import de données CSV (`test_data.csv` inclus)
- ✅ Calculs de répartition automatiques
- ✅ Navigation fluide entre pages
- ✅ Interface responsive
- ✅ Performance < 2sec par action

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

### Phase 1 - Foundation (✅ Terminée)
- Sécurisation complète
- Interface fonctionnelle
- Tests utilisateur validés

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
- **Backend** : FastAPI avec rechargement automatique
- **Frontend** : Next.js avec Hot Reload
- **Database** : SQLite avec migrations automatiques
- **Styling** : Tailwind CSS avec design system

## 📞 Support

### Fichiers d'Aide Inclus
- `GUIDE_TEST_UTILISATEUR.md` - Guide de test complet
- `INSTRUCTIONS_FINALES.md` - Instructions de démarrage
- `CORRECTIONS_TERMINEES.md` - Historique des corrections
- `SOLUTION_ESPACES.md` - Résolution problèmes Windows

### Démarrage Alternatif
Si les scripts `.bat` ne fonctionnent pas :
1. Suivre `INSTRUCTIONS_MANUELLES.txt`
2. Ou utiliser `SOLUTION_SANS_VENV.bat`

## ⚖️ Licence

Projet privé - Tous droits réservés
Application développée avec l'assistance de Claude Code (Anthropic)

---

**Version** : v2.3.2-IMPORT-ENHANCED  
**Status** : 🔄 Development (Import CSV Navigation)  
**Dernière mise à jour** : 2025-08-10