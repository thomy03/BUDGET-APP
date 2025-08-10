# CRUSH.md — Quick Ops & Style Guide for Agents

Build/run
- Backend (FastAPI):
  - Windows: backend\start_secure.py or `python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000` from backend/ after `pip install -r requirements.txt`
  - Linux/macOS: from backend/: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app:app --reload --host 127.0.0.1 --port 8000`
- Frontend (Next.js 14): from frontend/
  - `npm install`
  - `set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 && npm run dev` (Windows) or `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run dev`
  - Build: `npm run build`; Start: `npm start`

Tests
- Python pytest is used (see backend/tests and repo tests):
  - From repo root: `pytest -q`
  - Single file: `pytest backend/test_security.py -q`
  - Single test: `pytest backend/test_security.py::test_name -q`
- Integration helpers: `python integration_test_suite.py` and tests/tests csv samples.

Lint/Typecheck
- Frontend TypeScript: `npm run build` (Next/SWC typecheck) or `tsc -p tsconfig.json --noEmit` (if tsc available)
- Tailwind: standard config; no additional lint script defined.
- Python: prefer `ruff`/`flake8` if available; else PEP8 conventions. Security tests under backend/ should pass.

Imports & formatting
- Frontend: absolute app imports via Next.js app router; group order: react/next, third-party, internal (frontend/lib, components), styles.
- Use TypeScript strict typing, avoid any; prefer readonly types and discriminated unions; React function components; hooks at top-level only.
- Backend: follow FastAPI idioms; keep routers, models, services separated when adding code; respect CORS/security guards.

Naming & errors
- Names: camelCase for TS vars/functions, PascalCase for components/types, snake_case for Python.
- Errors: never swallow; in TS return Result-like objects or throw typed errors; in Python raise HTTPException for API, log via audit_logger where appropriate.
- Never log secrets; read env via process.env (frontend) and os.getenv (backend).

Testing conventions
- Prioritize tests for CSV parsing, auth, and security (see backend/test_security.py, test_critical_fixes*.py). Use sample CSV in tests/csv-samples/.
- Key user validation is mandatory before marking features done (see .claude/CLAUDE.md testing rules).

Docs & roadmap
- Read .claude/CLAUDE.md, ROADMAP_MASTER_V3.md, TECH_STANDARDS.md each task. Update roadmap when tasks complete.

Cursor/Copilot rules
- If .cursor/rules/ or .cursorrules or .github/copilot-instructions.md exist, follow them and mirror key points here. None detected currently.

Reasoning policy
- reasoning_policy: adaptive_max
- Simple tasks: minimal reasoning, direct answer
- Intermediate tasks: reinforced reasoning with targeted validations
- Complex/critical tasks (arch/security/perf/data/ML/integrations/debug): maximal reasoning with structured plan, cross-checks, self-review, and systematic tests

Golden rule (agents & conversation)
- For EVERY user message: respond first via the appropriate agent defined in .crush/agents (announce the agent role and squad)
- Selection: choose lead agent by domain; add reviewers (tech-lead, security-privacy, qa-sdet) based on impact
- Process: apply .crush/GOLDEN_RULE.md multi-tour plan (Lead → Tech Lead → Security → QA → Synthèse)
- Output: provide the agent-driven analysis/plan first, then the concrete actions and results
- Exceptions: trivial system confirmations only
