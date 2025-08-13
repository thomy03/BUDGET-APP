# PRD - Budget Famille v2.3
## Product Requirements Document

Document de spécifications produit pour l'application de gestion budgétaire familiale Budget Famille v2.3.

---

## 1. Vue d'Ensemble Produit

### Vision Produit
Budget Famille v2.3 est une application web moderne qui **simplifie la gestion budgétaire familiale** grâce à l'intelligence artificielle et une interface intuitive, permettant aux familles de **reprendre le contrôle de leurs finances** avec un suivi automatisé et des insights personnalisés.

### Mission
Transformer la corvée budgétaire en expérience fluide et enrichissante, en automatisant 95% des tâches répétitives tout en offrant une visibilité claire sur la santé financière familiale.

### Proposition de Valeur Unique
- **IA Auto-tagging** : 95.4% précision, catégorisation automatique de toutes les transactions
- **Dashboard Hiérarchique** : Navigation intuitive du global au détail en 3 clics
- **Import Intelligent** : Traitement CSV/XLSX multi-banques avec détection automatique
- **Provisions Personnalisées** : Objectifs d'épargne flexibles avec calculs automatiques

---

## 2. Analyse Marché et Utilisateurs

### Marché Cible

#### Segment Primaire : Familles Tech-Friendly (70%)
- **Profil** : Couples 28-45 ans, revenus combinés 50k-120k€/an
- **Pain Points** : Manque de temps, complexité outils existants, pas de vision globale
- **Motivations** : Contrôle finances, épargne projets, éducation financière enfants

#### Segment Secondaire : Freelances et Indépendants (30%)
- **Profil** : 25-40 ans, revenus variables, gestion pro/perso mélangée
- **Pain Points** : Irrégularité revenus, séparation charges, provisions fiscales
- **Motivations** : Lissage revenus, optimisation fiscale, projections business

### Personas Principales

#### Marie & Julien - Famille Type
- **Contexte** : 2 enfants, double revenus, maison avec crédit
- **Besoins** : Suivi mensuel simple, objectifs vacances/travaux
- **Usage** : 15min/semaine, principalement mobile le soir
- **Quote** : *"On veut juste savoir où va notre argent sans y passer des heures"*

#### Sophie - Indépendante
- **Contexte** : Consultante, revenus irréguliers, charges déductibles
- **Besoins** : Lissage revenus, provisions charges sociales
- **Usage** : 1h/mois, desktop pour analyse détaillée
- **Quote** : *"J'ai besoin de prévoir mes charges même quand les revenus varient"*

---

## 3. Fonctionnalités Produit

### 3.1 Core Features (Must-Have)

#### CleanDashboard Provision-First ✅ IMPLÉMENTÉ
**Objectif** : Vue d'ensemble instantanée de la santé financière
- **Design moderne** : 4 métriques clés avec animations CountUp
- **Barre progression** : Provisions avec indicateur temporel (X/12 mois), visuel vert
- **Calcul familial** : (Provisions + Dépenses - Solde compte) / revenus nets
- **Quick Actions** : Navigation rapide vers fonctionnalités principales
- **Drill-down complet** : Dépenses → Variables/Fixes → Tags → Transactions
- **Filtrage strict** : Montants débiteurs uniquement, exclusion transactions marquées

#### Système de Tags Simplifié
**Objectif** : Édition directe sans interruption
- **Création automatique** : Nouveaux tags via TagAutomationService
- **Workflow direct** : Modification immédiate sans modal
- **Détection intelligente** : Filtrage strict des transactions
- **Performance** : Aucune latence, mise à jour instantanée

#### Provisions Personnalisées ✅ IMPLÉMENTÉES
**Objectif** : Épargne objectifs flexibles et automatisées
- **Types** : Pourcentage revenus, montant fixe, formule personnalisée
- **Calculs** : Répartition couple, dates début/fin, provisions temporaires
- **Suivi** : Barre progression verte avec montant cumulé depuis janvier
- **Progression annuelle** : Calcul automatique mois X/12 avec projections
- **Catégories** : Vacances, travaux, véhicule, urgence, projets enfants
- **Interface intégrée** : Gestion provisions dans détail catégorie du drill-down

### 3.2 Advanced Features (Should-Have)

#### Analytics & Insights
**Objectif** : Compréhension comportements financiers
- **Tendances** : Évolution 12 mois, comparaisons périodiques
- **Prédictions** : Projections 3-6 mois basées ML
- **Alertes** : Dépassements budgets, objectifs atteignables
- **Scoring** : Indice santé financière familiale

#### Configuration Avancée
**Objectif** : Adaptation tous profils familiaux
- **Multi-membres** : Répartition charges/revenus personnalisée
- **Calendrier** : Saisonnalité dépenses, événements récurrents
- **Règles business** : Formules calculs, exceptions, cas particuliers

### 3.3 Nice-to-Have Features

#### Collaboration Famille
- Comptes multiples, permissions granulaires
- Commentaires transactions, validations croisées
- Notifications objectifs partagés

#### Intégrations Externes
- APIs bancaires PSD2 (connexion directe)
- Export comptables (Ciel, Sage, Excel)
- Synchronisation calendriers (vacances, échéances)

---

## 4. Exigences Techniques

### 4.1 Architecture Système

#### Backend Requirements
- **Framework** : FastAPI (performance, documentation automatique)
- **Base de données** : SQLite → PostgreSQL (évolutivité)
- **ML Pipeline** : Scikit-learn, modèles pré-entraînés + apprentissage
- **APIs** : RESTful, documentation Swagger, versioning
- **Performance** : <2s temps réponse, 1000+ requêtes/min

#### Frontend Requirements
- **Framework** : Next.js 14 (SSR, optimisations)
- **UI/UX** : Tailwind CSS, composants réutilisables, design system
- **State Management** : React Context + Zustand pour états complexes
- **Mobile** : PWA, responsive design, touch gestures
- **Performance** : <3s First Contentful Paint, >90 Lighthouse score

#### Infrastructure Requirements
- **Containerisation** : Docker (développement + production)
- **CI/CD** : GitHub Actions, tests automatisés
- **Monitoring** : Logs structurés, métriques performance
- **Sécurité** : HTTPS, JWT, chiffrement données sensibles

### 4.2 Compatibilité et Support

#### Navigateurs
- **Desktop** : Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile** : iOS Safari 14+, Android Chrome 90+
- **PWA** : Installation native, fonctionnement offline

#### Systèmes
- **Développement** : Windows WSL2, macOS, Linux Ubuntu
- **Production** : Linux containers, cloud providers
- **Base de données** : SQLite (dev), PostgreSQL (prod)

---

## 5. Expérience Utilisateur (UX)

### 5.1 Parcours Utilisateur Principal

#### Onboarding (Premier usage)
1. **Accueil** : Présentation valeur ajoutée, promesse "5 minutes setup"
2. **Configuration** : Revenus couple, objectifs épargne principaux
3. **Import initial** : Assistant CSV, détection automatique colonnes
4. **Découverte** : Tour guidé interface, tips contextuels

#### Usage Récurrent (Hebdomadaire)
1. **Check rapide** : Dashboard, alertes nouvelles
2. **Transactions** : Validation auto-tagging, corrections manuelles
3. **Objectifs** : Progression épargnes, ajustements provisions

### 5.2 Principes Design

#### Simplicité
- **Règle 3 clics** : Toute information accessible en maximum 3 clics
- **Progressive disclosure** : Information complexe masquée par défaut
- **Defaults intelligents** : Configuration pré-remplie, suggestions contextuelles

#### Feedback Visuel
- **Micro-interactions** : Confirmations actions, transitions fluides
- **État système** : Loading states, progress bars, indicateurs santé
- **Accessibility** : Contraste, tailles texte, navigation clavier

#### Performance Perçue
- **Skeleton screens** : Chargement progressif
- **Cache intelligent** : Données fréquentes en local
- **Lazy loading** : Images et composants lourds différés

---

## 6. Modèle de Données

### 6.1 Entités Principales

#### Transaction
```sql
- id, date, amount, description, account
- category (auto + manual), subcategory  
- is_expense, is_fixed, exclude_from_budget
- tags[], ml_confidence_score
- created_at, updated_at, user_id
```

#### CustomProvision (Épargne)
```sql
- id, name, description, icon, color
- percentage, fixed_amount, base_calculation
- split_mode, split_member1, split_member2
- target_amount, current_amount, category
- is_active, is_temporary, start_date, end_date
- created_by, created_at, updated_at
```

#### Config (Utilisateur)
```sql
- id, user_id, member1_name, member2_name
- member1_salary, member2_salary
- tax_rate1, tax_rate2 (taux d'imposition en %)
- split_fixed_charges, split_variable_charges
- created_at, updated_at
```

### 6.2 Relations et Contraintes

#### Intégrité Données
- **Cascade Delete** : Suppression utilisateur → données associées
- **Validation** : Montants positifs, dates cohérentes, pourcentages 0-100%
- **Index** : Performance requêtes (date, user_id, category)

#### Évolutivité
- **Migrations** : Scripts automatisés, rollback possibles
- **Versioning** : Schema evolution, backward compatibility
- **Backup** : Stratégie sauvegarde, restore procédures

---

## 7. Sécurité et Conformité

### 7.1 Protection Données

#### Authentification
- **JWT Tokens** : Expiration automatique, refresh token
- **Sécurité mot de passe** : Hachage bcrypt, complexité minimum
- **Session management** : Timeout inactivité, logout automatique

#### Chiffrement
- **HTTPS obligatoire** : TLS 1.3, certificats automatiques
- **Données sensibles** : Chiffrement AES-256 en base
- **API Keys** : Stockage sécurisé, rotation périodique

#### Audit et Monitoring
- **Logs sécurité** : Tentatives connexion, actions sensibles
- **Alertes** : Détection intrusions, comportements anormaux
- **Compliance** : RGPD, droit suppression, portabilité données

### 7.2 Resilience

#### Backup et Recovery
- **Backup automatique** : Quotidien, rétention 30 jours
- **Test restore** : Vérification mensuelle procédures
- **Disaster recovery** : RTO <4h, RPO <1h

---

## 8. Métriques et KPIs

### 8.1 Métriques Produit

#### Adoption
- **MAU** (Monthly Active Users) : Objectif 1000+ utilisateurs
- **Retention** : J7 >40%, J30 >20%, J90 >15%
- **Time to Value** : <10 minutes premier import réussi

#### Engagement
- **Session duration** : Objectif 8-12 minutes moyenne
- **Pages par session** : >5 pages (navigation hiérarchique)
- **Feature adoption** : >80% utilisation dashboard, >60% provisions

### 8.2 Métriques Techniques

#### Performance
- **API Response Time** : P95 <2s, P99 <5s
- **Frontend Performance** : FCP <3s, TTI <5s, CLS <0.1
- **Uptime** : >99.5% (objectif 99.9%)

#### Qualité
- **ML Accuracy** : Auto-tagging >95% (objectif 97%)
- **Error Rate** : <1% erreurs utilisateur, <0.1% erreurs système
- **Support Tickets** : <5% utilisateurs actifs/mois

---

## 9. Roadmap et Releases

### 9.1 Release Planning

#### v2.3.3 (Août 2025) - Current
- ✅ CleanDashboard Provision-First avec design moderne
- ✅ Drill-down dépenses hiérarchique complet
- ✅ Système de tags simplifié sans modal IA
- ✅ Import CSV/XLSX intelligent multi-format
- ✅ Provisions personnalisées avec barre progression verte
- ✅ Système fiscal avec taux d'imposition individuels
- ✅ Calcul revenus nets et répartition équitable automatisée
- ✅ Navigation hiérarchique : Dépenses → Variables/Fixes → Tags → Transactions
- ✅ Quick Actions opérationnels avec animations CountUp

#### v2.4 (Octobre 2025) - Stabilisation
- 🎯 Correction bugs critiques (CORS, authentification)
- 🎯 PWA et optimisations mobile
- 🎯 Tests end-to-end complets
- 🎯 Performance <1s API response

#### v2.5 (Décembre 2025) - Intelligence
- 🎯 Prédictions ML (dépenses, épargne)
- 🎯 Analytics avancés et insights
- 🎯 Alertes et recommandations
- 🎯 Export PDF automatisé

### 9.2 Feature Flags

#### Experimental Features
- **ML Predictions** : Rollout progressif 10→50→100%
- **PSD2 Integrations** : Beta testing utilisateurs volontaires
- **Advanced Analytics** : A/B test vs interface actuelle

---

## 10. Risques et Mitigation

### 10.1 Risques Techniques

#### Performance et Scalabilité
- **Risque** : Dégradation performance avec croissance données
- **Mitigation** : Pagination, cache Redis, optimisation requêtes

#### Complexité ML
- **Risque** : Maintenance modèles, drift accuracy
- **Mitigation** : Pipeline automatisé, monitoring qualité

### 10.2 Risques Produit

#### Adoption Utilisateur
- **Risque** : Courbe apprentissage trop complexe
- **Mitigation** : Onboarding guidé, documentation interactive

#### Concurrence
- **Risque** : Nouveaux entrants avec features similaires
- **Mitigation** : Innovation continue, fidélisation utilisateurs

---

**Document Version** : 2.3.3  
**Auteur** : Équipe Produit Budget Famille  
**Dernière mise à jour** : 2025-08-13  
**Prochaine révision** : 2025-09-30  

*Ce PRD est un document évolutif, mis à jour en fonction des retours utilisateurs et de l'évolution du marché.*