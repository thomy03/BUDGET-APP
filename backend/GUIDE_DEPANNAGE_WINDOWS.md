# Guide de Dépannage - Erreur "Probleme configuration backend"

## 🔍 Diagnostic de l'Erreur

L'erreur "Probleme configuration backend" lors du test `python -c "import app; print('Backend OK')"` peut avoir plusieurs causes sur Windows 10.

## 📋 Solutions par Étapes

### Étape 1: Vérification de l'Environnement

1. **Vérifiez que votre venv est activé:**
   ```bash
   # Le prompt doit afficher (venv) au début
   # Si non activé:
   venv\Scripts\activate
   ```

2. **Vérifiez Python:**
   ```bash
   python --version
   # Doit afficher Python 3.8+ 
   ```

### Étape 2: Diagnostic Automatique

Exécutez le script de diagnostic:
```bash
python diagnostic_windows.py
```

Ce script identifiera les modules manquants et proposera des solutions spécifiques.

### Étape 3: Correction Automatique

Utilisez le script de correction automatique:
```bash
fix_windows_dependencies.bat
```

### Étape 4: Correction Manuelle

Si la correction automatique échoue:

#### Option A - Dépendances Windows (Recommandé)
```bash
pip install --upgrade pip
pip install -r requirements_windows.txt
```

#### Option B - Dépendances Minimales
```bash
pip install --upgrade pip  
pip install -r requirements_minimal.txt
```

#### Option C - Installation Individuelle
```bash
pip install fastapi uvicorn pandas numpy sqlalchemy
pip install python-multipart python-jose[cryptography]
pip install passlib[bcrypt] python-dotenv cryptography
pip install email-validator pydantic[email]
```

### Étape 5: Problèmes Spécifiques Windows

#### Module `python-magic`
Sur Windows, `python-magic` nécessite `libmagic.dll`:
```bash
# Solution recommandée:
pip install python-magic-bin
```

#### Module `pysqlcipher3`
Ce module est problématique sur Windows:
```bash
# Ignorez cette erreur - l'app fonctionne sans SQLCipher
# Elle utilisera SQLite standard à la place
```

## 🔧 Problèmes Courants et Solutions

### Erreur: "Microsoft Visual C++ 14.0 is required"

**Solution:**
1. Téléchargez et installez "Microsoft C++ Build Tools"
2. Ou utilisez les wheels précompilés avec:
   ```bash
   pip install --only-binary=all <package_name>
   ```

### Erreur: "Failed building wheel"

**Solutions:**
1. Mettez à jour pip, setuptools et wheel:
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

2. Utilisez conda si disponible:
   ```bash
   conda install <package_name>
   ```

### Erreur: "SSL: CERTIFICATE_VERIFY_FAILED"

**Solution:**
```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org <package_name>
```

## ✅ Test de Validation

Après correction, testez:
```bash
python -c "import app; print('Backend OK')"
```

Si succès, vous devriez voir:
```
🚨 SÉCURITÉ: Génération d'une nouvelle clé JWT
🚨 SÉCURITÉ: Génération d'une nouvelle clé de chiffrement
INFO:app:✅ Base chiffrée déjà opérationnelle
ERROR:database_encrypted:SQLCipher non disponible (pysqlcipher3 manquant): No module named 'pysqlcipher3'. Fallback SQLite.
INFO:app:🔐 Utilisation base chiffrée SQLCipher
Backend OK
```

⚠️ L'erreur SQLCipher est normale sur Windows - l'application fonctionne correctement.

## 🚀 Démarrage du Backend

Une fois corrigé, démarrez le backend:
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

## 📞 Aide Supplémentaire

### Versions Python Supportées
- Python 3.8+
- Windows 10/11
- Architecture x64 recommandée

### Fichiers de Requirements Disponibles
- `requirements.txt` - Complet avec SQLCipher (peut échouer sur Windows)
- `requirements_windows.txt` - Windows-friendly sans SQLCipher 
- `requirements_minimal.txt` - Version minimale

### Logs de Debug
Les logs détaillés sont dans:
- `audit.log` - Logs d'audit
- Console Python - Erreurs d'import

## 🔒 Note de Sécurité

Le fallback vers SQLite standard (sans chiffrement) est sécurisé pour un usage local. Pour un déploiement en production, configurez SQLCipher correctement.

## 📋 Checklist de Résolution

- [ ] Environnement virtuel activé
- [ ] Python 3.8+ installé
- [ ] pip mis à jour
- [ ] Dépendances Windows installées
- [ ] Test d'import réussi
- [ ] Backend démarre correctement

## 💡 Conseils Préventifs

1. Utilisez toujours un environnement virtuel
2. Mettez à jour pip régulièrement
3. Sur Windows, privilégiez `requirements_windows.txt`
4. Gardez Python à jour (3.8+ minimum)
5. Installez Visual C++ Build Tools si nécessaire