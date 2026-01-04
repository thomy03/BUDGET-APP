# 🎯 Proposition : Hiérarchie des Dépenses par Nature

**Date** : 05/11/2025
**Objectif** : Structurer les dépenses de manière intelligente et analytique

---

## 🐛 Problème Identifié : Calcul Incorrect des Tags

### Bug Actuel
```python
# Ligne 58 de backend/routers/tags.py
tag_data['total_amount'] += abs(tx.amount)  # ❌ PROBLÈME
```

**Conséquence** :
- Les **avoirs** (remboursements) sont comptés comme des **dépenses**
- Exemple : AVOIR Amazon +11.13€ est compté comme -11.13€
- Les totaux par tag sont **surévalués**

### Solution Proposée
```python
# Correction
if tx.amount < 0:
    # Dépense normale
    tag_data['total_amount'] += abs(tx.amount)
    tag_data['expense_count'] += 1
else:
    # Avoir/Remboursement - à soustraire
    tag_data['total_amount'] -= tx.amount
    tag_data['refund_count'] += 1
```

**Impact** :
- Tag "amazon" : Dépenses -100€ + Avoirs +30€ = **Net -70€** ✅
- Analyse plus précise du coût réel

---

## 📊 Proposition : Hiérarchie Intelligente des Dépenses

### Niveau 0 : Classification Fondamentale

```
TOUTES LES TRANSACTIONS
├─ 💰 REVENUS (amount > 0)
│   ├─ Salaires
│   ├─ Prestations sociales
│   ├─ Remboursements
│   └─ Autres revenus
│
└─ 💸 DÉPENSES (amount < 0)
    ├─ FIXES (récurrentes, prévisibles)
    ├─ VARIABLES (irrégulières)
    └─ EXCEPTIONNELLES (ponctuelles)
```

### Niveau 1 : Nature de la Dépense

```
DÉPENSES
├─ 🏠 LOGEMENT & HABITAT
│   Nature : Essentiel, Fixe
│   Compressibilité : Faible (0-10%)
│
├─ 🍔 ALIMENTATION
│   Nature : Essentiel, Variable
│   Compressibilité : Moyenne (10-30%)
│
├─ 🚗 TRANSPORT & MOBILITÉ
│   Nature : Essentiel, Variable
│   Compressibilité : Moyenne (15-40%)
│
├─ 💊 SANTÉ & BIEN-ÊTRE
│   Nature : Essentiel, Variable
│   Compressibilité : Faible (5-15%)
│
├─ 👕 HABILLEMENT
│   Nature : Semi-essentiel, Variable
│   Compressibilité : Élevée (30-70%)
│
├─ 🎮 LOISIRS & CULTURE
│   Nature : Discrétionnaire, Variable
│   Compressibilité : Très élevée (50-100%)
│
├─ 📱 COMMUNICATION & NUMÉRIQUE
│   Nature : Essentiel moderne, Fixe
│   Compressibilité : Moyenne (20-40%)
│
├─ 💰 ÉPARGNE & PLACEMENTS
│   Nature : Objectif, Fixe
│   Compressibilité : Variable selon revenus
│
├─ 🎓 ÉDUCATION & FORMATION
│   Nature : Investissement, Variable
│   Compressibilité : Faible (contexte dépendant)
│
└─ ⚡ EXCEPTIONNEL & IMPRÉVU
    Nature : Ponctuel
    Compressibilité : Non applicable
```

### Niveau 2 : Détail par Catégorie

#### 🏠 LOGEMENT & HABITAT
```
LOGEMENT
├─ FIXE (Incompressible)
│   ├─ Loyer / Crédit immobilier
│   ├─ Charges de copropriété
│   ├─ Assurance habitation
│   ├─ Taxe foncière
│   └─ Taxe d'habitation
│
└─ VARIABLE (Semi-compressible)
    ├─ Électricité
    ├─ Gaz / Chauffage
    ├─ Eau
    ├─ Internet & Box
    ├─ Travaux & Réparations
    ├─ Décoration & Aménagement
    └─ Bricolage & Jardinage
```

#### 🍔 ALIMENTATION
```
ALIMENTATION
├─ ESSENTIEL (Compressible 10-20%)
│   ├─ Courses supermarché
│   ├─ Courses bio / spécialisées
│   ├─ Boulangerie
│   └─ Marché
│
└─ PLAISIR (Compressible 50-100%)
    ├─ Restaurant midi
    ├─ Restaurant soir
    ├─ Livraison repas
    ├─ Fast-food
    ├─ Snacks & Gourmandises
    └─ Boissons (alcool, café)
```

#### 🚗 TRANSPORT & MOBILITÉ
```
TRANSPORT
├─ FIXE
│   ├─ Crédit auto / Leasing
│   ├─ Assurance auto
│   ├─ Abonnement transport
│   └─ Stationnement résident
│
└─ VARIABLE
    ├─ Essence / Carburant
    ├─ Péage autoroutier
    ├─ Parking ponctuel
    ├─ Train / Avion
    ├─ Taxi / VTC
    └─ Entretien véhicule
```

#### 💊 SANTÉ & BIEN-ÊTRE
```
SANTÉ
├─ ESSENTIEL
│   ├─ Mutuelle santé
│   ├─ Médecin généraliste
│   ├─ Pharmacie (ordonnance)
│   ├─ Dentiste
│   ├─ Optique
│   └─ Laboratoire analyses
│
└─ BIEN-ÊTRE
    ├─ Sport & Fitness
    ├─ Compléments alimentaires
    ├─ Parapharmacie
    ├─ Ostéopathe / Kiné
    └─ Relaxation / Spa
```

#### 🎮 LOISIRS & CULTURE
```
LOISIRS
├─ ABONNEMENTS FIXES
│   ├─ Streaming (Netflix, Disney+...)
│   ├─ Musique (Spotify...)
│   ├─ Presse / Magazines
│   └─ Clubs / Associations
│
└─ DÉPENSES VARIABLES
    ├─ Cinéma / Spectacles
    ├─ Livres / BD
    ├─ Jeux vidéo
    ├─ Hobbies
    ├─ Sorties nocturnes
    └─ Voyages & Vacances
```

---

## 🎯 Système de Scoring & Analyse

### Indicateurs par Nature de Dépense

#### 1. **Compressibilité** (0-100%)
```
Peut-on réduire cette dépense facilement ?

0-20%   : Incompressible (loyer, mutuelle)
20-40%  : Peu compressible (courses, essence)
40-60%  : Moyennement compressible (vêtements)
60-80%  : Très compressible (restaurants)
80-100% : Totalement optionnel (loisirs, sorties)
```

#### 2. **Essentialité** (1-5 étoiles)
```
À quel point cette dépense est-elle nécessaire ?

★★★★★ : Vital (logement, alimentation base)
★★★★☆ : Très important (santé, transport travail)
★★★☆☆ : Important (communication, éducation)
★★☆☆☆ : Confort (vêtements mode, loisirs réguliers)
★☆☆☆☆ : Luxe (restaurants fréquents, gadgets)
```

#### 3. **Récurrence** (Fixe/Variable/Ponctuel)
```
FIXE      : Même montant chaque mois (loyer, abonnements)
VARIABLE  : Montant fluctuant (courses, essence)
PONCTUEL  : Occurrence rare (électroménager, voyage)
```

#### 4. **Valeur Ajoutée** (Impact sur qualité de vie)
```
ÉLEVÉ    : Améliore significativement la vie
MOYEN    : Apporte du confort
FAIBLE   : Peu d'impact réel
NÉGATIF  : Dépense regrettée a posteriori
```

---

## 💡 Système de Tags Hiérarchiques Proposé

### Structure de Tag Recommandée

```yaml
Format : Nature/Catégorie/Détail/Contexte

Exemples:
  "ALIMENTATION/Courses/Supermarché/Hebdomadaire"
  "ALIMENTATION/Restaurant/Midi/Travail"
  "TRANSPORT/Essence/Voiture/Trajet-Travail"
  "LOGEMENT/Énergie/Électricité/Mensuel"
  "SANTÉ/Médecin/Généraliste/Enfant"
  "LOISIRS/Streaming/Netflix/Abonnement"
```

### Tags Spéciaux

```yaml
Métadonnées utiles:
  - "URGENT" : Dépense imprévue
  - "PLANIFIÉ" : Dépense anticipée
  - "REMBOURSÉ" : Sera remboursé (mutuelle, employeur)
  - "PARTAGÉ" : À diviser avec conjoint/coloc
  - "OBJECTIF-XXX" : Lié à un objectif (économie, projet)
  - "SAISON-XXX" : Dépense saisonnière (Noël, vacances)
```

---

## 📊 Tableaux de Bord Proposés

### Dashboard 1 : Vue par Nature (Matrice Importance/Compressibilité)

```
                    Compressibilité
                 Faible ←──────→ Élevée
               ┌──────────────────────────┐
      Élevée   │ LOGEMENT  │   ALIMENTATION│
               │ SANTÉ     │   HABILLEMENT │
Importance     ├───────────┼───────────────┤
               │ TRANSPORT │   LOISIRS     │
      Faible   │ NUMÉRIQUE │   GADGETS     │
               └──────────────────────────┘

Stratégie d'optimisation :
- Quadrant haut-gauche : Négocier (renégocier mutuelle, loyer)
- Quadrant haut-droite : Optimiser (manger moins au restaurant)
- Quadrant bas-gauche : Automatiser (abonnements groupés)
- Quadrant bas-droite : Réduire drastiquement
```

### Dashboard 2 : Évolution Temporelle par Nature

```
Graphique mensuel empilé :

€
│ ▓▓▓▓▓▓▓▓▓▓▓▓  Loisirs (optionnel)
│ ▒▒▒▒▒▒▒▒▒▒▒▒  Alimentation (semi-essentiel)
│ ░░░░░░░░░░░░  Logement (essentiel)
└─────────────────────────────────→ Mois
  Oct    Nov    Déc

Objectif : Stabiliser la zone essentielle, réduire l'optionnel
```

### Dashboard 3 : Top Postes d'Optimisation

```
Analyse automatique des dépenses optimisables :

1. 🍔 ALIMENTATION/Restaurant     -450€/mois
   Potentiel économie : -135€ (-30%)   ★★★★☆

2. 🎮 LOISIRS/Streaming           -85€/mois
   Potentiel économie : -35€ (-40%)    ★★★☆☆

3. 🚗 TRANSPORT/Essence            -280€/mois
   Potentiel économie : -56€ (-20%)    ★★★★☆
```

---

## 🔧 Implémentation Technique

### Modification Base de Données

```sql
-- Nouvelle table : expense_hierarchy
CREATE TABLE expense_natures (
    id INTEGER PRIMARY KEY,
    nature_code VARCHAR(50) UNIQUE,  -- Ex: "ALIMENTATION"
    parent_nature VARCHAR(50),       -- Hiérarchie
    compressibility INT,             -- 0-100
    essentiality INT,                -- 1-5 étoiles
    recurrence_type VARCHAR(20),     -- FIXE, VARIABLE, PONCTUEL
    icon_emoji VARCHAR(10),          -- 🍔
    color_hex VARCHAR(7),            -- #FF5733
    display_order INT
);

-- Lien tag → nature
CREATE TABLE tag_nature_mapping (
    tag_name VARCHAR(100),
    nature_code VARCHAR(50),
    confidence_score FLOAT,
    FOREIGN KEY (nature_code) REFERENCES expense_natures(nature_code)
);
```

### API Endpoints Nouveaux

```python
# Statistiques par nature
GET /analytics/by-nature?month=2025-10
Response:
{
  "ALIMENTATION": {
    "total": -850.50,
    "refunds": +30.00,
    "net": -820.50,
    "transactions_count": 45,
    "compressibility": 25,
    "essentiality": 5,
    "vs_last_month": +12.3,
    "subcategories": {
      "Courses": -600.00,
      "Restaurant": -220.50
    }
  }
}

# Suggestions d'économie
GET /analytics/optimization-suggestions
Response:
{
  "high_priority": [
    {
      "nature": "ALIMENTATION/Restaurant",
      "current_monthly": -450.00,
      "recommended_max": -300.00,
      "potential_saving": -150.00,
      "difficulty": "MEDIUM",
      "impact_score": 8.5
    }
  ]
}
```

---

## 🎨 Interface Utilisateur Proposée

### Sélecteur Hiérarchique de Tags

```
┌─────────────────────────────────────┐
│ 🏷️  Sélectionner une Nature        │
├─────────────────────────────────────┤
│ ▼ 🍔 ALIMENTATION                   │
│   ├─ □ Courses                      │
│   │   ├─ □ Supermarché             │
│   │   └─ □ Bio                     │
│   └─ □ Restaurant                   │
│       ├─ □ Midi                    │
│       └─ □ Soir                    │
│                                     │
│ ▼ 🏠 LOGEMENT                       │
│   ├─ □ Loyer                       │
│   └─ □ Charges                     │
│                                     │
│ ► 🚗 TRANSPORT                      │
│ ► 💊 SANTÉ                          │
└─────────────────────────────────────┘
```

---

## 🚀 Plan de Mise en Œuvre

### Phase 1 : Correction Bug Avoirs (Immédiat)
- [x] Identifier le problème (ligne 58 tags.py)
- [ ] Corriger le calcul : `amount` au lieu de `abs(amount)`
- [ ] Différencier dépenses et remboursements dans les stats
- [ ] Tester avec transactions octobre

### Phase 2 : Création Hiérarchie (1 semaine)
- [ ] Créer table `expense_natures`
- [ ] Peupler avec les 9 natures principales
- [ ] Créer API `/analytics/by-nature`
- [ ] Modifier frontend pour afficher par nature

### Phase 3 : Auto-Classification (2 semaines)
- [ ] ML pour détecter automatiquement la nature
- [ ] Système de scoring (compressibilité, essentialité)
- [ ] Suggestions d'optimisation automatiques

### Phase 4 : Dashboards Avancés (3 semaines)
- [ ] Matrice Importance/Compressibilité
- [ ] Graphiques d'évolution par nature
- [ ] Alertes budget par nature
- [ ] Export rapports personnalisés

---

## 📈 Bénéfices Attendus

### Analyse Plus Fine
- ✅ Vision claire : "Je dépense 35% en Alimentation"
- ✅ Comparaison : "Alimentation +12% vs mois dernier"
- ✅ Objectifs : "Réduire Restaurants de 30%"

### Optimisation Facilitée
- ✅ Priorisation : Focus sur postes compressibles
- ✅ Suggestions automatiques : "Économiser 150€/mois sur Restaurants"
- ✅ Gamification : Défis mensuels par nature

### Prise de Décision
- ✅ Budget prévisionnel par nature
- ✅ Alertes ciblées : "Budget Loisirs dépassé de 25%"
- ✅ Projections : "À ce rythme, -1,200€ de loisirs ce mois"

---

**Recommandation** : Commencer par la Phase 1 (correction bug) puis Phase 2 (hiérarchie de base). Les phases 3-4 peuvent être implémentées progressivement selon vos besoins.
