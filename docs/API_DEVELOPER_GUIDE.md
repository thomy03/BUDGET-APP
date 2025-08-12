# 🚀 Guide Développeur - Budget Famille API v2.3

## Vue d'ensemble

L'API Budget Famille v2.3 est une API REST complète construite avec **FastAPI** et optimisée pour la gestion budgétaire familiale. Ce guide vous accompagnera depuis la configuration initiale jusqu'à l'intégration avancée.

## 📋 Table des Matières

- [🛠️ Configuration Rapide](#️-configuration-rapide)
- [🔐 Authentification](#-authentification)
- [📊 Concepts Métier](#-concepts-métier)
- [🎯 Cas d'Usage Courants](#-cas-dusage-courants)
- [📦 SDKs et Clients](#-sdks-et-clients)
- [🔧 Gestion d'Erreurs](#-gestion-derreurs)
- [📈 Performance et Cache](#-performance-et-cache)
- [🧪 Tests et Validation](#-tests-et-validation)

---

## 🛠️ Configuration Rapide

### 1. Prérequis

```bash
# Vérifier que l'API est disponible
curl http://localhost:8000/health

# Réponse attendue
{
  "status": "ok",
  "version": "2.3.0",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### 2. Première Authentification

```bash
# Obtenir un token JWT
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"

# Réponse
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 3. Test de Connexion Authentifiée

```bash
# Utiliser le token pour une requête protégée
export TOKEN="your-jwt-token-here"

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/transactions?month=2024-01
```

---

## 🔐 Authentification

### Flow OAuth2 Standard

L'API utilise le standard OAuth2 Password Flow avec tokens JWT.

#### Python (requests)

```python
import requests
import json
from datetime import datetime, timedelta

class BudgetFamilleClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.token_expires = None
    
    def authenticate(self, username, password):
        """Authentification et stockage du token"""
        response = requests.post(
            f"{self.base_url}/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
            return True
        else:
            raise Exception(f"Authentication failed: {response.text}")
    
    def _get_headers(self):
        """Headers avec token d'authentification"""
        if not self.token or datetime.now() >= self.token_expires:
            raise Exception("Token expired or missing. Please authenticate.")
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_transactions(self, month):
        """Récupérer les transactions d'un mois"""
        response = requests.get(
            f"{self.base_url}/transactions",
            params={"month": month},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

# Utilisation
client = BudgetFamilleClient()
client.authenticate("admin", "secret")
transactions = client.get_transactions("2024-01")
```

#### JavaScript (Fetch API)

```javascript
class BudgetFamilleAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
        this.token = localStorage.getItem('budget_token');
        this.tokenExpiry = localStorage.getItem('budget_token_expiry');
    }

    async authenticate(username, password) {
        try {
            const response = await fetch(`${this.baseURL}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    username,
                    password
                })
            });

            if (!response.ok) {
                throw new Error(`Authentication failed: ${response.status}`);
            }

            const data = await response.json();
            this.token = data.access_token;
            this.tokenExpiry = Date.now() + (data.expires_in * 1000);
            
            // Sauvegarder en localStorage
            localStorage.setItem('budget_token', this.token);
            localStorage.setItem('budget_token_expiry', this.tokenExpiry);
            
            return data;
        } catch (error) {
            console.error('Authentication error:', error);
            throw error;
        }
    }

    async request(endpoint, options = {}) {
        // Vérifier la validité du token
        if (!this.token || Date.now() >= this.tokenExpiry) {
            throw new Error('Token expired. Please authenticate.');
        }

        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        const response = await fetch(url, config);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`API Error ${response.status}: ${errorData.detail || response.statusText}`);
        }

        return response.json();
    }

    // Méthodes convenience
    async getTransactions(month) {
        return this.request(`/transactions?month=${month}`);
    }

    async importCSV(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        return fetch(`${this.baseURL}/import`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`
            },
            body: formData
        }).then(res => res.json());
    }
}

// Utilisation
const api = new BudgetFamilleAPI();
await api.authenticate('admin', 'secret');
const transactions = await api.getTransactions('2024-01');
```

---

## 📊 Concepts Métier

### Structure des Données

#### Transaction
```json
{
  "id": 1425,
  "month": "2024-01",
  "date_op": "2024-01-15",
  "label": "Courses Carrefour Market",
  "category": "Alimentation",
  "category_parent": "Dépenses courantes",
  "amount": -45.67,
  "account_label": "Compte Principal",
  "is_expense": true,
  "exclude": false,
  "tags": ["courses", "alimentation", "carrefour"],
  "import_id": "import_20240115_123456"
}
```

#### Configuration Familiale
```json
{
  "member1": "Diana",
  "member2": "Thomas",
  "rev1": 3200.00,
  "rev2": 2800.00,
  "split_mode": "revenus",
  "split1": 0.53,
  "split2": 0.47,
  "other_split_mode": "clé",
  "var_percent": 30.0
}
```

#### Provision Personnalisée
```json
{
  "id": 15,
  "name": "Voyage Été 2024",
  "description": "Provision pour vacances familiales",
  "percentage": 5.0,
  "base_calculation": "total",
  "split_mode": "key",
  "monthly_amount": 300.00,
  "created_at": "2024-01-10T09:00:00Z"
}
```

---

## 🎯 Cas d'Usage Courants

### 1. Import de Relevé Bancaire

```python
def import_bank_statement(client, csv_file_path):
    """Import complet d'un relevé bancaire avec validation"""
    
    # 1. Ouvrir et préparer le fichier
    with open(csv_file_path, 'rb') as file:
        files = {'file': ('releve.csv', file, 'text/csv')}
        
        # 2. Lancer l'import
        response = requests.post(
            f"{client.base_url}/import",
            files=files,
            headers={"Authorization": f"Bearer {client.token}"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Import failed: {response.text}")
        
        import_data = response.json()
        
        # 3. Analyser les résultats
        print(f"✅ Import {import_data['importId']} terminé")
        print(f"📊 {len(import_data['months'])} mois détectés")
        
        for month_data in import_data['months']:
            print(f"  📅 {month_data['month']}: {month_data['newCount']} nouvelles transactions")
        
        if import_data['duplicatesCount'] > 0:
            print(f"⚠️  {import_data['duplicatesCount']} doublons ignorés")
        
        if import_data['warnings']:
            print("⚠️  Avertissements:")
            for warning in import_data['warnings']:
                print(f"    - {warning}")
        
        return import_data

# Utilisation
result = import_bank_statement(client, "releve_janvier_2024.csv")
```

### 2. Calcul de Répartition Intelligente

```python
def calculate_family_split(client, month):
    """Calcule la répartition familiale pour un mois"""
    
    # 1. Récupérer la configuration
    config = requests.get(
        f"{client.base_url}/config",
        headers=client._get_headers()
    ).json()
    
    # 2. Récupérer le résumé financier
    summary = requests.get(
        f"{client.base_url}/summary",
        params={"month": month},
        headers=client._get_headers()
    ).json()
    
    # 3. Analyser la répartition
    repartition = summary['repartition']
    
    analysis = {
        'month': month,
        'total_income': summary['total_revenus'],
        'total_expenses': summary['total_depenses'],
        'balance': summary['solde'],
        'member1': {
            'name': config['member1'],
            'income': config['rev1'],
            'share': repartition['member1'],
            'percentage': repartition['member1'] / summary['total_revenus'] * 100
        },
        'member2': {
            'name': config['member2'],
            'income': config['rev2'],
            'share': repartition['member2'],
            'percentage': repartition['member2'] / summary['total_revenus'] * 100
        }
    }
    
    return analysis

# Utilisation avec formatage
analysis = calculate_family_split(client, "2024-01")
print(f"💰 Analyse financière {analysis['month']}")
print(f"   {analysis['member1']['name']}: {analysis['member1']['share']:.2f}€ ({analysis['member1']['percentage']:.1f}%)")
print(f"   {analysis['member2']['name']}: {analysis['member2']['share']:.2f}€ ({analysis['member2']['percentage']:.1f}%)")
```

### 3. Monitoring et Alertes

```python
import asyncio
from datetime import datetime, timedelta

class BudgetMonitor:
    def __init__(self, client):
        self.client = client
        self.thresholds = {
            'high_expense': 500.0,  # Transaction > 500€
            'monthly_budget': 3000.0,  # Budget mensuel
            'category_limit': {
                'Alimentation': 600.0,
                'Loisirs': 300.0,
                'Transport': 400.0
            }
        }
    
    async def check_anomalies(self, month):
        """Détection d'anomalies financières"""
        
        # 1. Récupérer les anomalies ML
        ml_anomalies = requests.get(
            f"{self.client.base_url}/analytics/anomalies",
            params={"month": month, "threshold": 0.8},
            headers=self.client._get_headers()
        ).json()
        
        # 2. Vérifier les limites par catégorie
        categories = requests.get(
            f"{self.client.base_url}/analytics/categories",
            params={"month": month},
            headers=self.client._get_headers()
        ).json()
        
        alerts = []
        
        # Anomalies ML
        for anomaly in ml_anomalies:
            if anomaly['anomaly_score'] > 0.9:
                alerts.append({
                    'type': 'ML_ANOMALY',
                    'severity': 'HIGH',
                    'transaction_id': anomaly['transaction_id'],
                    'reason': anomaly['reason'],
                    'score': anomaly['anomaly_score']
                })
        
        # Dépassements budgétaires
        for cat in categories:
            if cat['category'] in self.thresholds['category_limit']:
                limit = self.thresholds['category_limit'][cat['category']]
                if abs(cat['total_amount']) > limit:
                    alerts.append({
                        'type': 'BUDGET_EXCEEDED',
                        'severity': 'MEDIUM',
                        'category': cat['category'],
                        'amount': cat['total_amount'],
                        'limit': limit,
                        'overage': abs(cat['total_amount']) - limit
                    })
        
        return alerts
    
    def format_alerts(self, alerts):
        """Formatage des alertes pour notification"""
        if not alerts:
            return "✅ Aucune anomalie détectée"
        
        message = f"⚠️ {len(alerts)} alerte(s) détectée(s):\n\n"
        
        for alert in alerts:
            if alert['type'] == 'ML_ANOMALY':
                message += f"🤖 Anomalie ML (Score: {alert['score']:.2f})\n"
                message += f"   Transaction ID: {alert['transaction_id']}\n"
                message += f"   Raison: {alert['reason']}\n\n"
            
            elif alert['type'] == 'BUDGET_EXCEEDED':
                message += f"💸 Dépassement budgétaire\n"
                message += f"   Catégorie: {alert['category']}\n"
                message += f"   Montant: {alert['amount']:.2f}€ (Limite: {alert['limit']:.2f}€)\n"
                message += f"   Dépassement: +{alert['overage']:.2f}€\n\n"
        
        return message

# Utilisation
monitor = BudgetMonitor(client)
alerts = asyncio.run(monitor.check_anomalies("2024-01"))
print(monitor.format_alerts(alerts))
```

---

## 📦 SDKs et Clients

### Client TypeScript/Node.js

```typescript
interface Transaction {
  id: number;
  month: string;
  date_op: string;
  label: string;
  category: string;
  amount: number;
  is_expense: boolean;
  tags: string[];
}

interface ImportResult {
  importId: string;
  months: Array<{
    month: string;
    newCount: number;
    totalCount: number;
  }>;
  duplicatesCount: number;
  warnings: string[];
  errors: string[];
}

class BudgetFamilleSDK {
  private baseURL: string;
  private token?: string;
  private tokenExpiry?: number;

  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async authenticate(username: string, password: string): Promise<void> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${this.baseURL}/token`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Authentication failed: ${response.statusText}`);
    }

    const data = await response.json();
    this.token = data.access_token;
    this.tokenExpiry = Date.now() + (data.expires_in * 1000);
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    if (!this.token || Date.now() >= (this.tokenExpiry || 0)) {
      throw new Error('Token expired. Please authenticate.');
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`API Error ${response.status}: ${errorData.detail || response.statusText}`);
    }

    return response.json();
  }

  async getTransactions(month: string): Promise<Transaction[]> {
    return this.request<Transaction[]>(`/transactions?month=${month}`);
  }

  async importCSV(file: File): Promise<ImportResult> {
    if (!this.token) {
      throw new Error('Not authenticated');
    }

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseURL}/import`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Import failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getSummary(month: string): Promise<any> {
    return this.request(`/summary?month=${month}`);
  }

  async getAnalytics(month: string): Promise<any> {
    return this.request(`/analytics/kpis?month=${month}`);
  }
}

// Utilisation
const sdk = new BudgetFamilleSDK();
await sdk.authenticate('admin', 'secret');

const transactions = await sdk.getTransactions('2024-01');
const summary = await sdk.getSummary('2024-01');
```

---

## 🔧 Gestion d'Erreurs

### Codes d'Erreur Standards

| Code | Description | Action Recommandée |
|------|-------------|-------------------|
| **400** | Requête invalide | Vérifier format des données |
| **401** | Non authentifié | Renouveler le token |
| **403** | Accès interdit | Vérifier permissions |
| **404** | Ressource non trouvée | Vérifier l'ID/endpoint |
| **422** | Erreur de validation | Corriger les données |
| **429** | Trop de requêtes | Implémenter rate limiting |
| **500** | Erreur serveur | Réessayer + contacter support |

### Gestion Robuste des Erreurs

```python
import time
import logging
from typing import Optional

class APIError(Exception):
    def __init__(self, status_code: int, detail: str, response_data: Optional[dict] = None):
        self.status_code = status_code
        self.detail = detail
        self.response_data = response_data or {}
        super().__init__(f"API Error {status_code}: {detail}")

class RobustBudgetClient:
    def __init__(self, base_url: str, max_retries: int = 3):
        self.base_url = base_url
        self.max_retries = max_retries
        self.token = None
        self.logger = logging.getLogger(__name__)
    
    def _handle_response(self, response):
        """Gestion centralisée des réponses et erreurs"""
        if response.status_code == 200:
            return response.json()
        
        # Tenter de parser le JSON d'erreur
        try:
            error_data = response.json()
            detail = error_data.get('detail', 'Unknown error')
        except:
            detail = response.text or f"HTTP {response.status_code}"
        
        # Gestion spécifique par code d'erreur
        if response.status_code == 401:
            self.token = None  # Forcer une nouvelle authentification
            raise APIError(401, "Token expired or invalid - please re-authenticate")
        
        elif response.status_code == 422:
            validation_errors = error_data.get('detail', [])
            if isinstance(validation_errors, list):
                formatted_errors = []
                for err in validation_errors:
                    field = ' -> '.join(err.get('loc', []))
                    msg = err.get('msg', 'Invalid value')
                    formatted_errors.append(f"{field}: {msg}")
                detail = "Validation errors:\n" + '\n'.join(formatted_errors)
        
        raise APIError(response.status_code, detail, error_data)
    
    def _retry_request(self, func, *args, **kwargs):
        """Mécanisme de retry avec backoff exponentiel"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            
            except APIError as e:
                last_exception = e
                
                # Certaines erreurs ne doivent pas être retentées
                if e.status_code in [400, 401, 403, 404, 422]:
                    raise
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Backoff exponentiel
                    self.logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed: {e}")
                    raise
            
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Unexpected error (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise last_exception
    
    def get_transactions_safe(self, month: str):
        """Version robuste de get_transactions avec retry"""
        def _make_request():
            response = requests.get(
                f"{self.base_url}/transactions",
                params={"month": month},
                headers=self._get_headers(),
                timeout=30
            )
            return self._handle_response(response)
        
        return self._retry_request(_make_request)

# Utilisation avec gestion d'erreurs
client = RobustBudgetClient("http://localhost:8000")

try:
    transactions = client.get_transactions_safe("2024-01")
    print(f"✅ {len(transactions)} transactions récupérées")
    
except APIError as e:
    if e.status_code == 401:
        print("🔑 Authentification requise")
        # Re-authentifier automatiquement
        client.authenticate("admin", "secret")
        transactions = client.get_transactions_safe("2024-01")
    
    elif e.status_code == 422:
        print(f"❌ Données invalides: {e.detail}")
    
    else:
        print(f"💥 Erreur API: {e}")

except Exception as e:
    print(f"⚠️ Erreur inattendue: {e}")
```

---

## 📈 Performance et Cache

### Optimisation des Requêtes

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class AsyncBudgetClient:
    def __init__(self, base_url: str, max_concurrent: int = 10):
        self.base_url = base_url
        self.token = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def get_multiple_months(self, months: list):
        """Récupération parallèle de plusieurs mois"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._get_month_data(session, month) 
                for month in months
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrer les erreurs
            successful_results = []
            for month, result in zip(months, results):
                if isinstance(result, Exception):
                    print(f"⚠️ Erreur pour {month}: {result}")
                else:
                    successful_results.append((month, result))
            
            return successful_results
    
    async def _get_month_data(self, session, month):
        """Récupération des données d'un mois avec limitation de concurrence"""
        async with self.semaphore:
            async with session.get(
                f"{self.base_url}/transactions",
                params={"month": month},
                headers={"Authorization": f"Bearer {self.token}"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")

# Utilisation pour analyse multi-mois
async def analyze_yearly_trends():
    client = AsyncBudgetClient("http://localhost:8000")
    # Authentification synchrone
    client.authenticate("admin", "secret")
    
    months = [f"2024-{i:02d}" for i in range(1, 13)]  # Année 2024
    
    print("📊 Récupération des données annuelles...")
    results = await client.get_multiple_months(months)
    
    yearly_analysis = {}
    total_income = 0
    total_expenses = 0
    
    for month, transactions in results:
        income = sum(t['amount'] for t in transactions if not t['is_expense'])
        expenses = sum(abs(t['amount']) for t in transactions if t['is_expense'])
        
        yearly_analysis[month] = {
            'income': income,
            'expenses': expenses,
            'balance': income - expenses,
            'transaction_count': len(transactions)
        }
        
        total_income += income
        total_expenses += expenses
    
    print(f"💰 Analyse annuelle 2024:")
    print(f"   Revenus totaux: {total_income:,.2f}€")
    print(f"   Dépenses totales: {total_expenses:,.2f}€")
    print(f"   Économies: {total_income - total_expenses:,.2f}€")
    
    return yearly_analysis

# Exécution
results = asyncio.run(analyze_yearly_trends())
```

### Cache Intelligent

```python
import redis
import json
import hashlib
from datetime import datetime, timedelta

class CachedBudgetClient:
    def __init__(self, base_url: str, redis_host: str = "localhost"):
        self.base_url = base_url
        self.token = None
        try:
            self.redis_client = redis.Redis(host=redis_host, decode_responses=True)
            self.redis_available = True
        except:
            self.redis_available = False
            print("⚠️ Redis non disponible - cache désactivé")
    
    def _cache_key(self, endpoint: str, params: dict = None):
        """Génère une clé de cache unique"""
        params_str = json.dumps(params or {}, sort_keys=True)
        key_content = f"{endpoint}:{params_str}"
        return f"budget_api:{hashlib.md5(key_content.encode()).hexdigest()}"
    
    def _get_cached(self, cache_key: str):
        """Récupère une valeur du cache"""
        if not self.redis_available:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Cache read error: {e}")
        
        return None
    
    def _set_cache(self, cache_key: str, data, ttl_seconds: int = 300):
        """Met en cache une valeur"""
        if not self.redis_available:
            return
        
        try:
            self.redis_client.setex(
                cache_key, 
                ttl_seconds, 
                json.dumps(data, default=str)
            )
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def get_transactions_cached(self, month: str, use_cache: bool = True):
        """Récupération des transactions avec mise en cache"""
        cache_key = self._cache_key("/transactions", {"month": month})
        
        # Tenter de récupérer du cache
        if use_cache:
            cached_data = self._get_cached(cache_key)
            if cached_data:
                print(f"📦 Cache hit pour {month}")
                return cached_data
        
        # Récupération depuis l'API
        print(f"🌐 API call pour {month}")
        response = requests.get(
            f"{self.base_url}/transactions",
            params={"month": month},
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            # Mettre en cache (TTL: 5 minutes)
            self._set_cache(cache_key, data, ttl_seconds=300)
            return data
        else:
            response.raise_for_status()
    
    def warm_cache(self, months: list):
        """Préchauffage du cache pour plusieurs mois"""
        print(f"🔥 Préchauffage du cache pour {len(months)} mois...")
        
        for month in months:
            try:
                self.get_transactions_cached(month, use_cache=False)
                print(f"   ✅ {month} mis en cache")
            except Exception as e:
                print(f"   ❌ Erreur pour {month}: {e}")
    
    def invalidate_cache_pattern(self, pattern: str = "budget_api:*"):
        """Invalide le cache selon un pattern"""
        if not self.redis_available:
            return 0
        
        keys = self.redis_client.keys(pattern)
        if keys:
            return self.redis_client.delete(*keys)
        return 0

# Utilisation avec cache
client = CachedBudgetClient("http://localhost:8000")
client.authenticate("admin", "secret")

# Premier appel - depuis l'API
transactions_jan = client.get_transactions_cached("2024-01")

# Deuxième appel - depuis le cache
transactions_jan_cached = client.get_transactions_cached("2024-01")

# Préchauffage pour plusieurs mois
client.warm_cache(["2024-01", "2024-02", "2024-03"])

# Invalidation du cache
cleared = client.invalidate_cache_pattern("budget_api:*")
print(f"🗑️ {cleared} entrées supprimées du cache")
```

---

## 🧪 Tests et Validation

### Suite de Tests Complète

```python
import pytest
import requests
from unittest.mock import patch
import tempfile
import csv

class TestBudgetFamilleAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuration des tests"""
        self.base_url = "http://localhost:8000"
        self.client = BudgetFamilleClient(self.base_url)
        self.client.authenticate("admin", "secret")
        self.test_month = "2024-01"
    
    def test_authentication_success(self):
        """Test d'authentification réussie"""
        client = BudgetFamilleClient(self.base_url)
        result = client.authenticate("admin", "secret")
        
        assert result is True
        assert client.token is not None
        assert client.token_expires is not None
    
    def test_authentication_failure(self):
        """Test d'authentification échouée"""
        client = BudgetFamilleClient(self.base_url)
        
        with pytest.raises(Exception, match="Authentication failed"):
            client.authenticate("wrong_user", "wrong_password")
    
    def test_get_transactions(self):
        """Test récupération des transactions"""
        transactions = self.client.get_transactions(self.test_month)
        
        assert isinstance(transactions, list)
        
        if transactions:
            tx = transactions[0]
            required_fields = ['id', 'month', 'date_op', 'label', 'amount', 'is_expense']
            for field in required_fields:
                assert field in tx, f"Field {field} missing from transaction"
    
    def test_csv_import(self):
        """Test d'import CSV"""
        # Créer un fichier CSV de test
        test_data = [
            ['dateOp', 'label', 'amount', 'category'],
            ['2024-01-15', 'Test Transaction', '-25.50', 'Test Category'],
            ['2024-01-16', 'Test Income', '100.00', 'Revenus']
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as file:
                files = {'file': ('test.csv', file, 'text/csv')}
                response = requests.post(
                    f"{self.base_url}/import",
                    files=files,
                    headers={"Authorization": f"Bearer {self.client.token}"}
                )
            
            assert response.status_code == 200
            
            import_data = response.json()
            assert 'importId' in import_data
            assert 'months' in import_data
            assert len(import_data['months']) > 0
            
        finally:
            import os
            os.unlink(temp_file)
    
    def test_summary_calculation(self):
        """Test des calculs de résumé"""
        summary_response = requests.get(
            f"{self.base_url}/summary",
            params={"month": self.test_month},
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        
        assert summary_response.status_code == 200
        
        summary = summary_response.json()
        required_fields = ['total_revenus', 'total_depenses', 'solde', 'repartition']
        
        for field in required_fields:
            assert field in summary, f"Field {field} missing from summary"
        
        # Vérification de cohérence des calculs
        calculated_balance = summary['total_revenus'] - summary['total_depenses']
        assert abs(calculated_balance - summary['solde']) < 0.01, "Balance calculation mismatch"
    
    def test_provisions_crud(self):
        """Test CRUD des provisions"""
        # Créer une provision
        provision_data = {
            "name": "Test Provision",
            "description": "Test description",
            "percentage": 5.0,
            "base_calculation": "total",
            "split_mode": "key"
        }
        
        create_response = requests.post(
            f"{self.base_url}/provisions",
            json=provision_data,
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        
        assert create_response.status_code == 200
        created_provision = create_response.json()
        provision_id = created_provision['id']
        
        # Lire la provision
        get_response = requests.get(
            f"{self.base_url}/provisions/{provision_id}",
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        
        assert get_response.status_code == 200
        retrieved_provision = get_response.json()
        assert retrieved_provision['name'] == provision_data['name']
        
        # Modifier la provision
        update_data = {"name": "Updated Test Provision"}
        update_response = requests.put(
            f"{self.base_url}/provisions/{provision_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        
        assert update_response.status_code == 200
        updated_provision = update_response.json()
        assert updated_provision['name'] == update_data['name']
        
        # Supprimer la provision
        delete_response = requests.delete(
            f"{self.base_url}/provisions/{provision_id}",
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        
        assert delete_response.status_code == 200
    
    def test_error_handling(self):
        """Test de la gestion d'erreurs"""
        # Test 404 - Ressource non trouvée
        response = requests.get(
            f"{self.base_url}/provisions/999999",
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        assert response.status_code == 404
        
        # Test 401 - Token invalide
        response = requests.get(
            f"{self.base_url}/transactions",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        
        # Test 422 - Données invalides
        invalid_provision = {
            "name": "",  # Nom vide - invalide
            "percentage": -5  # Pourcentage négatif - invalide
        }
        
        response = requests.post(
            f"{self.base_url}/provisions",
            json=invalid_provision,
            headers={"Authorization": f"Bearer {self.client.token}"}
        )
        assert response.status_code == 422
    
    @pytest.mark.performance
    def test_api_performance(self):
        """Tests de performance"""
        import time
        
        # Test temps de réponse des transactions
        start_time = time.time()
        transactions = self.client.get_transactions(self.test_month)
        response_time = time.time() - start_time
        
        assert response_time < 2.0, f"Transaction query too slow: {response_time}s"
        
        # Test parallèle
        start_time = time.time()
        months = ["2024-01", "2024-02", "2024-03"]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self.client.get_transactions, month) 
                for month in months
            ]
            results = [future.result() for future in futures]
        
        parallel_time = time.time() - start_time
        assert parallel_time < 5.0, f"Parallel queries too slow: {parallel_time}s"

# Configuration pytest
def pytest_configure(config):
    """Configuration pytest avec markers personnalisés"""
    config.addinivalue_line(
        "markers", 
        "performance: marks tests as performance tests (deselect with '-m \"not performance\"')"
    )

# Exécution des tests
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",  # Verbose
        "--tb=short",  # Traceback court
        "-m", "not performance",  # Exclure les tests de performance par défaut
        "--durations=10"  # Afficher les 10 tests les plus lents
    ])
```

### Validation de Données

```python
from pydantic import BaseModel, validator, ValidationError
from typing import List, Optional
from datetime import datetime

class TransactionValidator(BaseModel):
    """Validateur pour les données de transaction"""
    date_op: str
    label: str
    amount: float
    category: Optional[str] = None
    is_expense: bool
    
    @validator('date_op')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
    
    @validator('label')
    def validate_label_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Label cannot be empty')
        return v.strip()
    
    @validator('amount')
    def validate_amount_reasonable(cls, v):
        if abs(v) > 1000000:  # 1 million
            raise ValueError('Amount seems unreasonable')
        return v

def validate_api_data():
    """Validation complète des données de l'API"""
    client = BudgetFamilleClient()
    client.authenticate("admin", "secret")
    
    print("🔍 Validation des données API...")
    
    # Récupérer les transactions
    transactions = client.get_transactions("2024-01")
    
    validation_results = {
        'total_transactions': len(transactions),
        'valid_transactions': 0,
        'invalid_transactions': 0,
        'errors': []
    }
    
    for tx in transactions:
        try:
            # Convertir is_expense en booléen si nécessaire
            tx_data = {
                'date_op': tx['date_op'],
                'label': tx['label'],
                'amount': tx['amount'],
                'category': tx.get('category'),
                'is_expense': bool(tx['is_expense'])
            }
            
            # Valider avec Pydantic
            validated_tx = TransactionValidator(**tx_data)
            validation_results['valid_transactions'] += 1
            
        except ValidationError as e:
            validation_results['invalid_transactions'] += 1
            validation_results['errors'].append({
                'transaction_id': tx.get('id'),
                'errors': [error['msg'] for error in e.errors()]
            })
    
    # Rapport de validation
    print(f"📊 Résultats de validation:")
    print(f"   Total: {validation_results['total_transactions']}")
    print(f"   ✅ Valides: {validation_results['valid_transactions']}")
    print(f"   ❌ Invalides: {validation_results['invalid_transactions']}")
    
    if validation_results['errors']:
        print(f"   🔍 Erreurs détaillées:")
        for error in validation_results['errors'][:5]:  # Limiter à 5 erreurs
            print(f"      TX {error['transaction_id']}: {', '.join(error['errors'])}")
    
    return validation_results

# Exécution de la validation
results = validate_api_data()
```

---

## 📞 Support et Ressources

### Liens Utiles

- **Documentation Interactive** : http://localhost:8000/docs
- **Schéma OpenAPI** : http://localhost:8000/openapi.json
- **Health Check** : http://localhost:8000/health
- **Collection Postman** : [Budget_Famille_API_v2.3.postman_collection.json](./Budget_Famille_API_v2.3.postman_collection.json)

### Exemples de Code

Tous les exemples de ce guide sont disponibles dans le dossier `docs/examples/` du projet :

```bash
docs/examples/
├── python/
│   ├── basic_client.py
│   ├── async_client.py
│   ├── robust_error_handling.py
│   └── performance_testing.py
├── javascript/
│   ├── basic_client.js
│   ├── typescript_sdk.ts
│   └── react_integration.jsx
└── curl/
    └── api_examples.sh
```

### Troubleshooting

#### Problèmes Courants

1. **Token expiré**
   ```bash
   # Symptôme: 401 Unauthorized
   # Solution: Renouveler l'authentification
   curl -X POST http://localhost:8000/token -d "username=admin&password=secret"
   ```

2. **Import CSV échoue**
   ```bash
   # Vérifier l'encodage du fichier
   file -bi mon_fichier.csv
   
   # Convertir si nécessaire
   iconv -f ISO-8859-1 -t UTF-8 mon_fichier.csv > mon_fichier_utf8.csv
   ```

3. **Réponses lentes**
   ```bash
   # Vérifier le cache Redis
   redis-cli ping
   
   # Nettoyer le cache si nécessaire
   redis-cli flushdb
   ```

### Contact et Support

Pour toute question ou problème :

1. **Vérifier d'abord** : http://localhost:8000/health
2. **Consulter les logs** : `tail -f backend/app.log`
3. **Tester avec Postman** : Utiliser la collection fournie
4. **Issues GitHub** : Créer un ticket avec les détails de reproduction

---

**Version Guide** : 2.3.0  
**Dernière mise à jour** : 2025-08-11  
**Compatibilité API** : v2.3.0+

---

*Ce guide est maintenu à jour avec les dernières fonctionnalités de l'API. Pour des cas d'usage spécifiques non couverts, n'hésitez pas à consulter la documentation interactive Swagger ou à contacter l'équipe de développement.*