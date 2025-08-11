# 📡 Documentation API - Budget Famille v2.3

## 🎯 Vue d'ensemble

L'API Budget Famille est une API RESTful complète construite avec **FastAPI**, offrant toutes les fonctionnalités pour la gestion budgétaire familiale.

---

## 🔗 Accès à la Documentation

### 📖 Documentation Interactive (Swagger UI)
**URL** : `http://localhost:8000/docs` (serveur local)  
**Contenu** : Interface interactive complète avec test des endpoints  
**Format** : OpenAPI 3.0 auto-générée

### 📋 Documentation ReDoc  
**URL** : `http://localhost:8000/redoc` (serveur local)  
**Contenu** : Documentation formatée, idéale pour consultation  
**Format** : ReDoc style

### 🔧 Schéma OpenAPI  
**URL** : `http://localhost:8000/openapi.json`  
**Contenu** : Spécification OpenAPI complète au format JSON  
**Usage** : Génération clients, outils externes

---

## ⚙️ Configuration API Actuelle

### Informations Générales
- **Titre** : Budget Famille API - Consolidated
- **Version** : 2.3.0  
- **Description** : API unifiée pour la gestion budgétaire familiale - Ubuntu WSL optimisé
- **Base URL** : `http://localhost:8000` (développement)

### 🔒 Sécurité
- **Authentification** : JWT Bearer Token
- **Expiration token** : 24 heures
- **Endpoint auth** : `/token` (POST)
- **Protection CORS** : Configuré pour frontend

### 🌐 CORS Configuration
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:45678",
    "http://127.0.0.1:45678"
]
```

---

## 📋 Endpoints Principaux

### 🔐 Authentification
```http
POST /token
Content-Type: application/x-www-form-urlencoded

username=admin&password=secret
```
**Réponse** : JWT access token + type

### 👤 Utilisateur Actuel  
```http
GET /users/me
Authorization: Bearer {token}
```

### ⚕️ Health Check
```http
GET /health
```
**Réponse** : Status de santé de l'API

---

## 💰 Endpoints Transactions

### Récupérer Transactions
```http
GET /transactions?month=YYYY-MM
Authorization: Bearer {token}
```

### Ajouter Transaction
```http
POST /transactions
Authorization: Bearer {token}
Content-Type: application/json
```

### Mettre à Jour Transaction
```http
PUT /transactions/{id}
Authorization: Bearer {token}
```

### Supprimer Transaction  
```http
DELETE /transactions/{id}
Authorization: Bearer {token}
```

---

## 📄 Import & Export

### Import CSV
```http
POST /import
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [CSV file]
```
**Fonctionnalités** :
- Auto-détection du mois
- Validation format
- Parsing intelligent
- Support encodages multiples

### Export Données
```http
GET /export?month=YYYY-MM&format=csv
Authorization: Bearer {token}
```

---

## ⚙️ Configuration

### Récupérer Configuration
```http
GET /config
Authorization: Bearer {token}
```

### Mettre à Jour Configuration
```http
POST /config  
Authorization: Bearer {token}
Content-Type: application/json
```

---

## 📊 Analytics

### Statistiques par Mois
```http
GET /analytics?month=YYYY-MM
Authorization: Bearer {token}
```

### Répartition par Catégories
```http
GET /categories/summary?month=YYYY-MM
Authorization: Bearer {token}
```

---

## 🏷️ Tags

### Récupérer Tags
```http
GET /tags
Authorization: Bearer {token}
```

### Tags par Mois
```http
GET /tags/summary?month=YYYY-MM
Authorization: Bearer {token}
```

---

## 📝 Modèles de Données

### Transaction
```json
{
  "id": 1,
  "date_op": "2024-01-15",
  "month": "2024-01", 
  "label": "Courses Carrefour",
  "category": "Alimentation",
  "amount": -45.67,
  "account_label": "Compte Principal",
  "is_expense": true,
  "exclude": false,
  "tags": ["courses", "alimentation"]
}
```

### Configuration
```json
{
  "member1": "Diana",
  "member2": "Thomas", 
  "income1": 3200.0,
  "income2": 2800.0,
  "split_mode": "income",
  "loan_amount": 1200.0,
  "loan_equal": false
}
```

### Token Response
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

## ⚠️ Codes d'Erreur

| Code | Description | Exemple |
|------|-------------|---------|
| **200** | Succès | Opération réussie |
| **400** | Requête invalide | Format CSV incorrect |
| **401** | Non autorisé | Token manquant/invalide |
| **403** | Accès refusé | Token expiré |
| **404** | Non trouvé | Transaction inexistante |
| **422** | Données invalides | Validation échouée |
| **500** | Erreur serveur | Erreur base de données |

---

## 🧪 Tests API

### Tests Manuels
```bash
# Health check
curl http://localhost:8000/health

# Authentification
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"

# Test avec token
curl http://localhost:8000/transactions?month=2024-01 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Tests Automatisés
```bash
cd backend
python test_comprehensive_integration.py
```

---

## 🔧 Configuration Développement

### Variables d'Environnement
```env
# .env (optionnel)
DATABASE_URL=sqlite:///./budget.db
SECRET_KEY=your-secret-key
CORS_ORIGINS=["http://localhost:45678"]
DEBUG=true
```

### Démarrage Serveur
```bash
# Développement avec hot-reload
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🚀 Évolutions API Phase 2

### Fonctionnalités Prévues
- **Règles de tags** : CRUD règles d'auto-tagging
- **Lignes fixes** : Gestion postes fixes personnalisés  
- **Export avancé** : PDF, Excel avec formatage
- **Analytics avancés** : Graphiques, tendances
- **Notifications** : Alertes et rappels

### Nouveaux Endpoints Planifiés
```http
# Règles de tags
GET /rules
POST /rules
PUT /rules/{id}
DELETE /rules/{id}

# Lignes fixes
GET /fixed-lines  
POST /fixed-lines
PUT /fixed-lines/{id}

# Export PDF
GET /export/pdf?month=YYYY-MM
```

---

## 📞 Support API

### Logs & Debugging
```bash
# Logs API en temps réel
tail -f backend/app.log

# Debug authentification
python backend/debug_auth.py
```

### Outils Utiles
- **Postman** : Collection pour tests endpoints
- **curl** : Tests ligne de commande
- **httpie** : Alternative moderne à curl
- **Swagger UI** : Tests interactifs intégrés

---

## 🔍 Monitoring & Performance

### Métriques Importantes
- **Temps réponse** : < 100ms pour GET simples
- **Import CSV** : < 2s pour 1000 lignes  
- **Authentification** : < 50ms token validation
- **Disponibilité** : 99.9% uptime attendu

### Health Checks
```http
GET /health
→ {"status": "healthy", "timestamp": "2025-08-10T10:00:00Z"}
```

---

**Version API** : 2.3.0  
**Documentation générée** : 2025-08-10  
**Status** : ✅ Production Ready  
**Accès documentation live** : http://localhost:8000/docs