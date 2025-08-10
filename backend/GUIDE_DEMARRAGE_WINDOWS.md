# Guide de Démarrage Backend sur Windows

## Vue d'Ensemble

Ce guide vous permet de démarrer rapidement le backend de l'application Budget sur Windows, même en cas de problèmes avec les dépendances. Plusieurs stratégies de démarrage sont disponibles selon votre configuration.

## 🚀 Démarrage Rapide

### Option 1: Démarrage Automatique (Recommandé)

```bash
python start_degraded.py
```

Ce script :
- ✅ Détecte automatiquement les capacités de votre système
- ✅ Sélectionne le meilleur mode de démarrage disponible  
- ✅ Génère un script personnalisé pour votre configuration
- ✅ Crée un fichier requirements minimal si nécessaire

Puis démarrez avec le script généré :
```bash
python start_complete.py    # ou start_simplified.py, start_minimal_api.py selon votre config
```

### Option 2: Test de l'Import CSV Uniquement

Si vous voulez juste valider que l'import CSV fonctionne :

```bash
python test_csv_critical.py
```

## 🔍 Diagnostic et Dépannage

### Script de Diagnostic Complet

```bash
python diagnostic_windows.py
```

Génère un rapport détaillé (`diagnostic_report.json`) avec :
- ✅ Informations système Windows/WSL
- ✅ État des packages Python requis
- ✅ Test des imports individuels
- ✅ Vérification des modules locaux
- ✅ Test de connectivité base de données
- ✅ Validation des permissions fichiers

### Test des Imports Étape par Étape  

```bash
python test_imports_step_by_step.py
```

Teste chaque import individuellement pour identifier précisément le problème :
- Phase 1: Imports Python de base
- Phase 2: Imports typing
- Phase 3: Imports scientifiques (numpy, pandas)  
- Phase 4: Imports FastAPI
- Phase 5: Imports validation
- Phase 6: Imports base de données
- Phase 7: Imports cryptographiques
- Phase 8: Imports spéciaux (magic, multipart)
- Phase 9: Imports modules locaux

### Test d'Environnement Windows

```bash
python test_environment_windows.py
```

Validation spécifique Windows :
- ✅ Compatibilité Python 3.8+
- ✅ Détection WSL
- ✅ Test permissions répertoires
- ✅ Vérification encodages
- ✅ Test packages avec alternatives Windows
- ✅ Validation fonctionnalité CSV

## 🎯 Modes de Démarrage Disponibles

### Mode Complet (Priorité 1)
```bash
python app.py  # ou start_complete.py
```
**Requis :** FastAPI, uvicorn, pandas, SQLAlchemy, auth, database_encrypted
**Fonctionnalités :** Authentification, chiffrement, API complète, import CSV, audit

### Mode Simplifié (Priorité 2)  
```bash
python app_simple.py  # ou start_simplified.py
```
**Requis :** FastAPI, uvicorn, pandas, SQLAlchemy
**Fonctionnalités :** Authentification basique, base standard, import CSV, API

### Mode Minimal API (Priorité 3)
```bash  
python app_minimal_csv.py  # ou start_minimal_api.py
```
**Requis :** FastAPI, uvicorn
**Fonctionnalités :** Import CSV uniquement, API basique

### Mode Ligne de Commande (Priorité 4)
```bash
python app_minimal_csv.py test                    # Test CSV
python app_minimal_csv.py import fichier.csv      # Import fichier
python app_minimal_csv.py history                 # Historique
```
**Requis :** Python seulement
**Fonctionnalités :** Traitement CSV en ligne de commande

## 🛠️ Résolution des Problèmes Courants

### Problème: pysqlcipher3 non disponible
**Solution :** Le système utilisera SQLite standard automatiquement
```bash
export DISABLE_DB_ENCRYPTION=true
python app_simple.py
```

### Problème: python-magic manquant sur Windows
**Solution :** Installer la version Windows-compatible
```bash
pip install python-magic-bin
```

### Problème: FastAPI/uvicorn manquant
**Solution :** Utiliser le mode ligne de commande
```bash
python app_minimal_csv.py test
```

### Problème: pandas manquant  
**Solution :** Le système utilisera le module csv standard Python
```bash
pip install pandas  # ou continuer sans pandas
```

## 📊 Test de la Fonctionnalité CSV

### Test Complet
```bash
python test_csv_critical.py
```

Valide :
- ✅ Parsing avec module csv standard ET pandas
- ✅ Opérations fichiers (lecture/écriture)  
- ✅ Opérations base de données
- ✅ Intégration complète CSV → Base
- ✅ Performance sur gros fichiers

### Test API CSV (si FastAPI disponible)
```bash
# Démarrer le serveur
python app_minimal_csv.py

# Dans un autre terminal
curl http://localhost:8000/api/test-csv
curl http://localhost:8000/health
```

## 📁 Fichiers Générés

Après exécution des scripts de diagnostic :

- `diagnostic_report.json` - Rapport système complet
- `test_imports_report.json` - Résultats tests imports
- `environment_test_report.json` - Validation environnement  
- `csv_critical_test_results.json` - Tests fonctionnalité CSV
- `degraded_startup_config.json` - Configuration démarrage
- `requirements_fallback.txt` - Packages minimaux
- `start_[mode].py` - Scripts de démarrage personnalisés

## 🔧 Configuration Avancée

### Variables d'Environnement

Créez un fichier `.env` avec :
```bash
# Optionnel: Désactiver le chiffrement si problématique
DISABLE_DB_ENCRYPTION=true

# Configuration serveur
HOST=127.0.0.1
PORT=8000

# Clés générées automatiquement (ajoutées par start_degraded.py)
JWT_SECRET_KEY=...
DB_ENCRYPTION_KEY=...
```

### Forcer un Mode Spécifique

```bash
# Mode simplifié sans chiffrement
DISABLE_DB_ENCRYPTION=true python app_simple.py

# Mode minimal CSV seulement
python app_minimal_csv.py

# Mode ligne de commande
python app_minimal_csv.py test
```

## ✅ Vérification du Succès

### L'application fonctionne si :
1. **Aucune erreur critique** dans les diagnostics
2. **Test CSV** retourne `STATUT GLOBAL: FONCTIONNALITÉ CSV OPÉRATIONNELLE`
3. **Serveur** démarre sans erreur sur `http://localhost:8000`
4. **Endpoint santé** répond : `GET http://localhost:8000/health`

### Points de Contrôle Rapides :
```bash
# 1. Test rapide CSV
python -c "import csv; print('CSV: OK')"

# 2. Test base de données  
python -c "import sqlite3; print('SQLite: OK')"

# 3. Test FastAPI (optionnel)
python -c "from fastapi import FastAPI; print('FastAPI: OK')"
```

## 🆘 Support

En cas de problème persistant :

1. **Exécuter le diagnostic complet** : `python diagnostic_windows.py`
2. **Vérifier les logs** dans les fichiers JSON générés
3. **Essayer le mode minimal** : `python app_minimal_csv.py test`
4. **Vérifier les requirements** : `pip install -r requirements_fallback.txt`

Le mode ligne de commande CSV fonctionne même avec une installation Python minimale et permet de valider l'import CSV même si le serveur web ne démarre pas.