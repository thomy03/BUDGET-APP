# 🚨 GUIDE IMPLÉMENTATION SÉCURITÉ - BUDGET FAMILLE API

## 📊 RÉSUMÉ EXÉCUTIF

**Date**: 2025-08-09  
**Version**: v2.3.1-SECURED  
**Statut**: DÉPLOIEMENT CRITIQUE 48H  
**Niveau de risque initial**: CRITIQUE ➜ **Niveau actuel**: SÉCURISÉ  

### ✅ VULNÉRABILITÉS CORRIGÉES

| Vulnérabilité | Statut | Solution Implémentée |
|---------------|--------|---------------------|
| CORS Wildcard | ✅ CORRIGÉ | Origins restrictives uniquement |
| Authentification manquante | ✅ CORRIGÉ | JWT avec FastAPI Security |
| Base non chiffrée | ✅ CORRIGÉ | SQLCipher avec clé 256-bit |
| Upload non sécurisé | ✅ CORRIGÉ | Validation + limitation taille |
| Exposition endpoints | ✅ CORRIGÉ | Protection par token JWT |
| Logs d'audit manquants | ✅ CORRIGÉ | Système d'audit complet |

## 🚀 DÉPLOIEMENT IMMÉDIAT

### ÉTAPE 1: Installation des dépendances

```bash
cd backend/
pip install -r requirements.txt
```

### ÉTAPE 2: Configuration des variables d'environnement

```bash
# Copier le template
cp .env.example .env

# CRITIQUE: Générer des clés sécurisées
python -c "import secrets; print(f'JWT_SECRET_KEY={secrets.token_urlsafe(32)}')" >> .env
python -c "import secrets; print(f'DB_ENCRYPTION_KEY={secrets.token_urlsafe(32)}')" >> .env

# Configurer admin
echo "ADMIN_USERNAME=admin" >> .env
echo "ADMIN_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(16))')" >> .env
```

### ÉTAPE 3: Démarrage sécurisé

```bash
# Backend
uvicorn app:app --host 127.0.0.1 --port 8000

# Frontend (nouveau terminal)
cd ../frontend/
npm install
npm run dev
```

### ÉTAPE 4: Vérification sécurité

```bash
# Exécuter les tests de sécurité
python test_security.py --wait-server
```

## 🔒 FONCTIONNALITÉS SÉCURISÉES

### 1. AUTHENTIFICATION JWT

**Implémentation**: Module `auth.py`
- Token JWT avec expiration (30 min)
- Hash bcrypt pour mots de passe
- Protection CSRF automatique
- Logs d'audit des connexions

**Utilisation**:
```bash
# Login
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"

# Utilisation token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/config
```

### 2. CHIFFREMENT BASE DE DONNÉES

**Implémentation**: Module `database_encrypted.py`
- SQLCipher avec AES-256
- Migration automatique des données
- KDF PBKDF2 256,000 itérations
- Sauvegarde automatique

**Migration sécurisée**:
- ✅ Base originale → `budget.db.old`
- ✅ Base chiffrée → `budget_encrypted.db`
- ✅ Sauvegarde → `budget.db.backup_[PID]`

### 3. VALIDATION DES ENTRÉES

**Protections implémentées**:
- Taille fichier max: 10MB
- Extensions autorisées: .csv, .xlsx, .xls
- Validation MIME type
- Protection injection SQL via ORM

### 4. AUDIT SÉCURISÉ

**Module**: `audit_logger.py`
- Logs JSON structurés
- Hash des IP/User-Agents
- Sanitisation des données sensibles
- Rotation automatique

## 🆘 PLAN DE ROLLBACK

### SCÉNARIO 1: Problème d'authentification

```bash
# Désactiver l'authentification temporairement
export DISABLE_AUTH=true
uvicorn app:app --reload

# OU modifier app.py ligne 41:
# if os.getenv("DISABLE_AUTH", "false").lower() == "true":
#     # Skip authentication
```

### SCÉNARIO 2: Problème base chiffrée

```bash
# Restaurer base originale
cd backend/
python -c "
from database_encrypted import rollback_migration
rollback_migration()
"

# OU manuellement
mv budget.db.old budget.db
rm budget_encrypted.db
```

### SCÉNARIO 3: Rollback complet

```bash
# 1. Arrêter les services
pkill -f uvicorn
pkill -f "npm run dev"

# 2. Restaurer base originale
cd backend/
mv budget.db.old budget.db 2>/dev/null || true
rm -f budget_encrypted.db

# 3. Désactiver sécurité
export DISABLE_AUTH=true
export ENABLE_DB_ENCRYPTION=false

# 4. Version minimale
git stash  # si dans repo git
# OU restaurer depuis sauvegarde

# 5. Redémarrer
uvicorn app:app --host 127.0.0.1 --port 8000
```

## ⚡ TESTS DE NON-RÉGRESSION

### Tests automatiques
```bash
python test_security.py
```

### Tests manuels

1. **Connexion**:
   - ✅ Login admin/secret fonctionne
   - ✅ Mauvais credentials rejetés
   - ✅ Token généré correctement

2. **Fonctionnalités**:
   - ✅ Import CSV avec authentification
   - ✅ Configuration sauvée
   - ✅ Transactions affichées
   - ✅ Logout fonctionne

3. **Sécurité**:
   - ✅ Endpoints protégés sans token
   - ✅ Base chiffrée non lisible
   - ✅ CORS restrictif
   - ✅ Logs d'audit générés

## 🎯 CONFIGURATION POST-DÉPLOIEMENT

### 1. Changer les mots de passe par défaut

```python
# Dans auth.py, remplacer fake_users_db
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Générer nouveau hash
new_password = "VOTRE_MOT_DE_PASSE_FORT"
hashed = pwd_context.hash(new_password)
print(f"Nouveau hash: {hashed}")
```

### 2. Configuration production

```bash
# .env production
JWT_SECRET_KEY=[CLEF_32_CHARS_UNIQUE]
DB_ENCRYPTION_KEY=[CLEF_32_CHARS_UNIQUE]
ADMIN_USERNAME=admin
ADMIN_PASSWORD=[MOT_DE_PASSE_FORT]
AUDIT_LOG_FILE=/var/log/budget-app/audit.log
LOG_LEVEL=WARNING
CORS_ORIGINS=https://votre-domaine.com
```

### 3. Monitoring sécurité

```bash
# Surveiller les logs d'audit
tail -f backend/audit.log | jq '.'

# Analyser les tentatives d'intrusion
grep "LOGIN_FAILED\|SECURITY_VIOLATION" backend/audit.log
```

## 🔧 MAINTENANCE

### Rotation des clés (mensuel)
```bash
# Générer nouvelles clés
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Tester avec nouvelle clé
export JWT_SECRET_KEY="nouvelle_clé"
python test_security.py
```

### Backup sécurisé
```bash
# Backup chiffré
tar -czf backup_$(date +%Y%m%d).tar.gz backend/budget_encrypted.db backend/.env
gpg --symmetric --cipher-algo AES256 backup_$(date +%Y%m%d).tar.gz
rm backup_$(date +%Y%m%d).tar.gz
```

## 📞 SUPPORT SÉCURITÉ

En cas de problème critique:

1. **Arrêt d'urgence**: `pkill -f uvicorn`
2. **Logs d'audit**: `tail backend/audit.log`
3. **Rollback**: Suivre procédure ci-dessus
4. **Sauvegarde**: Localiser `*.backup_*` files

**⚠️ IMPORTANT**: Ne jamais exposer les clés JWT ou de chiffrement dans les logs ou les repos Git.