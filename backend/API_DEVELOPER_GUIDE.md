# 🚀 Budget Famille API v2.3 - Guide Développeur

## 📋 Table des Matières

- [Vue d'ensemble](#vue-densemble)
- [Installation et démarrage](#installation-et-démarrage)
- [Authentification](#authentification)
- [Endpoints principaux](#endpoints-principaux)
- [Exemples d'intégration](#exemples-dintégration)
- [Gestion des erreurs](#gestion-des-erreurs)
- [Rate limiting et sécurité](#rate-limiting-et-sécurité)
- [Postman Collection](#postman-collection)
- [FAQ et dépannage](#faq-et-dépannage)

---

## 🎯 Vue d'ensemble

Budget Famille v2.3 est une API RESTful complète pour la gestion budgétaire familiale avec architecture modulaire. Elle offre:

- **Authentification JWT** sécurisée avec OAuth2
- **Gestion complète des transactions** avec import CSV
- **Analytics avancés** (KPI, tendances, détection d'anomalies)
- **Système de provisions** personnalisables
- **Charges fixes** configurables
- **Import/Export** multi-formats
- **Architecture modulaire** prête pour l'IA

### 🔧 Technologies utilisées

- **FastAPI** 0.100+ avec documentation OpenAPI automatique
- **SQLAlchemy** avec support SQLite et SQLCipher (chiffrement)
- **JWT** pour l'authentification stateless
- **Pydantic** pour validation et sérialisation
- **Redis** pour le cache (optionnel)
- **Python** 3.8+

---

## 🛠️ Installation et démarrage

### Prérequis

```bash
# Python 3.8+
python --version

# Installer les dépendances
pip install -r requirements.txt

# Pour les fonctionnalités ML (optionnel)
pip install -r requirements_ml.txt
```

### Variables d'environnement

Créer un fichier `.env` :

```bash
# Configuration JWT
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Base de données
DATABASE_URL=sqlite:///./budget.db
ENABLE_DB_ENCRYPTION=false

# Redis (optionnel)
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS=false

# Sécurité
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

### Démarrage du serveur

```bash
# Mode développement
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Mode production
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Vérification

```bash
# Health check
curl http://localhost:8000/health

# Documentation interactive
open http://localhost:8000/docs
```

---

## 🔐 Authentification

### 1. Obtenir un token JWT

**OAuth2 Standard (Form-data):**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password&grant_type=password"
```

**Alternative JSON:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

**Réponse:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2. Utiliser le token

Inclure dans l'header de toutes les requêtes authentifiées:

```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### 3. Valider/Renouveler le token

```bash
# Validation
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/auth/validate

# Renouvellement  
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/auth/refresh
```

---

## 🎯 Endpoints principaux

### 📊 Configuration budgétaire

```bash
# Obtenir la configuration
GET /config
Authorization: Bearer <token>

# Mettre à jour
POST /config
Content-Type: application/json
Authorization: Bearer <token>

{
  "salaire1": 2800.0,
  "salaire2": 2400.0,
  "charges_fixes": 1350.0,
  "provision_vacances": 250.0,
  "r1": 65.0,
  "r2": 35.0,
  "mode": "proportionnel"
}
```

### 💰 Transactions

```bash
# Liste des transactions
GET /transactions?month=2024-01
Authorization: Bearer <token>

# Exclure une transaction
PATCH /transactions/{id}
Content-Type: application/json
Authorization: Bearer <token>

{"exclude": true}

# Mettre à jour les tags
PATCH /transactions/{id}/tags
Content-Type: application/json
Authorization: Bearer <token>

{"tags": "urgent,personnel,alimentation"}
```

### 📈 Analytics

```bash
# KPI sur les 3 derniers mois
GET /analytics/kpis?months=last3
Authorization: Bearer <token>

# Tendances sur 6 mois
GET /analytics/trends?months=last6
Authorization: Bearer <token>

# Répartition par catégories
GET /analytics/categories?month=2024-01
Authorization: Bearer <token>

# Détection d'anomalies
GET /analytics/anomalies?month=2024-01
Authorization: Bearer <token>
```

### 🏦 Provisions personnalisées

```bash
# Liste des provisions
GET /provisions?active_only=true
Authorization: Bearer <token>

# Créer une provision
POST /provisions
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Provision Vacances",
  "description": "Épargne pour les vacances d'été",
  "percentage": 8.0,
  "base_calculation": "net_income",
  "target_amount": 2000.0,
  "icon": "🏖️",
  "color": "#FFD93D"
}

# Résumé des provisions
GET /provisions/summary
Authorization: Bearer <token>
```

### 🏠 Charges fixes

```bash
# Liste des charges fixes
GET /fixed-lines?category=logement
Authorization: Bearer <token>

# Créer une charge fixe
POST /fixed-lines
Content-Type: application/json
Authorization: Bearer <token>

{
  "label": "Assurance Habitation",
  "amount": 45.0,
  "freq": "mensuelle",
  "category": "logement",
  "split_mode": "égalitaire"
}

# Statistiques par catégorie
GET /fixed-lines/stats/by-category
Authorization: Bearer <token>
```

---

## 💻 Exemples d'intégration

### JavaScript/React

```javascript
class BudgetAPI {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('auth_token');
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      localStorage.setItem('auth_token', this.token);
      return data;
    }
    throw new Error('Authentication failed');
  }

  async getKPIs(months = 'last3') {
    const response = await fetch(`${this.baseURL}/analytics/kpis?months=${months}`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return response.json();
  }

  async getTransactions(month) {
    const response = await fetch(`${this.baseURL}/transactions?month=${month}`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return response.json();
  }

  async createProvision(provisionData) {
    const response = await fetch(`${this.baseURL}/provisions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify(provisionData)
    });
    return response.json();
  }
}

// Utilisation
const api = new BudgetAPI();
await api.login('admin', 'password');
const kpis = await api.getKPIs('last6');
```

### Python

```python
import requests
import json
from typing import Optional, Dict, Any

class BudgetAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authentification et récupération du token"""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers avec authentification"""
        if not self.token:
            raise ValueError("Pas de token d'authentification")
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_config(self) -> Dict[str, Any]:
        """Récupérer la configuration budgétaire"""
        response = requests.get(
            f"{self.base_url}/config",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_kpis(self, months: str = "last3") -> Dict[str, Any]:
        """Récupérer les KPI financiers"""
        response = requests.get(
            f"{self.base_url}/analytics/kpis",
            params={"months": months},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def import_csv(self, file_path: str) -> Dict[str, Any]:
        """Importer un fichier CSV de transactions"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/import",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
        response.raise_for_status()
        return response.json()

# Utilisation
client = BudgetAPIClient()
client.login("admin", "password")

# Récupérer la configuration
config = client.get_config()
print(f"Revenus totaux: {config['salaire1'] + config['salaire2']}€")

# Analytics
kpis = client.get_kpis("last6")
print(f"Taux d'épargne: {kpis['savings_rate']}%")

# Import CSV
result = client.import_csv("transactions_janvier.csv")
print(f"Import: {result['rows_processed']} transactions importées")
```

### cURL Scripts

```bash
#!/bin/bash
# budget-api-test.sh

BASE_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="password"

# 1. Authentification
echo "🔐 Authentification..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
echo "Token obtenu: ${TOKEN:0:20}..."

# 2. Configuration
echo "⚙️ Configuration budgétaire..."
curl -s -X GET "$BASE_URL/config" \
  -H "Authorization: Bearer $TOKEN" | jq '.salaire1, .salaire2'

# 3. KPI
echo "📊 KPI derniers 3 mois..."
curl -s -X GET "$BASE_URL/analytics/kpis?months=last3" \
  -H "Authorization: Bearer $TOKEN" | jq '.savings_rate, .total_expenses'

# 4. Provisions
echo "🏦 Provisions actives..."
curl -s -X GET "$BASE_URL/provisions?active_only=true" \
  -H "Authorization: Bearer $TOKEN" | jq 'length'
```

---

## 🚨 Gestion des erreurs

### Codes de statut HTTP

| Code | Description | Action recommandée |
|------|-------------|-------------------|
| 200 | Succès | Traiter la réponse |
| 401 | Token invalide/expiré | Re-authentifier |
| 403 | Accès refusé | Vérifier permissions |
| 422 | Données invalides | Corriger la requête |
| 429 | Rate limit dépassé | Attendre et retry |
| 500 | Erreur serveur | Contacter support |

### Format des erreurs

```json
{
  "detail": "Message d'erreur principal",
  "error_code": "CODE_UNIQUE_001", 
  "timestamp": "2024-01-15T10:30:00Z",
  "context": {
    "field": "username",
    "value": "invalid_user"
  }
}
```

### Gestion en JavaScript

```javascript
async function handleAPICall(apiCall) {
  try {
    const response = await apiCall();
    return response;
  } catch (error) {
    if (error.status === 401) {
      // Token expiré - réauthentifier
      await this.refreshToken();
      return apiCall(); // Retry
    } else if (error.status === 429) {
      // Rate limit - attendre
      await new Promise(resolve => setTimeout(resolve, 5000));
      return apiCall(); // Retry
    } else if (error.status === 422) {
      // Données invalides - afficher erreurs de validation
      console.error('Validation errors:', error.response.data.detail);
    }
    throw error;
  }
}
```

---

## 🔒 Rate limiting et sécurité

### Limites par défaut

- **Authentification**: 5 tentatives/minute par IP
- **API générale**: 100 requêtes/minute par token
- **Import CSV**: 5 fichiers/heure par utilisateur
- **Export**: 10 exports/heure par utilisateur

### Headers de rate limiting

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642587488
Retry-After: 300
```

### Bonnes pratiques sécurité

1. **Stockage du token**: Utiliser httpOnly cookies ou secure storage
2. **HTTPS**: Toujours utiliser HTTPS en production
3. **Expiration**: Gérer l'expiration automatique des tokens
4. **Logging**: Logger les accès pour audit
5. **Validation**: Valider toutes les entrées côté client et serveur

---

## 📦 Postman Collection

### Import de la collection

1. Télécharger `Budget_Famille_API_v2.3.postman_collection.json`
2. Importer dans Postman
3. Configurer les variables d'environnement:
   - `base_url`: http://localhost:8000
   - `username`: admin
   - `password`: password

### Variables automatiques

- Le token JWT est automatiquement sauvegardé après login
- Utilisé automatiquement dans toutes les requêtes authentifiées

### Tests inclus

- Validation des réponses HTTP
- Sauvegarde automatique du token
- Tests de données de réponse

---

## ❓ FAQ et dépannage

### Q: Comment débugger un token JWT ?

```bash
# Endpoint de debug (développement seulement)
curl -X POST "http://localhost:8000/api/v1/auth/debug" \
  -H "Content-Type: application/json" \
  -d '{"token":"eyJ0eXAi..."}'
```

### Q: Erreur "Token expired" fréquente

- Le token expire par défaut après 60 minutes
- Utiliser l'endpoint `/refresh` pour renouveler
- Implémenter un refresh automatique côté client

### Q: Import CSV échoue

1. Vérifier le format du fichier (UTF-8, délimiteurs)
2. Taille maximale: 10MB
3. Colonnes requises: date, montant, libellé
4. Utiliser l'endpoint `/import` avec `multipart/form-data`

### Q: Performances lentes sur analytics

- Activer le cache Redis: `ENABLE_REDIS=true`
- Limiter les périodes d'analyse (éviter `last12`)
- Utiliser la pagination pour gros volumes

### Q: Base de données corrompue

```bash
# Backup automatique
./backup_rotation.sh

# Restauration
./restore_database.sh backup_20240115_120000

# Migration vers SQLCipher
ENABLE_DB_ENCRYPTION=true python migrate.py
```

### Q: Erreurs CORS en développement

Vérifier la configuration dans `.env`:

```bash
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

---

## 🔗 Ressources supplémentaires

- **Documentation API**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Postman Collection**: `Budget_Famille_API_v2.3.postman_collection.json`

---

## 🆘 Support

Pour signaler un bug ou demander une fonctionnalité:

1. Vérifier les logs: `tail -f audit.log`
2. Reproduire avec Postman
3. Documenter les étapes et erreurs
4. Inclure la version (`GET /health`)

---

*Guide mis à jour pour Budget Famille API v2.3.0 - Architecture modulaire*