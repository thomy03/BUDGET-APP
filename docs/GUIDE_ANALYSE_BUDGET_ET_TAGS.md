# 📊 Guide Complet : Analyse Budget & Système de Tags Intelligents

**Date** : 05/11/2025
**Version** : 2.3
**Statut** : Guide Utilisateur

---

## 🎯 Réponse à Votre Question

### ❓ "Est-ce que les tags seront appliqués automatiquement aux futures transactions ?"

**✅ OUI !** Votre application dispose d'un **système ML (Machine Learning)** qui apprend de vos actions :

1. **Vous taguez une transaction** → Le système enregistre le pattern
2. **Transaction similaire arrive** → Le tag est suggéré automatiquement
3. **Plus vous taguez** → Plus le système devient précis

---

## 🧠 Comment Fonctionne le Système ML

### 1️⃣ Apprentissage Automatique (`label_tag_mappings`)

Quand vous taguez une transaction :
- Le système **analyse le libellé** (ex: "CARTE 30/10 MC DONALD'S")
- Crée un **pattern de reconnaissance** (ex: "MC DONALD")
- **Associe le tag** (ex: "Restaurant", "FastFood")
- **Calcule la confiance** basée sur votre historique

### 2️⃣ Auto-Suggestion sur Nouvelles Transactions

```
Exemple concret :
─────────────────────────────────────────────────────
Vous taguez : "CARTE 15/10 MC DONALD'S" → "Restaurant, FastFood"

Le mois suivant : "CARTE 12/11 MC DONALD'S" arrive
                  ↓
                  Le système suggère automatiquement : "Restaurant, FastFood"
                  ↓
                  Vous validez ou modifiez
                  ↓
                  Le système améliore sa confiance
```

### 3️⃣ Services ML Disponibles

Votre backend a **11 services ML** :
- `ml_tagging_engine.py` - Moteur principal de tagging
- `enhanced_ml_learning.py` - Apprentissage renforcé
- `ml_feedback_learning.py` - Feedback utilisateur
- `intelligent_tag_service.py` - Suggestions intelligentes
- `contextual_auto_tagging.py` - Tagging contextuel
- Et 6 autres services spécialisés

---

## 📈 Comment Analyser Efficacement Votre Budget

### Stratégie de Tagging Recommandée

#### **Niveau 1 : Catégories Principales** (Obligatoire)
```
🏠 Logement          → Loyer, Charges, Eau, Électricité, Gaz
🍔 Alimentation      → Courses, Restaurant, Livraison
🚗 Transport         → Essence, Péage, Transport public, Parking
💊 Santé             → Médecin, Pharmacie, Mutuelle
👕 Vêtements         → Habits, Chaussures
🎮 Loisirs           → Sorties, Abonnements, Streaming
💰 Épargne           → Virement épargne
```

#### **Niveau 2 : Sous-Catégories** (Recommandé)
```
Alimentation :
  ├─ Courses-Bio
  ├─ Courses-Supermarché
  ├─ Restaurant-Midi
  ├─ Restaurant-Soir
  └─ Livraison-Food

Transport :
  ├─ Essence
  ├─ Parking
  ├─ Métro
  └─ Train
```

#### **Niveau 3 : Tags Spécifiques** (Optionnel)
```
🎯 Objectifs : "Économie", "Budget-Serré", "Dépense-Prévue"
📅 Périodes : "Vacances", "Rentrée", "Noël"
👥 Personne : "Perso", "Conjoint", "Enfants"
```

---

## 🛠️ Actions Pratiques Immédiates

### ✅ Étape 1 : Tagguer vos Transactions Actuelles (Octobre)

**Pourquoi ?** Créer la base d'apprentissage ML

**Comment ?**
1. Allez sur `/transactions`
2. Sélectionnez **Octobre 2025**
3. Pour chaque transaction récurrente, ajoutez des tags :
   ```
   PERSPECTIVE BIO    → Alimentation, Courses, Bio
   MC DONALD'S        → Alimentation, Restaurant, FastFood
   E.LECLERC          → Alimentation, Courses, Supermarché
   AMZN Mktp FR       → Shopping, Amazon, En-ligne
   PHARMACIE FOCH     → Santé, Pharmacie
   ```

4. **Concentrez-vous sur les marchands récurrents** en priorité

### ✅ Étape 2 : Tester l'Auto-Tagging

1. Importez les transactions de **Novembre**
2. Vérifiez que les tags sont **suggérés automatiquement**
3. Validez ou corrigez les suggestions
4. Le système apprend de vos corrections

### ✅ Étape 3 : Créer des Vues d'Analyse

#### Dans Settings (Page Paramètres)

**A. Définir vos Tags Standards**
```sql
Catégories fixes :
├─ Logement (fixe mensuel)
├─ Alimentation (variable)
├─ Transport (variable)
├─ Santé (variable)
├─ Loisirs (variable)
└─ Épargne (fixe mensuel)
```

**B. Créer des Provisions Personnalisées**
```
Exemple :
- Nom : "Budget Alimentation"
- Montant mensuel : 800€
- Catégorie : Alimentation
- Actif : Oui
```

---

## 📊 Analyses Disponibles

### 1. Page Dashboard (http://localhost:3000/dashboard)

**Métriques Clés** :
- **Solde disponible** après provisions
- **Provisions actives** (mensuelles/annuelles)
- **Dépenses variables vs fixes**
- **Transactions récentes**

**Drill-Down** :
```
Dépenses Totales
  ├─ Dépenses Variables (cliquable)
  │    ├─ Alimentation (cliquable)
  │    │    ├─ Courses
  │    │    └─ Restaurant
  │    └─ Transport
  └─ Dépenses Fixes
       ├─ Loyer
       └─ Charges
```

### 2. Page Transactions (http://localhost:3000/transactions)

**Fonctionnalités** :
- ✅ Filtrage par période (MonthPicker)
- ✅ Recherche par libellé
- ✅ Filtrage par type (Revenus/Dépenses)
- ✅ Tri par montant/date
- ✅ Édition tags en ligne
- ✅ Statistiques en temps réel

**Statistiques Affichées** :
```
Total Transactions : 116
Dépenses : -2,330.50€
Revenus : +500.00€
Solde Net : -1,830.50€
```

### 3. Page Analytics (http://localhost:3000/analytics-sota)

**Graphiques Disponibles** :
- 📊 **Évolution mensuelle** : Tendance dépenses/revenus
- 🥧 **Répartition par catégorie** : Camembert interactif
- 📈 **Top 10 Marchands** : Classement par montant
- 📉 **Anomalies détectées** : Dépenses inhabituelles

---

## 🎯 Suggestions Avancées

### 1. **Créer des Règles de Budget**

**Exemple pratique** :
```python
Règle : "Alerte si Alimentation > 800€/mois"

1. Taguez toutes les transactions "Alimentation"
2. Dans Settings, créez une provision "Budget Alimentation" : 800€
3. Le dashboard affiche automatiquement :
   - Consommé : 650€ / 800€ (81%)
   - Restant : 150€
   - Statut : ✅ Dans le budget
```

### 2. **Analyser les Patterns de Dépenses**

**Questions à se poser** :
```
🔍 Quels jours dépensez-vous le plus ?
   → Filtrer par jour de la semaine

🔍 Quel est votre plus gros poste de dépense ?
   → Analytics → Répartition par catégorie

🔍 Où pouvez-vous économiser ?
   → Comparer mois par mois les catégories variables

🔍 Y a-t-il des dépenses récurrentes à optimiser ?
   → Rechercher les abonnements et services
```

### 3. **Automatiser le Tagging par Règles**

**Créez des règles intelligentes** :
```javascript
Règle 1 : Si libellé contient "CARTE" ET "FRANPRIX" → Tags : "Alimentation, Courses, Proximité"
Règle 2 : Si libellé contient "VIR" ET montant > 0 → Tags : "Revenu, Virement"
Règle 3 : Si libellé contient "PRLV SEPA" → Tags : "Prélèvement, Abonnement"
Règle 4 : Si montant < -100€ → Tag : "Grosse-Dépense"
```

### 4. **Suivi Objectifs Financiers**

**Exemple d'objectifs** :
```
🎯 Objectif 1 : Réduire Restaurant de 20%
   - Octobre : 450€
   - Objectif Novembre : 360€
   - Suivi : Filtrer tag "Restaurant" chaque mois

🎯 Objectif 2 : Épargner 500€/mois
   - Créer provision "Épargne" : 500€
   - Virement automatique le 1er du mois
   - Tag : "Épargne"

🎯 Objectif 3 : Budget Courses < 600€
   - Tags : "Alimentation, Courses"
   - Provision : 600€/mois
   - Alert si dépassement
```

---

## 💡 Autres Pistes d'Analyse

### A. Export et Visualisations Externes

**Vous pouvez exporter vos données** :
```bash
# Export CSV avec tags
GET /export/transactions?month=2025-10&include_tags=true

# Import dans Excel/Google Sheets pour :
- Tableaux croisés dynamiques
- Graphiques personnalisés
- Prévisions (tendances)
```

### B. Comparaisons Multi-Mois

**Tableau de bord comparatif** :
```
                Oct 2025    Nov 2025    Évolution
─────────────────────────────────────────────────
Alimentation     -650€       -720€      +10.7% ⚠️
Transport        -180€       -150€      -16.7% ✅
Loisirs          -320€       -280€      -12.5% ✅
TOTAL          -1,150€     -1,150€       0.0%
```

### C. Détection Anomalies

**Le système peut détecter** :
- Dépenses inhabituellement élevées
- Doublons de transaction
- Abonnements oubliés
- Pics de dépenses

### D. Prévisions Budgétaires

**Basé sur l'historique** :
```
Prévision Décembre 2025 :
- Alimentation : ~650€ (moyenne 3 derniers mois)
- Transport : ~165€
- Loisirs : ~300€
+ Primes de Noël : +200€
= Budget prévu : -915€
```

---

## 🔧 Configuration Recommandée

### Tags de Base à Créer Maintenant

```yaml
Catégories Essentielles:
  - Alimentation: ["Courses", "Restaurant", "Livraison"]
  - Logement: ["Loyer", "Charges", "Eau", "Électricité", "Internet"]
  - Transport: ["Essence", "Parking", "Métro", "Train"]
  - Santé: ["Médecin", "Pharmacie", "Mutuelle"]
  - Loisirs: ["Sport", "Sorties", "Streaming", "Jeux"]
  - Épargne: ["Virement-Épargne", "Placement"]

Tags Spéciaux:
  - "Essentiel": Dépenses incompressibles
  - "Discrétionnaire": Dépenses évitables
  - "Exceptionnel": Dépenses ponctuelles
  - "Récurrent": Abonnements mensuels
```

---

## 📝 Plan d'Action Immédiat

### Semaine 1 : Mise en Place
- [ ] Tagguer toutes les transactions d'Octobre
- [ ] Identifier les 10 marchands les plus fréquents
- [ ] Créer 5-7 catégories principales
- [ ] Créer 3 provisions (Alimentation, Transport, Loisirs)

### Semaine 2 : Affinage
- [ ] Importer Novembre et valider les suggestions ML
- [ ] Ajuster les tags si nécessaire
- [ ] Créer des sous-catégories utiles
- [ ] Définir un budget pour chaque catégorie

### Semaine 3 : Analyse
- [ ] Comparer Octobre vs Novembre
- [ ] Identifier les postes à optimiser
- [ ] Définir 2-3 objectifs d'économie
- [ ] Créer des règles de budget

### Mois 2 : Automatisation
- [ ] Le système suggère automatiquement 80%+ des tags
- [ ] Vous ne validez/corrigez que 20%
- [ ] Analyse mensuelle automatisée
- [ ] Alertes budget configurées

---

## 🎉 Résultats Attendus

**Après 3 mois d'utilisation** :
- ✅ **95% des transactions auto-taguées** par le ML
- ✅ **Vision claire** de vos postes de dépenses
- ✅ **Économies identifiées** : 10-20% sur dépenses variables
- ✅ **Budgets respectés** grâce aux provisions
- ✅ **Temps gagné** : 5 min/mois vs 1h sans automatisation

---

## 💬 Questions Fréquentes

**Q: Combien de temps pour que le ML soit efficace ?**
R: 20-30 transactions taguées par catégorie suffisent. Après 1 mois, il sera déjà très précis.

**Q: Que se passe-t-il si je change un tag suggéré ?**
R: Le système apprend de votre correction et améliore ses futures suggestions.

**Q: Puis-je avoir plusieurs tags par transaction ?**
R: Oui ! Ex: "Alimentation, Courses, Bio" - Séparez par des virgules.

**Q: Les tags sont-ils partagés entre utilisateurs ?**
R: Non, chaque compte a son propre modèle ML personnalisé.

**Q: Comment supprimer un mauvais pattern ?**
R: Via Settings → Tags Management, vous pouvez désactiver ou supprimer des mappings.

---

## 📚 Documentation Technique

### Tables de Données

**`label_tag_mappings`** - Apprentissage ML
```sql
label_pattern      : "MC DONALD"
suggested_tags     : "Restaurant,FastFood"
confidence_score   : 0.95
usage_count        : 12
success_rate       : 0.92
last_used          : 2025-11-05
```

**`transactions`** - Données brutes
```sql
id         : 1234
label      : "CARTE 30/10 MC DONALD'S"
amount     : -28.09
tags       : "Restaurant,FastFood,Midi"
month      : "2025-10"
```

### API Endpoints Utiles

```bash
# Liste tous les tags avec stats
GET /tags

# Suggestions pour une transaction
POST /tags/suggest
Body: { "label": "CARTE MC DONALD'S", "amount": -25 }

# Stats par catégorie
GET /tags/stats?month=2025-10

# Patterns ML appris
GET /tags/patterns
```

---

**Prochaine étape recommandée** : Commencez par tagguer vos 20 transactions les plus récurrentes d'octobre. Le système commencera à apprendre dès maintenant ! 🚀
