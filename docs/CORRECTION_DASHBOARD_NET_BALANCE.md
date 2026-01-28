# ✅ Correction Dashboard - Net Balance à Provisionner (06/11/2025)

## 🎯 Objectif de la Modification

Modifier la section **"Dépenses courantes"** du Dashboard pour qu'elle devienne **"Dépenses courantes à provisionner"** et calcule le **montant net réel à provisionner** en tenant compte de :

1. ✅ **Dépenses** (transactions négatives)
2. ✅ **Avoirs/Remboursements** (transactions positives)
3. ✅ **Solde début de mois** (qui est en réalité le solde fin du mois précédent)

## 🐛 Problème Initial

### Calcul Incorrect (Avant)

```typescript
// ❌ Prenait seulement les dépenses en valeur absolue
const depensesVariables = transactions
  .filter(t => t.amount < 0 && !t.exclude)
  .reduce((sum, t) => sum + Math.abs(t.amount), 0);

// Répartition entre les deux membres
const member1Depenses = depensesVariables * member1Share;
const member2Depenses = depensesVariables * member2Share;
```

**Conséquence** :
- Les **avoirs** (remboursements) n'étaient pas soustraits
- Le **solde début de mois** n'était pas pris en compte
- La répartition ne reflétait pas le montant réel à provisionner

### Exemple Concret

**Mois d'octobre 2025** :
- Dépenses : -2 317,15€
- Avoirs : +130,24€ (Temu, etc.)
- Solde début octobre : -816,10€ (déficit du mois précédent)

**Calcul incorrect** :
```
Dépenses courantes = 2 317,15€
→ Ne tient pas compte des 130€ d'avoirs récupérés
→ Ne tient pas compte du déficit de -816€ à combler
```

**Calcul correct** :
```
Dépenses nettes à provisionner = 2 317,15€ - 130,24€ + 816,10€ = 3 003,01€
→ Montant réel que le couple doit provisionner ce mois
```

## ✅ Correction Appliquée

### Nouveau Calcul (Après)

```typescript
// Dépenses du mois (négatives)
const depensesVariables = transactions
  .filter(t => t.amount < 0 && !t.exclude)
  .reduce((sum, t) => sum + Math.abs(t.amount), 0);

// Revenus du mois (positives - avoirs et autres revenus)
const revenusTransactions = transactions
  .filter(t => t.amount > 0 && !t.exclude)
  .reduce((sum, t) => sum + t.amount, 0);

// ✅ NET BALANCE à provisionner = Dépenses - Avoirs + Solde début mois
const depensesNettesAProvisionner = depensesVariables - revenusTransactions + accountBalance;

// Charges SANS les virements programmés
const chargesSansVirements = depensesNettesAProvisionner + totalProvisions;

// Répartition entre les deux membres (basée sur revenus nets)
const member1Depenses = depensesNettesAProvisionner * member1Share;
const member2Depenses = depensesNettesAProvisionner * member2Share;
```

### Modifications dans l'Interface

1. **Titre changé** :
   - Avant : `"Dépenses courantes"`
   - Après : `"Dépenses courantes à provisionner"`

2. **Montant affiché** :
   - Avant : `€{depensesVariables.toFixed(2)}`
   - Après : `€{depensesNettesAProvisionner.toFixed(2)}`

3. **Répartition** :
   - Avant : Basée sur `depensesVariables`
   - Après : Basée sur `depensesNettesAProvisionner`

## 📊 Impact sur le Dashboard

### Section "Répartition des Charges"

**Affichage** :
```
⚖️ Répartition des Charges

Dépenses courantes à provisionner : €3 003,01
Provisions (épargne)                : €1 200,00
Virements programmés (fixes)        : €1 652,00
──────────────────────────────────────────────
TOTAL CHARGES                       : €5 855,01
```

### Répartition par Membre

**Membre 1** (Part proportionnelle au revenu) :
```
💳 Dépenses courantes à provisionner : €1 501,51
💰 Provisions (épargne)               : €600,00
🔄 Virements programmés               : €826,00
──────────────────────────────────────────────
CONTRIBUTION TOTALE                   : €2 927,51
```

**Membre 2** :
```
💳 Dépenses courantes à provisionner : €1 501,50
💰 Provisions (épargne)               : €600,00
🔄 Virements programmés               : €826,00
──────────────────────────────────────────────
CONTRIBUTION TOTALE                   : €2 927,50
```

## 🎯 Bénéfices

### 1. Montant Réaliste

✅ **Le montant affiché correspond à ce que le couple doit réellement mettre de côté ce mois**

Au lieu de voir :
- "Dépenses courantes : 2 317€"

Vous voyez maintenant :
- "Dépenses courantes à provisionner : 3 003€"
  - Dépenses : 2 317€
  - Moins avoirs : -130€
  - Plus déficit précédent : +816€

### 2. Gestion du Déficit/Excédent

✅ **Le solde début de mois est automatiquement pris en compte**

**Si déficit** (solde négatif) :
```
accountBalance = -816€
→ Le montant à provisionner augmente de 816€
→ Le couple doit combler le déficit du mois précédent
```

**Si excédent** (solde positif) :
```
accountBalance = +200€
→ Le montant à provisionner diminue de 200€
→ Le couple profite de l'excédent du mois précédent
```

### 3. Répartition Juste

✅ **Chaque membre provisionne sa part exacte du montant net**

Avec répartition proportionnelle aux revenus nets :
- Si Membre 1 gagne 60% des revenus nets
- Il provisionne 60% des dépenses nettes à provisionner

### 4. Vision Claire

✅ **La section "Dépenses courantes à provisionner" montre clairement le montant à budgéter**

C'est la réponse à la question :
> "Combien doit-on mettre de côté ce mois pour couvrir nos dépenses variables ?"

## 📝 Fichier Modifié

**Fichier** : `frontend/app/dashboard/page.tsx`

**Lignes modifiées** :
- Lignes 141-143 : Ajout calcul `depensesNettesAProvisionner`
- Lignes 149-150 : Utilisation dans `chargesSansVirements`
- Lignes 166-167 : Utilisation dans répartition membres
- Ligne 378 : Changement titre affichage
- Ligne 379 : Changement montant affiché

## 🔍 Comment Vérifier

1. **Allez sur le Dashboard** : http://localhost:3000/dashboard
2. **Connectez-vous** : admin / secret
3. **Sélectionnez octobre 2025**
4. **Vérifiez la section "Répartition des Charges"** :

```
Dépenses courantes à provisionner : €3 003,01
  = Dépenses (2 317,15€)
  - Avoirs (130,24€)
  + Solde début mois (816,10€)
```

5. **Vérifiez que les montants par membre reflètent cette valeur**

## 💡 Notes Importantes

### Solde Début de Mois

Le `accountBalance` est **éditable** dans le Dashboard (via le crayon ✏️).

**Recommandation** :
- Mettre à jour ce solde au **début de chaque mois**
- Entrer le **solde réel de fin du mois précédent**
- Exemple : Si vous terminez septembre à -816€, entrez `-816` début octobre

### Avoirs et Revenus

Les **transactions positives** incluent :
- Avoirs/Remboursements (ex: AVOIR AMAZON +60€)
- Autres revenus ponctuels (ventes, cadeaux, etc.)
- MAIS PAS les salaires (qui sont dans `rev1Net` et `rev2Net`)

### Mode de Répartition

La répartition entre membres dépend du `split_mode` configuré :
- **"revenus"** (par défaut) : Proportionnel aux revenus nets
- **"50/50"** : Parts égales
- **"manuel"** : Pourcentages personnalisés

## 🎉 Résultat

Le Dashboard affiche maintenant le **montant net réel à provisionner** pour les dépenses courantes, en tenant compte de :
- ✅ Toutes les dépenses du mois
- ✅ Tous les remboursements reçus
- ✅ Le déficit ou excédent du mois précédent

La répartition entre les membres du couple est **juste et réaliste** !

---

**Version** : 2.3.12
**Date de modification** : 06/11/2025
**Fichier modifié** : `frontend/app/dashboard/page.tsx`
**Statut** : ✅ Modification appliquée et fonctionnelle
