# CLAUDE.md - Budget Famille v2.3

Ce fichier fournit les instructions et le contexte pour Claude Code lors du travail sur ce projet.

## Vue d'ensemble du projet

Budget Famille v2.3 est une application web moderne de gestion budgétaire familiale avec :
- **Backend** : FastAPI + SQLite avec système ML avancé d'auto-tagging
- **Frontend** : Next.js 14 + TypeScript + Tailwind CSS (Docker pour WSL2)
- **Fonctionnalités** : Import CSV, provisions personnalisées, dépenses fixes, analytics IA

## Scripts de développement recommandés

### Frontend (Docker - Solution WSL2)
```bash
cd frontend
./dev-docker.sh start    # Démarrer le serveur Docker
./dev-docker.sh logs     # Voir les logs
./dev-docker.sh restart  # Redémarrer
./dev-docker.sh stop     # Arrêter
```

### Backend
```bash
cd backend
python3 app.py           # Démarrer le serveur FastAPI
```

### Scripts globaux
```bash
./start-development.sh   # Démarrage complet automatisé
./stop-development.sh    # Arrêt propre de tous les services
```

## Architecture actuelle

### Structure technique
- **Port Frontend** : 45678 (Docker)
- **Port Backend** : 8000 (Python)
- **Base de données** : SQLite avec chiffrement optionnel
- **Authentification** : JWT avec utilisateur admin/secret

### Fonctionnalités clés implémentées
1. **CleanDashboard Provision-First** avec design moderne et 4 métriques clés
2. **Drill-down dépenses hiérarchique** : Dépenses → Variables/Fixes → Tags → Transactions
3. **Système de tags simplifié** : Édition directe sans modal IA
4. **Import CSV/XLSX** multi-mois avec détection automatique
5. **Provisions personnalisées** avec barre de progression et calculs automatiques
6. **Système fiscal complet** avec taux d'imposition et revenus nets

## Standards de développement

### Frontend
- **Framework** : Next.js 14 avec App Router
- **Styling** : Tailwind CSS avec composants UI réutilisables
- **TypeScript** strict activé
- **Docker** obligatoire pour WSL2 (problème Next.js natif)

### Backend
- **Framework** : FastAPI avec Pydantic v1 (important: ne pas utiliser v2 syntax)
- **Base de données** : SQLAlchemy ORM + SQLite
- **ML/IA** : Système de classification avancé intégré
- **API** : Endpoints RESTful documentés avec Swagger

### Outils de qualité
- **Tests** : Jest (frontend), pytest (backend)
- **Linting** : ESLint (frontend), ruff (backend)
- **Formatage** : Prettier (frontend), black (backend)

## Dernières améliorations (Août 2025)

### Session 2025-08-13 - CleanDashboard et Workflow Tags
- **CleanDashboard implémenté** : Design "Provision-First" avec 4 métriques clés
- **Barre progression provisions** : Affichage temporel (7/12 pour juillet) avec animation verte
- **Calcul familial avancé** : (Provisions + Dépenses - Solde compte) / revenus nets
- **Drill-down dépenses fonctionnel** : Navigation Dépenses → Variables/Fixes → Tags → Transactions
- **Filtrage strict** : Montants débiteurs uniquement, exclusion transactions marquées
- **Workflow tags simplifié** : Édition directe sans modal IA, création automatique
- **Cohérence totaux garantie** : drill-down = somme détails
- **Quick Actions opérationnels** : Navigation rapide vers fonctionnalités principales

### Session précédente - Système fiscal
- **Taux d'imposition** : Ajout tax_rate1 et tax_rate2 pour calcul revenus nets
- **Calcul provisions corrigé** : Suppression double division /12 (revenus déjà mensuels)
- **Répartition équitable** : Provisions sur revenus bruts, distribution sur revenus nets
- **Persistance données** : Correction sauvegarde taux d'imposition avec champs contrôlés
- **Compatibilité Pydantic v1** : Migration validators pour éviter ImportError

### Workflow de Tags Simplifié
- **Édition directe** : Modification immédiate sans interruption
- **Détection automatique** : Nouveaux tags créés via TagAutomationService
- **Cohérence** : Endpoint dédié pour mise à jour des tags
- **Performance** : Aucune latence modal IA

## Problèmes connus et solutions

### WSL2 + Next.js
- **Problème** : Next.js 14.2.31 incompatible avec WSL2
- **Solution** : Docker obligatoire via `dev-docker.sh`
- **Status** : ✅ Résolu et documenté

### Performance
- **Frontend** : Hot reload fonctionnel
- **Backend** : <2s temps de réponse
- **Database** : 34 index optimisés pour performance

### Authentification
- **Utilisateur** : admin / secret
- **JWT** : Token automatiquement géré
- **Sécurité** : Headers CORS configurés

## Commandes de test

```bash
# Tests backend
cd backend && python -m pytest

# Tests frontend  
cd frontend && npm test

# Tests end-to-end
python test_e2e_navigation.py

# Validation complète
./run_all_tests.sh
```

## Structure des données

### Tables principales
- **transactions** : Données bancaires importées
- **custom_provisions** : Provisions personnalisées
- **fixed_lines** : Dépenses fixes récurrentes
- **users** : Authentification utilisateurs
- **tag_mappings** : Système de tags IA
- **config** : Configuration utilisateur avec tax_rate1/tax_rate2

### Endpoints API essentiels
- `GET /custom-provisions` : Liste des provisions
- `POST /custom-provisions` : Créer provision
- `PUT /custom-provisions/{id}` : Modifier provision
- `DELETE /custom-provisions/{id}` : Supprimer provision (à vérifier)
- `GET /fixed-lines` : Dépenses fixes
- `POST /import` : Import CSV/XLSX

## Notes pour futures développements

### Priorités identifiées
1. **Performance optimisation** : Réduire appels API redondants en cache
2. **Interface provisions** : Améliorer UX dans drill-down catégories
3. **Mobile responsive** : Adapter CleanDashboard pour smartphones
4. **Tests E2E complets** : Valider drill-down et calculs provisions automatisés
5. **Nettoyage composants** : Supprimer références EnhancedDashboard legacy

### Architecture future
- **Multi-tenant** : Support plusieurs utilisateurs
- **Real-time** : WebSocket pour updates live
- **Export** : PDF automatisé des synthèses
- **Intégrations** : APIs bancaires PSD2

## Contact et support

Pour questions techniques ou améliorations :
- Utiliser les scripts de développement fournis
- Vérifier les logs avec `./dev-docker.sh logs`
- Consulter la documentation API sur http://localhost:8000/docs
- Tester l'interface sur http://localhost:45678

---

**Version** : 2.3.3  
**Dernière mise à jour** : 2025-08-13  
**Statut** : ✅ Production-ready avec CleanDashboard et drill-down complets