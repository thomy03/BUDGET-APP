# API Provisions Personnalisables - Budget Famille

## Vue d'ensemble

L'API des provisions personnalisables permet aux utilisateurs de créer N provisions sur mesure avec des calculs flexibles et une répartition configurable entre les membres du couple.

## Endpoints Disponibles

### 1. Liste des provisions
**GET** `/provisions`

Récupère toutes les provisions de l'utilisateur connecté.

**Query Parameters:**
- `active_only` (bool, default: true) - Filtrer les provisions actives uniquement
- `category` (string, optional) - Filtrer par catégorie

**Exemple:**
```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/provisions?category=investment"
```

### 2. Créer une provision
**POST** `/provisions`

Crée une nouvelle provision personnalisable.

**Body (JSON):**
```json
{
  "name": "Investissement ETF",
  "description": "Épargne mensuelle pour investissements ETF",
  "percentage": 10.0,
  "base_calculation": "total",
  "split_mode": "key", 
  "icon": "📈",
  "color": "#22c55e",
  "category": "investment",
  "target_amount": 50000.0
}
```

**Champs disponibles:**
- `name` (string, requis) - Nom de la provision
- `description` (string, optional) - Description
- `percentage` (float, 0-100) - Pourcentage du revenu 
- `base_calculation` (enum) - Base de calcul: "total", "member1", "member2", "fixed"
- `fixed_amount` (float) - Montant fixe si base_calculation = "fixed"
- `split_mode` (enum) - Mode répartition: "key", "50/50", "100/0", "0/100", "custom"
- `split_member1` (float, 0-100) - Part membre 1 si mode = "custom"
- `split_member2` (float, 0-100) - Part membre 2 si mode = "custom"
- `icon` (string) - Emoji ou icône
- `color` (string) - Couleur hexadécimale
- `category` (enum) - Catégorie: "savings", "investment", "project", "custom"
- `target_amount` (float) - Objectif d'épargne
- `is_temporary` (bool) - Provision temporaire
- `start_date` (datetime) - Date de début
- `end_date` (datetime) - Date de fin

### 3. Détails d'une provision
**GET** `/provisions/{id}`

Récupère les détails d'une provision spécifique avec calculs.

### 4. Modifier une provision
**PUT** `/provisions/{id}`

Met à jour une provision existante. Tous les champs sont optionnels.

**Exemple:**
```json
{
  "percentage": 12.0,
  "current_amount": 5000.0
}
```

### 5. Supprimer une provision
**DELETE** `/provisions/{id}`

Supprime définitivement une provision.

### 6. Résumé des provisions
**GET** `/provisions/summary`

Récupère un résumé complet avec calculs et agrégations.

**Réponse:**
```json
{
  "total_provisions": 2,
  "active_provisions": 2,
  "total_monthly_amount": 355.0,
  "total_monthly_member1": 185.0,
  "total_monthly_member2": 170.0,
  "provisions_by_category": {
    "investment": 1,
    "savings": 1
  },
  "provisions_details": [...]
}
```

## Modes de Calcul

### Base de calcul (`base_calculation`)
- `"total"` - Sur la somme des revenus des deux membres
- `"member1"` - Sur le revenu du membre 1 uniquement  
- `"member2"` - Sur le revenu du membre 2 uniquement
- `"fixed"` - Montant fixe mensuel (utilise `fixed_amount`)

### Mode de répartition (`split_mode`)
- `"key"` - Selon la clé de répartition globale (proportionnel aux revenus)
- `"50/50"` - Répartition égale
- `"100/0"` - Tout sur le membre 1
- `"0/100"` - Tout sur le membre 2  
- `"custom"` - Répartition personnalisée (utilise `split_member1/2`)

## Intégration dans le Summary

Les provisions personnalisables sont automatiquement intégrées dans l'endpoint `/summary` existant:

```json
{
  "month": "2024-01",
  "vac_monthly_total": 377.92,
  "detail": {
    "Provision — 📈 Investissement ETF": {
      "TestUser1": 30.0,
      "TestUser2": 25.0
    },
    "Provision — 🏦 Épargne retraite": {
      "TestUser1": 300.0,
      "TestUser2": 0.0
    }
  }
}
```

## Sécurité

- Tous les endpoints requirent une authentification JWT
- Les provisions sont isolées par utilisateur (créées avec `created_by`)
- Validation stricte des données avec Pydantic
- Audit des actions de création/modification/suppression

## Catégories Disponibles

- `"savings"` - Épargne générale
- `"investment"` - Investissements
- `"project"` - Projets spéciaux
- `"custom"` - Catégorie personnalisée

## Exemples d'Usage

### Provision en pourcentage avec clé de répartition
```json
{
  "name": "Investissement ETF",
  "percentage": 10.0,
  "base_calculation": "total", 
  "split_mode": "key",
  "category": "investment"
}
```

### Provision à montant fixe
```json
{
  "name": "Épargne retraite",
  "base_calculation": "fixed",
  "fixed_amount": 300.0,
  "split_mode": "100/0",
  "category": "savings"
}
```

### Provision temporaire avec dates
```json
{
  "name": "Voyage Japon",
  "percentage": 5.0,
  "is_temporary": true,
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2026-06-30T23:59:59",
  "target_amount": 8000.0,
  "category": "project"
}
```

## Notes Techniques

- Migration automatique de la base de données au démarrage
- Support des indices optimisés pour les requêtes
- Calculs en temps réel à chaque appel API
- Progression calculée automatiquement si `target_amount` défini
- Ordre d'affichage configurable via `display_order`