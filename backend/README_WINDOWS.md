# Backend Budget Famille - Guide Windows

Ce guide explique comment utiliser le backend sur Windows avec les optimisations et fallbacks nécessaires.

## Problèmes identifiés sur Windows

### 1. Dépendances système problématiques

- **pysqlcipher3** : Nécessite libsqlcipher compilé, difficile à installer sur Windows
- **python-magic** : Nécessite libmagic, problématique sur Windows
- **Compilation C/C++** : Certaines dépendances nécessitent Visual Studio Build Tools

### 2. Solutions implementées

✅ **Imports conditionnels** : Le code détecte automatiquement les modules disponibles
✅ **Fallback magic** : Remplacement de python-magic par detection basée sur signatures
✅ **SQLite standard** : Utilisation de SQLite non-chiffré si pysqlcipher3 indisponible
✅ **Gestion d'erreurs robuste** : Récupération gracieuse en cas d'échec de modules

## Installation Windows

### Option 1 : Version minimale (recommandée)

```bash
# Installer les dépendances minimales Windows-safe
pip install -r requirements_windows_minimal.txt

# Tester la compatibilité
python test_windows_compatibility.py

# Utiliser la version optimisée Windows
python app_windows_optimized.py
```

### Option 2 : Version complète (peut échouer)

```bash
# Essayer d'installer toutes les dépendances
pip install -r requirements.txt

# Utiliser la version principale avec fallbacks
python app.py
```

## Fichiers Windows-optimisés

- **app_windows_optimized.py** : Version complète avec tous les fallbacks
- **magic_fallback.py** : Remplacement de python-magic
- **requirements_windows_minimal.txt** : Dépendances Windows-safe uniquement
- **test_windows_compatibility.py** : Script de test complet

## Tests de compatibilité

```bash
# Lancer tous les tests
python test_windows_compatibility.py

# Résultat attendu :
# 🎉 TOUS LES TESTS CRITIQUES RÉUSSIS - Backend compatible Windows!
```

## Fonctionnalités par version

### app_windows_optimized.py (recommandé Windows)

✅ **Imports conditionnels** avec fallbacks complets
✅ **Magic fallback** pour détection MIME
✅ **Auth fallback** si module non disponible  
✅ **Audit fallback** si module non disponible
✅ **Base SQLite standard** (pas de chiffrement)
✅ **Gestion d'erreurs Windows**

### app.py (version principale)

✅ **Imports conditionnels** pour magic uniquement
⚠️  **Chiffrement DB** si pysqlcipher3 disponible
⚠️  **Modules complets** requis pour auth/audit

## Configuration environnement

### Variables .env pour Windows

```env
# Désactiver le chiffrement DB sur Windows
ENABLE_DB_ENCRYPTION=false

# Clés de sécurité (seront générées automatiquement)
JWT_SECRET_KEY=your-jwt-key-here
DB_ENCRYPTION_KEY=your-db-key-here

# Extensions de fichier autorisées
ALLOWED_EXTENSIONS=csv,xlsx,xls
```

## Dépannage Windows

### Erreur : "pysqlcipher3 non disponible"

```bash
# Solution 1 : Utiliser la version Windows optimisée
python app_windows_optimized.py

# Solution 2 : Désactiver le chiffrement
export ENABLE_DB_ENCRYPTION=false
```

### Erreur : "python-magic non disponible"

```bash
# Le fallback magic_fallback.py sera utilisé automatiquement
# Vérifier que le fichier magic_fallback.py existe
```

### Erreur : "Module 'X' non trouvé"

```bash
# Installer les dépendances minimales
pip install -r requirements_windows_minimal.txt

# Ou installer une dépendance spécifique
pip install <nom-du-module>
```

## API Endpoints disponibles

Tous les endpoints standards sont disponibles :

- `GET /health` - Diagnostic système et compatibilité
- `POST /token` - Authentification JWT
- `GET /config` - Configuration budgétaire
- `POST /import` - Import de fichiers CSV/Excel
- `GET /transactions` - Liste des transactions
- `GET /summary` - Résumé budgétaire

## Endpoint de diagnostic

```bash
# Vérifier l'état du système
curl http://localhost:8000/health

# Exemple de réponse Windows :
{
  "status": "ok",
  "version": "0.3.0-win",
  "features": {
    "database_encryption": false,
    "magic_detection": true,
    "audit_logging": true,
    "auth_module": true
  },
  "platform": "windows_optimized"
}
```

## Performance Windows

- ✅ **Import CSV** : Performance identique
- ✅ **API REST** : Performance identique  
- ✅ **Base de données** : SQLite standard très performant
- ⚠️  **Chiffrement** : Non disponible (pas de pysqlcipher3)
- ✅ **Validation fichiers** : Fallback magic aussi efficace

## Sécurité

Même niveau de sécurité avec quelques adaptations :

- ✅ **JWT** : Identique (passlib + jose)
- ✅ **Validation fichiers** : Fallback magic sécurisé
- ✅ **Sanitisation** : Identique
- ⚠️  **Chiffrement DB** : Désactivé par défaut sur Windows
- ✅ **Audit** : Fallback fonctionnel

## Migration vers Windows

Si vous migrez depuis Linux/Mac :

1. **Copier les données** : `budget.db` (SQLite standard)
2. **Installer dépendances** : `requirements_windows_minimal.txt`
3. **Utiliser version optimisée** : `app_windows_optimized.py`
4. **Configurer .env** : `ENABLE_DB_ENCRYPTION=false`

## Support

En cas de problème :

1. **Lancer le test** : `python test_windows_compatibility.py`
2. **Vérifier la santé** : `curl http://localhost:8000/health`
3. **Utiliser les logs** : Mode verbose activé automatiquement
4. **Version de secours** : `app_windows.py` (version simplifiée existante)