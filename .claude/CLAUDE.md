# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a family budget management application (Budget Famille v2.3) with a FastAPI backend and Next.js frontend. The application tracks expenses, manages shared budgets between two members, and provides analytics.

## Development general (IMPORTANT!!!)
Each time the user make a request, you must first of all read this documentation + PRD.md and ROADMAP_MASTER_V3.md
For each request, you must use agents under claude\agents to perform the request, task and the project. Be smart and consciousness. Use it in parallelle if needed.
You MUST each time you finish a task note it to ROADMAP_MASTER_V3 and note it also on PRD/CLAUDE.md
We'll use ubuntu env for our test.
When you finish the task with your agents, the final test will be to the Key users.

## 🚨 KEY USER TESTING - RÈGLE ABSOLUE (CRITICAL!!!)
**TOUTES les étapes finales de test DOIVENT être testées et validées par le key user (utilisateur principal du projet).**

### Processus de Validation Obligatoire :
1. **Avant déploiement** : L'utilisateur DOIT tester chaque fonctionnalité implémentée
2. **Tests d'acceptance** : Validation manuelle par l'utilisateur des scénarios critiques  
3. **Feedback requis** : L'utilisateur doit confirmer que tout fonctionne avant passage à l'étape suivante
4. **Documentation** : Noter tous les retours utilisateur et ajustements nécessaires

### Étapes de Test Key User :
- ✅ Connexion/authentification
- ✅ Import de données CSV 
- ✅ Gestion transactions
- ✅ Configuration paramètres
- ✅ Analytics et rapports
- ✅ Performance générale
- ✅ UX/UI satisfaction

⚠️ **AUCUNE fonctionnalité ne doit être considérée comme terminée sans validation explicite de l'utilisateur principal.**

## Development Commands

### Backend (FastAPI + SQLite)
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate  # Windows
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (Next.js + TypeScript)
```bash
cd frontend
npm install
set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000  # Windows
npm run dev  # Runs on port 45678
npm run build
```

## Architecture

### Backend Structure
- **FastAPI application** (`backend/app.py`) with SQLAlchemy ORM
- **SQLite database** (`budget.db`) storing:
  - Configuration settings (Config table)
  - Transactions (Tx table)
  - Fixed expenses (FixedLine table)
  - Global month settings (GlobalMonth table)
- **CORS enabled** for frontend communication
- **Key endpoints**:
  - Transaction management (CRUD operations)
  - CSV file upload and processing
  - Summary calculations with revenue-based or manual splits
  - Fixed expenses management
  - Analytics data generation

### Frontend Structure
- **Next.js 14** with TypeScript and Tailwind CSS
- **Pages** (App Router):
  - `/` - Main transaction view with filtering
  - `/upload` - CSV file upload interface
  - `/settings` - Configuration management
  - `/analytics` - Data visualization and analysis
- **API client** (`frontend/lib/api.ts`) using Axios with typed interfaces
- **Month management** (`frontend/lib/month.ts`) for date handling
- **MonthPicker component** for shared month selection across pages

## Key Features

- **Multi-month CSV import** with automatic transaction parsing
- **Customizable fixed expenses** with flexible frequency and split options
- **Tag system** for transaction categorization
- **Revenue-based or manual split calculations** between two members
- **Global shared month state** across application
- **Analytics** with category breakdowns and trends