# ROADMAP - Budget Famille v4.1

Feuille de route strategique pour le developpement continu de l'application Budget Famille.

## Version Actuelle : 4.1 (Janvier 2026)

### Fonctionnalites Livrees v4.0 - v4.1

#### Budget Intelligence System (v4.0 - Decembre 2025)
- **Objectifs Budget** : CRUD complet par categorie/tag
- **Predictions ML** : Fin de mois par categorie avec tendances
- **Alertes Intelligentes** : 3 types (overspend_risk, unusual_spike, category_trend)
- **Analyse IA** : Integration OpenRouter (DeepSeek V3.2)
- **Detection Anomalies** : Isolation Forest + fuzzy matching doublons

#### Dashboard Ameliore (v4.1 - Janvier 2026)
- **Repartition par membre** : Details provisions et depenses par personne
- **Production-ready** : Tests complets, corrections bugs
- **Orchestrator Skills** : Phase 0 avec cache local et recherche skills.sh

#### Auto-Tagging Frontend (v3.2 - Decembre 2025)
- **Bouton Auto-Tag** : Preview suggestions avec confiance
- **Mode Batch** : Selection multiple, raccourcis clavier
- **Drill-down ameliore** : Navigation jusqu'au niveau mois

#### Tests et Qualite (Janvier 2026)
- **Frontend** : 136 tests Jest passing
- **Backend** : pytest avec fixtures isolees
- **CI/CD** : GitHub Actions automatises

---

## Historique des Versions

### v4.1 (Janvier 2026) - ACTUELLE
- [x] Dashboard repartition detaillee provisions/depenses par membre
- [x] Budget Intelligence System production-ready
- [x] Corrections Pydantic v2 deprecation warnings
- [x] Tests database models isolation
- [x] Orchestrator avec Skills Discovery hybride
- [x] Cache local skills-registry.json (50 skills)

### v4.0 (Decembre 2025)
- [x] Budget Intelligence System complet
- [x] Objectifs budget par categorie (CategoryBudgetsConfig)
- [x] Predictions ML fin de mois (ml_budget_predictor.py)
- [x] Alertes intelligentes (AlertsBanner, AlertsIndicator)
- [x] Analyse IA ecarts (BudgetVarianceAnalysis)
- [x] Detection anomalies (ml_anomaly_detector.py)
- [x] Page Analytics avec onglets (drilldown, budget, ai)
- [x] Integration OpenRouter (DeepSeek V3.2)

### v3.2 (Decembre 2025)
- [x] Auto-tagging frontend avec preview
- [x] Drill-down analytics jusqu'au niveau mois
- [x] Mode batch transactions (B, T, Shift+Click)
- [x] Pattern matching intelligent (exact, first word, substring)

### v3.0 (Decembre 2025)
- [x] Dashboard Glassmorphism avec Dark Mode
- [x] Analytics modernisee (3 vues)
- [x] Smart Tag ameliore
- [x] Scripts PowerShell complets

### v2.3.3 (Aout 2025)
- [x] CleanDashboard Provision-First
- [x] Drill-down depenses hierarchique
- [x] Systeme fiscal (taux imposition)
- [x] Provisions personnalisees

---

## v4.2 - Phase Mobile (Fevrier 2026)

### Priorite 1 : Application Mobile

#### React Native / Expo
- [ ] Setup projet Expo
- [ ] Navigation React Navigation
- [ ] Composants partages avec web
- [ ] Authentification mobile

#### PWA Optimisee
- [ ] Service Worker complet
- [ ] Cache offline transactions
- [ ] Notifications push
- [ ] Installation native

### Priorite 2 : Export et Rapports

#### PDF Automatise
- [ ] Synthese mensuelle PDF
- [ ] Graphiques inclus
- [ ] Template personnalisable
- [ ] Envoi par email

#### Export Avance
- [ ] Excel avec formules
- [ ] CSV multi-format
- [ ] API export bulk

---

## v4.3 - Phase Intelligence+ (Mars 2026)

### Ameliorations ML

#### Transformers
- [ ] Modele de classification avance
- [ ] Embeddings marchands
- [ ] Clustering automatique categories

#### Predictions Avancees
- [ ] Forecast 6 mois
- [ ] Saisonnalite detectee
- [ ] Confidence intervals

### Analytics Avances

#### Nouveaux Dashboards
- [ ] Comparaison annee precedente
- [ ] Benchmark anonymise
- [ ] Goals tracking visuel

---

## v5.0 - Phase Ecosysteme (Q2 2026)

### Integrations Bancaires PSD2

#### Connecteurs
- [ ] Credit Agricole
- [ ] BNP Paribas
- [ ] Societe Generale
- [ ] Boursorama

#### Synchronisation
- [ ] Import automatique quotidien
- [ ] Reconciliation intelligente
- [ ] Multi-comptes

### Architecture Multi-tenant

#### Gestion Utilisateurs
- [ ] Comptes famille partages
- [ ] Permissions granulaires
- [ ] Invitations email

#### Infrastructure
- [ ] PostgreSQL migration
- [ ] Redis cache
- [ ] WebSocket temps reel

---

## v5.1+ - Phase Innovation (Q3+ 2026)

### Assistant IA Conversationnel

#### Chatbot
- [ ] Questions naturelles budget
- [ ] Conseils personnalises
- [ ] Commandes vocales

### Marketplace

#### API Publique
- [ ] Documentation OpenAPI
- [ ] SDK TypeScript/Python
- [ ] Webhooks

#### Integrations Tierces
- [ ] Logiciels comptables
- [ ] Comparateurs financiers
- [ ] Calendriers

---

## Stack Technique Evolution

### Backend
| Version | Stack |
|---------|-------|
| v4.x | FastAPI + SQLite + SQLAlchemy |
| v5.0 | + PostgreSQL + Redis |
| v5.1 | + Microservices + Kubernetes |

### Frontend
| Version | Stack |
|---------|-------|
| v4.x | Next.js 14 + TypeScript + Tailwind |
| v4.2 | + React Native + Expo |
| v5.0 | + Micro-frontends |

### ML/IA
| Version | Stack |
|---------|-------|
| v4.x | Scikit-learn + OpenRouter |
| v4.3 | + Transformers + Embeddings |
| v5.0 | + Fine-tuned models |

---

## Metriques de Qualite

### Performance Targets
| Metrique | Actuel | Target v5.0 |
|----------|--------|-------------|
| API Response | <2s | <500ms |
| FCP | <3s | <1s |
| Uptime | 99% | 99.9% |

### Tests Coverage
| Composant | Actuel | Target |
|-----------|--------|--------|
| Frontend Jest | 136 tests | 200+ |
| Backend pytest | En cours | 100+ |
| E2E | 0 | 50+ |

---

## Processus de Developpement

### Cycles de Release
- **Hotfix** : <24h pour corrections critiques
- **Minor** : Toutes les 2 semaines
- **Major** : Tous les 2-3 mois

### Outils Claude Code
- **Orchestrator** : Workflow structure avec Skills Discovery
- **Agents specialises** : 17 agents dans .claude/agents/
- **Skills.sh** : Cache local + recherche automatique

### Validation
- **Tests automatises** : GitHub Actions CI/CD
- **Code review** : Via Claude Code
- **Tests utilisateurs** : Beta testing

---

**Version document** : 4.1
**Derniere mise a jour** : 2026-01-25
**Prochaine revision** : 2026-02-15

*Cette roadmap est un document vivant, mis a jour en fonction des retours utilisateurs et de l'evolution technologique.*
