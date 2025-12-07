# CLAUDE.md - Budget Famille v3.2

Ce fichier fournit les instructions et le contexte pour Claude Code lors du travail sur ce projet.

## Vue d'ensemble du projet

Budget Famille v3.2 est une application web moderne de gestion budgetaire familiale avec :
- **Backend** : FastAPI + SQLite avec systeme ML avance d'auto-tagging
- **Frontend** : Next.js 14 + TypeScript + Tailwind CSS + Recharts
- **Design** : Glassmorphism UI avec Dark Mode complet
- **Fonctionnalites** : Import CSV, provisions personnalisees, depenses fixes, analytics IA avancee

## SESSION 07/12/2025 - AUTO-TAGGING FRONTEND + DRILL-DOWN AMELIORE

### Auto-Tagging Frontend (Page Transactions)

#### Nouvelles fonctionnalites implementees
1. **Bouton Auto-Tag** : Bouton violet dans l'en-tete de la page Transactions
   - Badge affichant le nombre de transactions non taguees
   - Ouvre un modal de preview des suggestions

2. **Modal de Preview Auto-Tag** :
   - Statistiques : total non tague, suggestions trouvees
   - Liste des suggestions avec checkbox pour selection
   - Affichage du type de match (exact, pattern, merchant, similar)
   - Score de confiance en pourcentage
   - Selection/Deselection de toutes les suggestions
   - Bouton "Appliquer" pour valider les tags selectionnes

3. **Types de suggestions** :
   - `exact` : Correspondance exacte du libelle
   - `pattern` : Correspondance par pattern ML
   - `merchant` : Correspondance par nom de marchand
   - `similar` : Correspondance par similarite

#### Implementation technique
```typescript
// Types API auto-tagging
export type AutoTagSuggestion = {
  transaction_id: number;
  label: string;
  suggested_tag: string;
  confidence: number;
  match_type: 'exact' | 'pattern' | 'merchant' | 'similar';
  source_label?: string;
};

// Preview des suggestions
const response = await autoTagApi.preview(month, 0.5);

// Application des tags selectionnes
for (const suggestionId of selectedSuggestions) {
  const suggestion = autoTagResult.suggestions.find(s => s.transaction_id === suggestionId);
  await autoTagApi.applyTag(suggestionId, suggestion.suggested_tag);
}
```

#### Fichiers modifies
- `frontend/lib/api.ts` : Ajout types et fonctions autoTagApi
- `frontend/app/transactions/page.tsx` : Bouton, modal et logique auto-tag

### Drill-Down Analytics Ameliore

#### Probleme resolu
- **Symptome** : Clic sur le graphique mensuel d'un tag ne filtrait pas les transactions par mois
- **Cause** : Le handler `handleCategoryMonthClick` existait mais le graphique dans la vue TAGS n'etait pas connecte

#### Solution implementee
1. **Nouvelle vue `category-month-transactions`** :
   - Affiche les transactions d'un tag pour un mois specifique
   - Breadcrumb complet : Categories > Categorie > Tag - Mois
   - Stats : Total du mois, nombre de transactions, moyenne/transaction
   - Liste des transactions filtrees par mois

2. **Graphiques mensuels par tag** :
   - Chaque tag dans la vue Categorie affiche maintenant un mini-graphique
   - Barres cliquables pour drill-down vers le mois specifique
   - Tooltip indiquant "Cliquez pour voir [mois]"

3. **Navigation amelioree** :
   - Flux : Categories → Tags (avec graphiques) → Clic sur barre → Transactions du mois
   - Bouton retour fonctionnel a chaque niveau
   - Breadcrumb interactif

#### Implementation technique
```typescript
// Nouveau type pour drill-down categorie-mois
type CategoryMonthData = {
  month: string;
  monthLabel: string;
  category: CategoryData;
  tag: TagData;
  transactions: Transaction[];
  total: number;
  count: number;
};

// Handler pour clic sur graphique mensuel d'un tag
const handleCategoryMonthClick = useCallback((data: any, tag: TagData) => {
  const monthStr = data.activePayload[0].payload.month;
  const monthTransactions = (tag.transactions || []).filter(tx => {
    const txMonth = tx.month || tx.date_op?.substring(0, 7);
    return txMonth === monthStr;
  });
  setSelectedCategoryMonth({ month: monthStr, monthLabel, category, tag, transactions: monthTransactions, ... });
  setDrillLevel('category-month-transactions');
}, [selectedCategory]);
```

#### Fichiers modifies
- `frontend/app/analytics/page.tsx` : Vue category-month-transactions, graphiques par tag

### Prochaine etape : Migration Mobile (Android/iOS)

#### Options identifiees
1. **React Native** : Reutilisation maximale du code TypeScript existant
2. **Expo** : Framework React Native avec tooling simplifie
3. **Capacitor** : Wrapper de l'app Next.js existante en app native
4. **PWA** : Progressive Web App (deja partiellement supporte)

## SESSION 06/12/2025 - DASHBOARD AMELIORE + GESTION CATEGORIES

### Gestion des Categories/Tags Interactive (06/12/2025)

#### Nouvelles fonctionnalites implementees
1. **Filtrage transactions exclues** : Le dashboard n'affiche plus les transactions marquees `exclude: true`
2. **Renommage/Fusion de tags** :
   - Bouton crayon sur chaque categorie pour renommer
   - Si le nouveau nom existe deja, les transactions sont fusionnees automatiquement
   - Modal avec confirmation et indication de fusion
3. **Drag & Drop transactions** :
   - Glisser une transaction vers une autre categorie pour la reaffecter
   - Indicateur visuel lors du survol d'une categorie cible
   - Mise a jour instantanee apres deplacement
4. **Suppression de categories vides** :
   - Bouton poubelle visible uniquement si la categorie est vide (0 transactions)
   - Les categories avec transactions sont protegees

#### Implementation technique
```typescript
// Filtrage des transactions non exclues
const expenseTransactions = transactions.filter((t: any) => t.amount < 0 && !t.exclude);

// Drag & drop avec API
await api.patch(`/transactions/${txId}/tags`, { tags: [toTag] });

// Renommage via API backend
await api.put(`/tags/${tagIndex + 1}`, { name: newTagName.trim().toLowerCase() });
```

#### Fichiers modifies
- `frontend/hooks/useCleanDashboard.ts` : Ajout filtre `!t.exclude`
- `frontend/components/dashboard/CleanDashboard.tsx` : Gestion tags, drag & drop, modals

### Dashboard Transactions Reelles (06/12/2025)

#### Probleme resolu
- **Symptome** : Dashboard affichait 55€ de depenses au lieu de ~5 400€
- **Cause** : Le hook `useCleanDashboard.ts` utilisait `summary.fixed_lines_total` et `summary.var_total` qui viennent de la table de configuration `fixed_lines`, PAS des vraies transactions importees

#### Solution implementee
1. **Chargement des transactions reelles** :
   ```typescript
   // Ajout de l'appel /transactions dans useCleanDashboard.ts
   const transactionsResponse = await api.get(`/transactions?month=${month}`)
   ```

2. **Calcul des depenses depuis les transactions** :
   ```typescript
   const expenseTransactions = transactions.filter((t: any) => t.amount < 0);
   const realExpensesTotal = expenseTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
   ```

3. **Nouvelles fonctionnalites ajoutees** :
   - **Graphique PieChart** : Repartition des depenses par categorie/tag
   - **Top Categories** : Liste triee des tags avec totaux et pourcentages
   - **Top 10 Marchands** : Extraction et classement automatique des marchands

#### Fichiers modifies
- `frontend/hooks/useCleanDashboard.ts` : Chargement transactions + calculs reels
- `frontend/components/dashboard/CleanDashboard.tsx` : Affichage graphique + listes

#### Import CSV - Colonne dateOp (05-06/12/2025)
- **Probleme** : Scripts precedents utilisaient la date du libelle au lieu de la colonne `dateOp`
- **Solution** : Toujours utiliser la colonne `dateOp` du CSV pour les dates
- **Format CSV** : La colonne `dateOp` contient les dates au format YYYY-MM-DD
- **Resultat** : 87 transactions novembre 2025 correctement importees

### Systeme ML d'Auto-Tagging Ameliore

#### Fonctionnalites implementees
1. **Import des tags existants** : Script `backend/scripts/import_existing_tags.py`
   - Importe automatiquement les transactions tagguees dans le systeme ML
   - Cree des patterns normalises pour chaque marchand
   - 45 patterns crees a partir de 71 transactions tagguees

2. **Pattern Matching Intelligent** :
   - **Exact match** : Correspondance exacte du nom marchand normalise
   - **First word match** : Correspondance sur le premier mot (ex: "franprix paris" -> "franprix")
   - **Substring match** : Correspondance partielle pour variantes

3. **Normalisation des noms de marchands** :
   - Suppression des prefixes bancaires (CARTE, CB, VIR, PRLV)
   - Suppression des dates (DD/MM/YY, DD/MM/YYYY)
   - Suppression des numeros de carte (CB*1234)
   - Extraction des 2 premiers mots significatifs

4. **Confiance adaptative** :
   - 100% pour match exact
   - 85% pour first word match
   - 70% pour substring match

#### Fichiers modifies
- `backend/services/ml_feedback_learning.py` : Ajout chargement patterns JSON
- `backend/scripts/import_existing_tags.py` : Script d'import des tags existants
- `backend/data/learned_patterns.json` : Stockage des patterns appris

#### Utilisation
```bash
# Importer les tags existants dans le systeme ML
cd backend && python scripts/import_existing_tags.py

# Redemarrer le backend pour charger les nouveaux patterns
python app.py
```

#### Test de l'API ML
```bash
curl -X POST http://localhost:8000/api/ml-classification/classify \
  -H "Content-Type: application/json" \
  -d '{"transaction_label": "CARTE FRANPRIX PARIS", "amount": 25.50}'

# Reponse attendue:
# {"suggested_tag": "courses", "confidence": 0.85, "source": "feedback", ...}
```

## SESSION 05/12/2025 - NOUVELLES FONCTIONNALITES

### Phase 3 - Dashboard Ameliore
- **Graphique AreaChart** : Evolution revenus/depenses sur 6 mois
- **API Trends** : Appel `/analytics/trends?months=last6`
- **Moyennes affichees** : Revenus, depenses et solde moyens
- **Gradients visuels** : Vert (revenus) et rouge (depenses)

### Phase 4 - ML Tagging Batch
- **Mode Batch** : Selection multiple avec checkboxes (touche B)
- **Shift+Click** : Selection de plage de transactions
- **Ctrl+A** : Selectionner toutes les transactions (en mode batch)
- **Modal Batch** : Appliquer tags a plusieurs transactions (touche T)
- **Tags Recents** : Quick access aux 5 derniers tags utilises
- **Raccourcis Clavier** :
  - `B` : Toggle mode batch
  - `T` : Ouvrir modal tagging (si selection)
  - `Escape` : Annuler/Fermer
  - `Enter` : Sauver tags
  - `?` : Afficher aide raccourcis

### Phase 5 - Analytics Avances
- **SpendingHeatMap** : Carte de chaleur des depenses par jour/heure
- **AnomaliesDetection** : Detection automatique des anomalies
- **Integration** : Composants ajoutes a l'onglet "Tendances"

### Phase 6 - Nettoyage
- **Pages supprimees** : dashboard-sota, dashboard-real, analytics-sota, settings-sota, upload-sota
- **Structure clarifiee** : Uniquement les pages principales conservees

## DEMARRAGE RAPIDE

### Application 100% Fonctionnelle avec Design Moderne

#### URLs de Production
- **Frontend (Vercel)** : https://budget-app-v2-bice.vercel.app
- **Backend (Render)** : https://budget-app-p8p9.onrender.com (utiliser local pour dev)
- **Documentation API** : http://localhost:8000/docs (local)

#### Developpement Local (PowerShell - Recommande)
```powershell
# Methode recommandee - Script unifie PowerShell
.\scripts\Start-BudgetApp.ps1

# Ou avec options
.\scripts\Start-BudgetApp.ps1 -Backend       # Backend uniquement
.\scripts\Start-BudgetApp.ps1 -Frontend      # Frontend uniquement
.\scripts\Start-BudgetApp.ps1 -NoBrowser     # Sans ouvrir le navigateur
```

#### Developpement Local (Methode manuelle)
```bash
# Backend (Terminal 1)
cd backend
python app.py
# API: http://localhost:8000

# Frontend (Terminal 2)
cd frontend
npm run dev
# App: http://localhost:3000
```

### Identifiants
- **Utilisateur** : admin
- **Mot de passe** : secret
- **Hash bcrypt** : $2b$12$N1BHKdi0fjTPgk3/aYYOCuBCjYY3hpq/7cmPnoMLXJ5wYafUpZP/u

## Architecture technique

### Structure
- **Port Frontend Next.js** : 3000 (npm run dev)
- **Port Backend** : 8000 (FastAPI)
- **Base de donnees** : SQLite (budget.db)
- **Authentification** : JWT avec utilisateurs en base

### Fonctionnalites cles implementees v3.1
1. **Dashboard Glassmorphism** avec design moderne, Dark Mode et graphiques Recharts
2. **Analytics avancee** : Vue d'ensemble, Details, Tendances avec graphiques interactifs
3. **Systeme Smart Tag ML** :
   - Mode batch avec raccourcis clavier
   - Auto-apply haute confiance
   - Import des tags existants
   - Pattern matching intelligent (first word, substring)
4. **Drill-down depenses hierarchique** : Depenses -> Variables/Fixes -> Tags -> Transactions
5. **Import CSV/XLSX** multi-mois avec detection automatique
6. **Provisions personnalisees** avec barre de progression et calculs automatiques
7. **Systeme fiscal complet** avec taux d'imposition et revenus nets

### Scripts PowerShell disponibles
- **Start-BudgetApp.ps1** : Lancement unifie backend + frontend
- **Backup-Database.ps1** : Backup automatique SQLite (daily/weekly/manual)
- **Restore-Database.ps1** : Restauration interactive avec rollback
- **Dev-Tools.ps1** : Utilitaires (clear-cache, check-ports, health, test-api)

## Standards de developpement

### Frontend
- **Framework** : Next.js 14 avec App Router
- **Styling** : Tailwind CSS avec Dark Mode (`darkMode: 'class'`)
- **Design System** : Glassmorphism avec GlassCard, ModernCard
- **Graphiques** : Recharts (PieChart, AreaChart, BarChart, LineChart)
- **TypeScript** strict active

### Backend
- **Framework** : FastAPI avec Pydantic v1 (important: ne pas utiliser v2 syntax)
- **Base de donnees** : SQLAlchemy ORM + SQLite
- **ML/IA** : Systeme de classification avance integre
- **API** : Endpoints RESTful documentes avec Swagger

### Outils de qualite
- **Tests** : Jest (frontend), pytest (backend)
- **Linting** : ESLint (frontend), ruff (backend)
- **Formatage** : Prettier (frontend), black (backend)

## Endpoints API ML

### Classification intelligente
```
POST /api/ml-classification/classify
{
  "transaction_label": "CARTE 05/12/25 FRANPRIX PARIS",
  "amount": 25.50,
  "include_alternatives": true
}

Response:
{
  "suggested_tag": "courses",
  "expense_type": "VARIABLE",
  "confidence": 0.85,
  "source": "feedback",
  "feedback_pattern_used": true,
  "merchant_name_clean": "franprix paris"
}
```

### Feedback ML
```
POST /api/ml-feedback/
{
  "transaction_id": 123,
  "original_tag": "divers",
  "corrected_tag": "courses",
  "feedback_type": "correction",
  "confidence_before": 0.5
}
```

## Structure des donnees

### Tables principales
- **transactions** : Donnees bancaires importees
- **custom_provisions** : Provisions personnalisees
- **fixed_lines** : Depenses fixes recurrentes
- **users** : Authentification utilisateurs
- **tag_mappings** : Systeme de tags IA
- **ml_feedback** : Historique des corrections ML
- **config** : Configuration utilisateur avec tax_rate1/tax_rate2

### Fichiers de patterns ML
- `backend/data/learned_patterns.json` : Patterns appris depuis les transactions tagguees

## Corrections et ameliorations recentes

### Session 2025-12-06 - Systeme ML Intelligent
- **Import tags existants** : Script pour importer 71 transactions tagguees -> 45 patterns
- **Chargement patterns JSON** : Service ML charge automatiquement les patterns au demarrage
- **Pattern matching ameliore** : First word match pour variantes de marchands
- **Normalisation corrigee** : Suppression dates, prefixes bancaires, numeros de carte

### Session 2025-12-05 - Corrections Import CSV et Dashboard
- **Import CSV** : Parsing dates corrige, synchronisation champ `month`
- **Dashboard** : Nouveau calcul "Repartition Famille" avec deficit compte
- **Scripts PowerShell** : Clean-Cache, Full-Reset, Fix-Venv, Kill-Ports
- **Compatibilite Python 3.13** : bcrypt 4.x, pydantic v2 validators

### Session 2025-12-04 - Refonte Design Moderne v3.0
- **Scripts PowerShell complets** : Start-BudgetApp.ps1, Backup-Database.ps1
- **Dark Mode active** : ThemeProvider dans layout.tsx avec toggle anime
- **Dashboard refait** : Design Glassmorphism avec GlassCard, graphiques Recharts
- **Analytics modernisee** : 3 vues (Overview, Details, Tendances)
- **Smart Tag ameliore** : Mode batch, raccourcis clavier, tags recents

## Commandes utiles

```bash
# Tests backend
cd backend && python -m pytest

# Tests frontend
cd frontend && npm test

# Import tags existants dans ML
cd backend && python scripts/import_existing_tags.py

# Verification API ML
curl -s http://localhost:8000/api/ml-classification/classify \
  -X POST -H "Content-Type: application/json" \
  -d '{"transaction_label": "AMAZON MARKETPLACE", "amount": 50}'
```

## Notes pour futures developpements

### Priorites identifiees
1. **Amelioration ML** : Ajouter plus de sources de patterns (regex, categories)
2. **Performance** : Cache Redis pour patterns ML frequents
3. **Mobile responsive** : Adapter interface pour smartphones
4. **Export** : PDF automatise des syntheses
5. **Integrations** : APIs bancaires PSD2

### Architecture future
- **Multi-tenant** : Support plusieurs utilisateurs
- **Real-time** : WebSocket pour updates live
- **ML avance** : Modele de classification transformer

---

**Version** : 3.2.0
**Derniere mise a jour** : 2025-12-07
**Statut** : Application 100% fonctionnelle - Auto-tagging frontend + Drill-down analytics ameliore
**Note** : Backend Render disponible, developpement local recommande pour tests
**Prochaine etape** : Migration mobile Android/iOS
