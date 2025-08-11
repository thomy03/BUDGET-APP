# 🛠️ Guide de Troubleshooting Complet - Budget Famille v2.3

## 📋 Vue d'ensemble

Ce guide centralise toutes les solutions aux problèmes courants rencontrés avec Budget Famille v2.3, organisées par catégorie avec des solutions éprouvées.

## 🚨 Problèmes Critiques et Solutions

### ❌ PROBLÈME MAJEUR : WSL2 + Next.js Incompatibilité

**🎯 SOLUTION FINALE (100% TESTÉE)** : **Docker Container**

**Symptômes** :
- Next.js se bloque indéfiniment au "Starting..."
- Erreurs SIGBUS lors du build production
- Performance extrêmement dégradée
- Hot-reload non fonctionnel

**Solution Recommandée** :
```bash
# 1. Backend WSL2 natif (performance optimale)
cd backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 2. Frontend Docker (contourne le problème)
cd frontend
./dev-docker.sh start
```

**Résultats** :
- ✅ Démarrage en 2 secondes (vs bloqué)
- ✅ Hot-reload fonctionnel
- ✅ Build production réussi
- ✅ Performance stable

**Documentation détaillée** : `frontend/README-DOCKER.md`

---

## 🔐 Problèmes d'Authentification

### Erreur : "Invalid credentials"

**Causes possibles** :
1. Utilisateur admin non créé
2. Hash de mot de passe corrompu
3. Base de données corrompue

**Solutions** :

**1. Recréer l'utilisateur admin**
```bash
cd backend
python generate_password_hash.py
# Utilise le hash généré dans start.py
python start.py
```

**2. Reset complet de la base**
```bash
cd backend
mv budget.db budget.db.backup
python start.py
# Recrée la DB avec utilisateur admin/secret
```

**3. Vérifier manuellement**
```bash
# Test direct du hash
cd backend
python check_password.py
```

### Token JWT expiré

**Solution** :
- Déconnexion/reconnexion automatique
- Token valide 24h par défaut
- Modification dans `backend/auth.py` si nécessaire

### Erreur CORS

**Symptômes** :
- Erreurs "blocked by CORS policy"
- Requêtes API échouent côté frontend

**Solution** :
```python
# Vérifier backend/app.py
CORS_ORIGINS = [
    "http://localhost:45678",
    "http://0.0.0.0:45678",
    "http://127.0.0.1:45678"
]
```

---

## 📁 Problèmes d'Import CSV

### Import CSV échoue avec erreur 400

**Causes courantes** :
1. Format CSV non reconnu
2. Encodage de fichier problématique
3. Colonnes manquantes ou mal nommées

**Solutions** :

**1. Vérifier le format** :
```bash
# Utiliser les échantillons de test
tests/csv-samples/01_happy_path_janvier_2024.csv
```

**2. Problème d'encodage** :
```bash
# Convertir en UTF-8
file --mime-encoding votre_fichier.csv
iconv -f CP1252 -t UTF-8 votre_fichier.csv > fichier_utf8.csv
```

**3. Diagnostic détaillé** :
```bash
cd backend
python test_csv_import_flow.py votre_fichier.csv
```

### Navigation post-import ne fonctionne pas

**✅ CORRIGÉ dans v2.3.3**

**Problème** : Après import CSV, pas de redirection vers /transactions

**Solution appliquée** :
- Redirection automatique après import réussi
- Feedback visuel avec toast notification
- Synchronisation état global du mois

### Import de gros fichiers lent

**Solutions** :
1. Chunking automatique (implémenté)
2. Traitement en arrière-plan
3. Barre de progression

```bash
# Pour fichiers > 1000 lignes
# Le système traite automatiquement par chunks
```

---

## 🖥️ Problèmes de Performance

### Frontend lent en mode développement

**Solution WSL2** :
- Utiliser la solution Docker (recommandée)
- Ou installation Windows native

**Solution optimisation** :
```bash
# Nettoyer le cache Node.js
npm cache clean --force
rm -rf node_modules .next package-lock.json
npm install
```

### Backend lent

**Diagnostic** :
```bash
cd backend
python -c "import time; print('Test timing:', time.time())"
# Doit être instantané
```

**Solutions** :
1. Vérifier les index de base de données
2. Optimiser les requêtes SQLite
3. Vider les logs volumineux

```bash
# Nettoyer les logs
> backend/app.log
> backend/audit.log
```

### Base de données corrompue

**Symptômes** :
- Erreurs SQLite "database is locked"
- Requêtes qui n'aboutissent jamais
- Données incohérentes

**Solutions** :
```bash
cd backend
# 1. Backup préventif
cp budget.db budget.db.emergency

# 2. Vérification intégrité
sqlite3 budget.db "PRAGMA integrity_check;"

# 3. Réparation
sqlite3 budget.db ".dump" | sqlite3 budget_repaired.db
mv budget_repaired.db budget.db

# 4. Restauration backup si nécessaire
cp backups/manual/budget.db.backup_YYYYMMDD_HHMMSS budget.db
```

---

## 🌐 Problèmes de Réseau et Ports

### Port 8000 déjà utilisé

**Solutions** :

**1. Identifier le processus** :
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/WSL
sudo lsof -ti:8000
kill -9 <PID>
```

**2. Utiliser un port alternatif** :
```bash
# Backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8001

# Frontend (modifier .env.local)
NEXT_PUBLIC_API_BASE=http://localhost:8001
```

### Port 45678 déjà utilisé

**Solutions Docker** :
```bash
# Modifier le port dans dev-docker.sh
docker run -d -p 3000:45678 ...

# Ou utiliser docker-compose avec port mapping
```

### Problème de connexion Backend ↔ Frontend

**Solutions** :

**1. Variables d'environnement** :
```bash
# Frontend .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000

# Si Docker
NEXT_PUBLIC_API_BASE=http://host.docker.internal:8000
```

**2. Test de connectivité** :
```bash
# Depuis le container frontend
docker exec -it budget-frontend curl http://host.docker.internal:8000/health
```

---

## 🐳 Problèmes Docker

### Container ne démarre pas

**Diagnostic** :
```bash
# Vérifier les logs
docker logs budget-frontend

# Vérifier l'image
docker images | grep budget-frontend

# Rebuild complet
./dev-docker.sh clean
./dev-docker.sh rebuild
```

### Erreur "port already in use"

**Solutions** :
```bash
# Arrêter tous les containers
docker stop $(docker ps -aq)

# Ou spécifiquement
docker stop budget-frontend
docker rm budget-frontend
```

### Volume mounting problèmes

**Symptômes** :
- Code changes non reflétées
- Fichiers non persistants

**Solution** :
```bash
# Vérifier les volumes
docker inspect budget-frontend

# Recréer avec volumes corrects
./dev-docker.sh stop
./dev-docker.sh start
```

### Build Docker échoue

**Solutions** :
```bash
# Build sans cache
docker build -f Dockerfile.dev -t budget-frontend-dev . --no-cache

# Vérifier l'espace disque
docker system df
docker system prune  # Si nécessaire
```

---

## 📱 Problèmes d'Interface Utilisateur

### MonthPicker ne fonctionne pas

**✅ CORRIGÉ dans v2.3.3**

**Problèmes résolus** :
- Synchronisation entre calendrier et sélecteur
- Persistance du mois sélectionné
- Navigation cohérente entre pages

### Données ne s'affichent pas

**Solutions** :
1. Vérifier la sélection du mois
2. Contrôler les filtres actifs
3. Valider l'import des données

```bash
# Diagnostic données
cd backend
python -c "
import sqlite3
conn = sqlite3.connect('budget.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM transactions')
print('Total transactions:', cursor.fetchone()[0])
cursor.execute('SELECT DISTINCT month FROM transactions')
print('Mois disponibles:', cursor.fetchall())
"
```

### Interface ne répond pas

**Solutions** :
1. Recharger la page (F5)
2. Vider le cache navigateur
3. Redémarrer les services

```bash
# Redémarrage complet
./dev-docker.sh restart  # Frontend
# Ctrl+C puis relancer le backend
```

---

## 🔧 Problèmes de Configuration

### Variables d'environnement

**Frontend (.env.local)** :
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
NODE_ENV=development
```

**Backend (.env optionnel)** :
```
DATABASE_URL=sqlite:///./budget.db
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=["http://localhost:45678"]
```

### Configuration Docker

**Si problème de communication** :
```bash
# Dans dev-docker.sh, utiliser --network=host
docker run -d --network=host ...

# Ou configurer les variables réseau
-e NEXT_PUBLIC_API_BASE=http://host.docker.internal:8000
```

---

## 🧪 Problèmes de Tests

### Tests échouent

**Solutions** :
1. Vérifier que les services sont démarrés
2. Utiliser les données de test fournies
3. Contrôler les ports et configurations

```bash
# Tests backend
cd backend
python test_comprehensive_integration.py

# Tests frontend
cd frontend
npm test
```

---

## 📊 Problèmes de Données

### Calculs incorrects

**Solutions** :
1. Vérifier la configuration des membres
2. Contrôler les règles de répartition
3. Valider les données source

**Diagnostic** :
```bash
cd backend
python -c "
# Test de calcul simple
from app import calculate_split
print(calculate_split(100, 'equal'))  # Doit être 50/50
"
```

### Données dupliquées

**Solutions** :
```bash
# Detecter doublons
cd backend
python test_duplicates.py

# Nettoyer si nécessaire (backup avant!)
sqlite3 budget.db "DELETE FROM transactions WHERE id IN (
  SELECT id FROM transactions 
  GROUP BY date_op, label, amount 
  HAVING COUNT(*) > 1
);"
```

---

## ⚡ Solutions Rapides

### Problème urgent - Redémarrage complet

```bash
# 1. Arrêter tout
docker stop $(docker ps -aq)  # Si Docker
# Ctrl+C sur le backend

# 2. Nettoyer
docker system prune -f  # Si Docker
rm -rf frontend/.next frontend/node_modules

# 3. Redémarrer proprement
cd backend && python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
cd frontend && ./dev-docker.sh start
```

### Test de santé rapide

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl -I http://localhost:45678

# Authentification
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"
```

### Logs essentiels

```bash
# Backend errors
tail -f backend/app.log

# Docker frontend
docker logs -f budget-frontend

# System
dmesg | tail  # Linux errors
```

---

## 📞 Support et Ressources

### Documentation de référence

1. **Installation** : `docs/GUIDE_INSTALLATION_COMPLET.md`
2. **Docker** : `frontend/README-DOCKER.md`
3. **Backend** : `backend/CONSOLIDATION_GUIDE.md`
4. **Tests** : `docs/installation/GUIDE_TEST_FINAL_IMPORT_CSV.md`

### Scripts de diagnostic

```bash
# Diagnostic automatique
python backend/diagnostic_windows.py

# Tests critiques
python backend/test_critical_fixes.py

# Validation environnement
python backend/test_environment_windows.py
```

### Méthode de rapport de bug

1. **Logs complets** (backend + frontend)
2. **Étapes de reproduction** précises
3. **Configuration** (OS, versions, Docker/natif)
4. **Données de test** utilisées

---

**Version du guide** : v2.3.3  
**Dernière mise à jour** : 2025-08-10  
**Solutions testées** : Windows 11 WSL2, Ubuntu 20.04, Docker Desktop  
**Status** : Toutes les solutions majeures validées et testées
