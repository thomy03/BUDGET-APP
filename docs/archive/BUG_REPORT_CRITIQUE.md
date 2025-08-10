# 🐛 RAPPORT DE BUGS CRITIQUES
## Application Budget Famille v2.3

---

**Date:** 2025-08-09  
**Statut:** BLOQUANT POUR PRODUCTION  
**Priorité:** P0 - Critique  
**Détecté lors de:** Tests d'intégration pré-key user  

---

## 🚨 BUG #001 - SÉCURITÉ UPLOAD FICHIERS
**Priorité:** P0 - CRITIQUE  
**Catégorie:** Sécurité  

### Description
L'endpoint `/import` accepte tous types de fichiers sans validation du type MIME réel, permettant l'upload de fichiers potentiellement dangereux (.exe, .js, .php).

### Reproduction
```bash
curl -X POST "http://127.0.0.1:8000/import" \
  -H "Authorization: Bearer [TOKEN]" \
  -F "file=@malicious.exe;type=text/csv"
# Résultat: Status 200 - Fichier accepté
```

### Impact
- **Risque sécurité majeur** - Exécution code malveillant
- **Compromission serveur** potentielle
- **Non-respect OWASP** guidelines upload

### Solution Requise
```python
import magic

def validate_file_security(file: UploadFile) -> bool:
    # Validation MIME type avec python-magic
    file_header = file.file.read(2048)
    file.file.seek(0)
    mime_type = magic.from_buffer(file_header, mime=True)
    
    allowed_mimes = {
        'text/csv', 
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    return mime_type in allowed_mimes
```

### Tests de Validation
- [ ] Fichier .exe rejeté avec 400
- [ ] Fichier .js rejeté avec 400  
- [ ] Fichier CSV valide accepté
- [ ] Headers MIME falsifiés détectés

---

## 🐛 BUG #002 - DONNÉES NON PERSISTANTES  
**Priorité:** P0 - CRITIQUE  
**Catégorie:** Données  

### Description
Aucun fichier de base de données persistant détecté. Configuration et transactions risquent d'être perdues au redémarrage du serveur.

### Reproduction
1. Configurer l'application (noms, revenus)
2. Importer des transactions
3. Redémarrer le serveur
4. **Résultat:** Données perdues

### Impact
- **Perte de données utilisateur** critique
- **Expérience utilisateur** dégradée
- **Fiabilité application** compromise

### Solution Requise
```python
# Vérifier la création effective du fichier
DATABASE_FILE = Path("budget.db")
if not DATABASE_FILE.exists():
    logger.error("CRITIQUE: Fichier BDD non créé")
    
# Ajouter test de persistance
def test_data_persistence():
    # Insérer données
    # Redémarrer service
    # Vérifier données présentes
```

### Tests de Validation
- [ ] Fichier budget.db créé au démarrage
- [ ] Configuration sauvée après modification
- [ ] Transactions persistées après import
- [ ] Redémarrage ne perd pas les données

---

## ⚠️ BUG #003 - LIMITE TAILLE FICHIER MANQUANTE
**Priorité:** P1 - Élevé  
**Catégorie:** Performance/Sécurité  

### Description
Aucune limitation de taille sur l'upload de fichiers. Vulnérabilité DoS par upload de fichiers volumineux.

### Reproduction
```bash
# Créer fichier 100MB
dd if=/dev/zero of=large.csv bs=1M count=100

curl -X POST "http://127.0.0.1:8000/import" \
  -H "Authorization: Bearer [TOKEN]" \
  -F "file=@large.csv;type=text/csv"
# Résultat: Status 200 - Fichier traité (risque mémoire)
```

### Impact
- **Vulnérabilité DoS** par saturation mémoire
- **Performance** dégradée
- **Coûts serveur** non maîtrisés

### Solution Requise
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file_size(file: UploadFile):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Fichier trop volumineux")
    await file.seek(0)  # Reset pour traitement
```

---

## ⚠️ BUG #004 - VALIDATION JWT INCOHÉRENTE
**Priorité:** P2 - Moyen  
**Catégorie:** Sécurité  

### Description
Certains endpoints acceptent des tokens JWT malformés ou invalides, compromettant la sécurité d'authentification.

### Reproduction
```bash
curl -X GET "http://127.0.0.1:8000/config" \
  -H "Authorization: Bearer invalid_token_here"
# Résultat: Status 200 au lieu de 401
```

### Impact
- **Contournement authentification** possible
- **Accès non autorisé** aux données
- **Sécurité** compromise

### Solution Requise
```python
# Middleware global de validation JWT
@app.middleware("http")
async def validate_jwt_middleware(request: Request, call_next):
    protected_paths = ["/config", "/transactions", "/summary"]
    
    if request.url.path in protected_paths:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not validate_jwt_token(auth_header):
            return JSONResponse(
                status_code=401, 
                content={"detail": "Token invalide"}
            )
    
    return await call_next(request)
```

---

## 📋 PLAN DE RÉSOLUTION

### Phase Immédiate (4-8 heures)
1. **Validation Upload Sécurisée** (2h)
   - Implémenter python-magic
   - Tester types MIME
   - Bloquer extensions dangereuses

2. **Persistance Base Données** (2h)
   - Vérifier chemin fichier SQLite
   - Tester write/read permissions
   - Valider persistance au redémarrage

### Phase Suivante (2-4 heures)  
3. **Limite Taille Fichiers** (1h)
   - Implémenter limite 10MB
   - Message erreur utilisateur
   
4. **Validation JWT Globale** (2h)
   - Middleware authentification
   - Tests tous endpoints

### Validation Corrections
- [ ] Tests automatisés pour chaque bug
- [ ] Validation manuelle scénarios utilisateur
- [ ] Tests de régression complets
- [ ] Documentation mise à jour

---

## ✅ CRITÈRES D'ACCEPTATION

### Bug #001 - Upload Sécurisé
- [ ] `.exe`, `.js`, `.php` rejetés avec 400
- [ ] Types MIME vérifiés avec magic numbers
- [ ] CSV/Excel valides acceptés uniquement
- [ ] Messages d'erreur utilisateur clairs

### Bug #002 - Persistance
- [ ] Fichier `budget.db` créé et accessible
- [ ] Configuration persistante entre redémarrages  
- [ ] Transactions sauvées immédiatement
- [ ] Récupération données après crash

### Bug #003 - Limite Taille
- [ ] Fichiers > 10MB rejetés (413)
- [ ] Message erreur avec limite explicite
- [ ] Performance maintenue avec gros fichiers
- [ ] Pas de consommation mémoire excessive

### Bug #004 - JWT Cohérent
- [ ] Token invalide = 401 sur tous endpoints
- [ ] Token expiré géré correctement
- [ ] Headers Authorization vérifiés
- [ ] Bypass impossible

---

## 🎯 IMPACT SUR PLANNING

**Délai estimé résolution:** 6-12 heures  
**Tests validation:** 2-4 heures  
**Mise en prod:** Possible après corrections

**Recommandation:** Reporter tests utilisateur key user de 1-2 jours pour garantir la qualité et sécurité maximales.

---

*Rapport généré automatiquement par tests d'intégration*  
*Assigné à: Équipe Développement*  
*Review par: QA Lead*