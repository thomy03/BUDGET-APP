# PRD - Budget Famille v4.1
## Product Requirements Document

Document de specifications produit pour l'application de gestion budgetaire familiale Budget Famille v4.1.

---

## 1. Vue d'Ensemble Produit

### Vision Produit
Budget Famille v4.1 est une application web moderne qui **simplifie la gestion budgetaire familiale** grace a l'intelligence artificielle et une interface intuitive, permettant aux familles de **reprendre le controle de leurs finances** avec un suivi automatise, des predictions ML et des insights personnalises par IA.

### Mission
Transformer la gestion budgetaire en experience fluide et enrichissante, en automatisant 95% des taches repetitives tout en offrant une visibilite claire sur la sante financiere familiale avec des predictions intelligentes.

### Proposition de Valeur Unique
- **IA Auto-tagging** : 95.4% precision, categorisation automatique de toutes les transactions
- **Budget Intelligence System** : Predictions ML fin de mois, alertes intelligentes, analyse IA des ecarts
- **Dashboard Hierarchique** : Navigation intuitive du global au detail en 3 clics
- **Import Intelligent** : Traitement CSV/XLSX multi-banques avec detection automatique
- **Provisions Personnalisees** : Objectifs d'epargne flexibles avec repartition par membre

---

## 2. Analyse Marche et Utilisateurs

### Marche Cible

#### Segment Primaire : Familles Tech-Friendly (70%)
- **Profil** : Couples 28-45 ans, revenus combines 50k-120k EUR/an
- **Pain Points** : Manque de temps, complexite outils existants, pas de vision globale
- **Motivations** : Controle finances, epargne projets, education financiere enfants

#### Segment Secondaire : Freelances et Independants (30%)
- **Profil** : 25-40 ans, revenus variables, gestion pro/perso melangee
- **Pain Points** : Irregularite revenus, separation charges, provisions fiscales
- **Motivations** : Lissage revenus, optimisation fiscale, projections business

### Personas Principales

#### Marie & Julien - Famille Type
- **Contexte** : 2 enfants, double revenus, maison avec credit
- **Besoins** : Suivi mensuel simple, objectifs vacances/travaux
- **Usage** : 15min/semaine, principalement mobile le soir
- **Quote** : *"On veut juste savoir ou va notre argent sans y passer des heures"*

#### Sophie - Independante
- **Contexte** : Consultante, revenus irreguliers, charges deductibles
- **Besoins** : Lissage revenus, provisions charges sociales
- **Usage** : 1h/mois, desktop pour analyse detaillee
- **Quote** : *"J'ai besoin de prevoir mes charges meme quand les revenus varient"*

---

## 3. Fonctionnalites Produit

### 3.1 Core Features (Must-Have) - IMPLEMENTEES

#### CleanDashboard Provision-First
**Objectif** : Vue d'ensemble instantanee de la sante financiere
- **Design moderne** : 4 metriques cles avec animations CountUp
- **Barre progression** : Provisions avec indicateur temporel (X/12 mois), visuel vert
- **Repartition par membre** : Details provisions et depenses par personne
- **Quick Actions** : Navigation rapide vers fonctionnalites principales
- **Drill-down complet** : Depenses -> Variables/Fixes -> Tags -> Transactions -> Mois
- **Filtrage strict** : Montants debiteurs uniquement, exclusion transactions marquees

#### Budget Intelligence System v4.1
**Objectif** : Intelligence artificielle pour optimisation budgetaire
- **Objectifs Budget** : CRUD complet par categorie/tag avec suggestions historiques
- **Predictions ML** : Fin de mois par categorie avec tendances (increasing/decreasing/stable)
- **Alertes Intelligentes** : overspend_risk, unusual_spike, category_trend (3 severites)
- **Analyse IA Ecarts** : Integration OpenRouter (DeepSeek V3.2) pour explications
- **Detection Anomalies** : Isolation Forest + fuzzy matching doublons
- **Recommandations** : Suggestions d'economies personnalisees

#### Systeme de Tags ML
**Objectif** : Categorisation automatique intelligente
- **Auto-tagging** : Pattern matching (exact, first word, substring, similar)
- **Confiance adaptative** : 100% exact, 85% first word, 70% substring
- **Mode Batch** : Selection multiple avec raccourcis clavier (B, T, Shift+Click)
- **Preview suggestions** : Modal avec checkboxes avant application
- **Feedback ML** : Apprentissage continu des corrections utilisateur

#### Provisions Personnalisees
**Objectif** : Epargne objectifs flexibles et automatisees
- **Types** : Pourcentage revenus, montant fixe, formule personnalisee
- **Calculs** : Repartition couple, dates debut/fin, provisions temporaires
- **Suivi** : Barre progression verte avec montant cumule depuis janvier
- **Repartition membre** : Affichage detaille par personne dans dashboard
- **Categories** : Vacances, travaux, vehicule, urgence, projets enfants

### 3.2 Advanced Features (Should-Have) - IMPLEMENTEES

#### Analytics & Insights
**Objectif** : Comprehension comportements financiers
- **Drill-down hierarchique** : 5 niveaux de navigation
- **Tendances 6 mois** : AreaChart evolution revenus/depenses
- **Heatmap depenses** : Carte de chaleur par jour/heure
- **Top Categories/Marchands** : Classements automatiques

#### Page Analytics Onglets
- **Drilldown** : Navigation hierarchique depenses
- **Budget** : Analyse Budget vs Reel avec graphiques
- **IA** : Chat contextuel et suggestions economies

#### Configuration Avancee
**Objectif** : Adaptation tous profils familiaux
- **Multi-membres** : Repartition charges/revenus personnalisee
- **Taux imposition** : tax_rate1 et tax_rate2 individuels
- **Revenus nets** : Calcul automatique apres imposition
- **Objectifs budget** : Definition par categorie avec historique

### 3.3 Nice-to-Have Features (PLANIFIEES)

#### Collaboration Famille
- Comptes multiples, permissions granulaires
- Commentaires transactions, validations croisees
- Notifications objectifs partages

#### Integrations Externes
- APIs bancaires PSD2 (connexion directe)
- Export comptables (Ciel, Sage, Excel)
- Synchronisation calendriers (vacances, echeances)

#### Application Mobile
- React Native ou Expo
- PWA optimisee
- Notifications push

---

## 4. Exigences Techniques

### 4.1 Architecture Systeme

#### Backend Requirements
- **Framework** : FastAPI avec Pydantic (v1 syntax)
- **Base de donnees** : SQLite avec SQLAlchemy ORM
- **ML Pipeline** : Scikit-learn (Isolation Forest), patterns JSON
- **IA** : OpenRouter API (DeepSeek V3.2)
- **Cache** : Redis (aioredis compatible Python 3.11+)
- **APIs** : RESTful, documentation Swagger, JWT auth
- **Performance** : <2s temps reponse, 1000+ requetes/min

#### Frontend Requirements
- **Framework** : Next.js 14 avec App Router
- **Styling** : Tailwind CSS avec Dark Mode
- **Design System** : Glassmorphism (GlassCard, ModernCard)
- **Graphiques** : Recharts (PieChart, AreaChart, BarChart, LineChart)
- **State** : React Context + hooks personnalises
- **TypeScript** : Mode strict active
- **Tests** : Jest (136 tests passing)

#### Infrastructure Requirements
- **Containerisation** : Docker (developpement + production)
- **CI/CD** : GitHub Actions avec tests automatises
- **Deploiement** : Vercel (frontend) + Render (backend)
- **Monitoring** : Logs structures, metriques performance

### 4.2 Compatibilite et Support

#### Navigateurs
- **Desktop** : Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile** : iOS Safari 14+, Android Chrome 90+
- **PWA** : Installation native, fonctionnement offline

#### Systemes
- **Developpement** : Windows (PowerShell), macOS, Linux
- **Production** : Linux containers, cloud providers
- **Python** : 3.11+ (compatibilite aioredis)

---

## 5. Experience Utilisateur (UX)

### 5.1 Parcours Utilisateur Principal

#### Onboarding (Premier usage)
1. **Accueil** : Presentation valeur ajoutee, promesse "5 minutes setup"
2. **Configuration** : Revenus couple, taux imposition, objectifs epargne
3. **Import initial** : Assistant CSV, detection automatique colonnes
4. **Decouverte** : Tour guide interface, tips contextuels

#### Usage Recurrent (Hebdomadaire)
1. **Check rapide** : Dashboard, alertes predictions
2. **Transactions** : Validation auto-tagging, corrections avec feedback ML
3. **Objectifs** : Progression provisions, ajustements budgets
4. **Analyse IA** : Consultation recommandations, chat contextuel

### 5.2 Principes Design

#### Glassmorphism
- **Transparence** : Effets de verre avec blur
- **Dark Mode** : Theme complet avec toggle anime
- **Couleurs** : Gradients subtils, accents violet/bleu

#### Simplicite
- **Regle 3 clics** : Toute information accessible rapidement
- **Progressive disclosure** : Information complexe masquee par defaut
- **Defaults intelligents** : Configuration pre-remplie, suggestions ML

#### Performance Percue
- **Skeleton screens** : Chargement progressif
- **Animations CountUp** : Metriques animees
- **Cache intelligent** : Donnees frequentes en local

---

## 6. Modele de Donnees

### 6.1 Entites Principales

#### Transaction
```sql
- id, date_op, amount, label, account
- tags[], expense_type (FIXE/VARIABLE)
- exclude (boolean), month (YYYY-MM)
- ml_confidence_score, source
- created_at, updated_at, user_id
```

#### CustomProvision (Epargne)
```sql
- id, name, description, icon, color
- percentage, fixed_amount, base_calculation
- split_mode, split_member1, split_member2
- target_amount, current_amount, category
- is_active, is_temporary, start_date, end_date
```

#### CategoryBudget (NEW v4.0)
```sql
- id, user_id, category_name, tag_name
- budget_amount, month (YYYY-MM)
- is_active, created_at, updated_at
```

#### Config (Utilisateur)
```sql
- id, user_id, member1_name, member2_name
- member1_salary, member2_salary
- tax_rate1, tax_rate2 (taux imposition %)
- split_fixed_charges, split_variable_charges
```

### 6.2 Fichiers ML
- `backend/data/learned_patterns.json` : Patterns marchands appris
- `backend/ml_budget_predictor.py` : Predictions et alertes
- `backend/ml_anomaly_detector.py` : Detection anomalies

---

## 7. Securite et Conformite

### 7.1 Protection Donnees

#### Authentification
- **JWT Tokens** : Expiration automatique, refresh token
- **Securite mot de passe** : Hachage bcrypt
- **Session management** : Timeout inactivite

#### API Keys
- **OpenRouter** : Stockage securise .env
- **CORS** : Origins autorisees (localhost, 127.0.0.1)

### 7.2 Resilience

#### Backup
- **Scripts PowerShell** : Backup-Database.ps1
- **Strategie** : Daily/Weekly/Manual
- **Restore** : Restore-Database.ps1 avec rollback

---

## 8. Metriques et KPIs

### 8.1 Metriques Produit

#### Qualite ML
- **Auto-tagging accuracy** : >95% (actuel 95.4%)
- **Predictions accuracy** : >80% fin de mois
- **Alertes pertinence** : <10% faux positifs

#### Performance
- **API Response Time** : P95 <2s
- **Frontend FCP** : <3s
- **Tests coverage** : 136 tests Jest passing

### 8.2 Tests

#### Backend (pytest)
- Tests unitaires modeles
- Tests API endpoints
- Tests ML classification

#### Frontend (Jest)
- Tests composants React
- Tests hooks personnalises
- Tests utilitaires

---

## 9. Roadmap et Releases

### v4.1 (Janvier 2026) - ACTUELLE
- Dashboard repartition detaillee par membre
- Budget Intelligence System production-ready
- Tests complets (Jest + pytest)
- Orchestrator avec Skills Discovery
- Agents specialises (.claude/agents/)

### v4.2 (Fevrier 2026) - PLANIFIEE
- Application mobile (React Native/Expo)
- PWA optimisee avec notifications
- Export PDF automatise
- Ameliorations ML (transformers)

### v5.0 (Q2 2026) - VISION
- Integrations bancaires PSD2
- Multi-tenant complet
- WebSocket temps reel
- Assistant IA conversationnel

---

## 10. Risques et Mitigation

### Risques Techniques
- **Performance ML** : Monitoring continu, cache Redis
- **API timeouts** : Fallbacks, retry strategies
- **Compatibilite Python** : Tests multi-versions

### Risques Produit
- **Adoption** : Onboarding guide, documentation
- **Complexite** : Progressive disclosure, defaults intelligents

---

**Document Version** : 4.1.0
**Auteur** : Equipe Produit Budget Famille
**Derniere mise a jour** : 2026-01-25
**Prochaine revision** : 2026-02-28

*Ce PRD est un document evolutif, mis a jour en fonction des retours utilisateurs et de l'evolution du marche.*
