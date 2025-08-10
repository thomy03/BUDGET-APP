# Solution Windows 10 - Budget App

## 🎯 Problème résolu

Le fichier `app.py` principal ne démarrait pas sur Windows 10 à cause du module `python-magic` qui nécessite des dépendances système complexes (libmagic, DLLs).

## ✅ Solution implementée

### 1. Application Windows optimisée
- **Fichier**: `app_windows.py` 
- **Avantages**: Évite les dépendances problématiques tout en gardant les fonctionnalités essentielles
- **Import CSV**: Fonctionnel et sécurisé
- **Authentification**: JWT avec utilisateur test `admin/secret`
- **Base de données**: SQLite standard (sans chiffrement pour simplifier)

### 2. Script de démarrage simplifié
- **Fichier**: `start_windows.py`
- **Fonctionnalités**:
  - Vérification automatique des dépendances
  - Test d'import des modules
  - Démarrage du serveur avec configuration Windows
  - Messages informatifs pour l'utilisateur

### 3. Script de diagnostic complet  
- **Fichier**: `diagnose_windows.py`
- **Analyse**: Système, modules Python, base de données, CSV, réseau
- **Recommandations**: Automatiques avec commandes à exécuter
- **Rapport**: Sauvegarde JSON pour debugging

## 🚀 Comment démarrer l'application

### Méthode recommandée
```bash
python start_windows.py
```

### Méthode alternative
```bash
python -m uvicorn app_windows:app --host 127.0.0.1 --port 8000 --reload
```

## 📋 Vérifications préalables

### 1. Dépendances requises
```bash
pip install -r requirements_windows.txt
```

### 2. Diagnostic complet
```bash
python diagnose_windows.py
```

## 🔧 Configuration

### Variables d'environnement (optionnelles)
Créer un fichier `.env` :
```env
JWT_SECRET_KEY=your-secret-key
ALLOWED_EXTENSIONS=csv,xlsx,xls
```

### Utilisateur de test
- **Nom d'utilisateur**: `admin`
- **Mot de passe**: `secret`

## 📊 Fonctionnalités disponibles

### ✅ Fonctionnelles sur Windows
- Import CSV avec validation sécurisée
- Authentification JWT 
- Gestion des transactions
- Configuration du budget
- Lignes fixes personnalisées
- API REST complète
- Interface Swagger/OpenAPI

### ⚠️ Simplifications par rapport à app.py
- Pas de détection MIME avec `python-magic`
- Pas de chiffrement SQLCipher (base SQLite standard)
- Validation de fichiers simplifiée mais sécurisée
- Schéma de base de données adapté

## 🌐 Accès à l'application

Une fois démarrée, l'application est accessible à :
- **API principale**: http://127.0.0.1:8000
- **Documentation**: http://127.0.0.1:8000/docs  
- **Alternative docs**: http://127.0.0.1:8000/redoc

## 🛠️ Test de l'import CSV

### Fichier de test fourni
- **Fichier**: `test_windows_import.csv`
- **Format**: Date, Description, Montant, Compte
- **Exemple**:
```csv
Date,Description,Montant,Compte
2024-01-15,Courses Leclerc,-85.50,Compte courant
2024-01-16,Salaire Thomas,2500.00,Compte courant
```

### Via l'interface
1. Aller sur http://127.0.0.1:8000/docs
2. Authentification avec `admin/secret`
3. Endpoint `POST /import`
4. Upload du fichier CSV

## 🔍 Dépannage

### Si `python start_windows.py` ne fonctionne pas

1. **Vérifier Python**:
   ```bash
   python --version
   # ou
   python3 --version  
   ```

2. **Installer les dépendances**:
   ```bash
   pip install -r requirements_windows.txt
   ```

3. **Diagnostic complet**:
   ```bash
   python diagnose_windows.py
   ```

4. **Test import direct**:
   ```bash
   python -c "import app_windows; print('OK')"
   ```

### Si le port 8000 est occupé

1. **Vérifier les processus**:
   ```bash
   netstat -ano | findstr :8000
   ```

2. **Changer le port** dans `start_windows.py`:
   ```python
   uvicorn.run(..., port=8001)
   ```

## 📁 Fichiers de la solution

| Fichier | Description |
|---------|-------------|
| `app_windows.py` | Application principale Windows |
| `start_windows.py` | Script de démarrage simplifié |
| `diagnose_windows.py` | Diagnostic système complet |
| `requirements_windows.txt` | Dépendances Windows |
| `test_windows_import.csv` | Fichier de test CSV |
| `SOLUTION_WINDOWS.md` | Cette documentation |

## 🎉 Prochaines étapes

1. **Démarrer l'application**: `python start_windows.py`
2. **Tester l'import CSV** avec le fichier fourni
3. **Vérifier les corrections** d'import CSV mentionnées
4. **Adapter le frontend** pour pointer vers l'API Windows si nécessaire

## 📞 Support technique

En cas de problème :
1. Exécuter `python diagnose_windows.py` 
2. Consulter le fichier `diagnostic_report.json` généré
3. Vérifier les logs du serveur
4. S'assurer que les ports ne sont pas bloqués par le firewall

---

**✅ Solution testée et validée pour Windows 10**  
**🚀 Application prête à l'utilisation avec toutes les fonctionnalités d'import CSV**