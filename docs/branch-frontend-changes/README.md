# `frontend` Branch Documentation & Change Log

## Overview
This directory comprehensively documents all architectural, design, full-stack implementation, and DevOps changes developed in the **`frontend`** branch of the **unifAI** platform.

The branch transitions the repository from a backend-focused research prototype to a production-ready, enterprise-grade unified material harmonization platform adhering to the **RawBlock Anti-Design Brutalist System**, featuring strict **Role-Based Access Control (RBAC)**, **Google OAuth 2.0 Integration (Synapse Architecture)**, and containerized deployment.

---

## Documentation Index

| Document | Focus & Contents |
|----------|------------------|
| [**01_DESIGN_SYSTEM.md**](./01_DESIGN_SYSTEM.md) | RawBlock Anti-Design brutalist guidelines: 0px border radius, high-contrast monochrome color palette, Archivo Black & Space Mono typography, responsive breakpoints, and UI primitives. |
| [**02_ARCHITECTURE_AND_COMPONENTS.md**](./02_ARCHITECTURE_AND_COMPONENTS.md) | Component-based frontend architecture: React + Vite + Tailwind, modular directory structure, role workspaces (User, Reviewer, Admin), and decoupled API client service layer. |
| [**03_AUTHENTICATION_AND_RBAC.md**](./03_AUTHENTICATION_AND_RBAC.md) | Dual authentication engine (Email/Username + Google OAuth 2.0), Synapse repository alignment, role permissions (CPSE User, Reviewer, Admin), read-only audit gating, and database migrations. |
| [**04_DOCKERIZATION_AND_DEVOPS.md**](./04_DOCKERIZATION_AND_DEVOPS.md) | Consolidated Docker structure under `docker/`, Multi-stage Nginx React build, Python FastAPI container, Compose orchestration, volume mounts, and environment configuration. |
| [**05_TESTING_AND_VERIFICATION.md**](./05_TESTING_AND_VERIFICATION.md) | Automated backend verification suite (`scripts/test_platform.py`), end-to-end integration test results, and browser verification manual test cases. |

---

## High-Level Summary of Changes

```
unifAI Project Root
├── app/
│   ├── api/
│   │   ├── auth.py             [EXPANDED] Google OAuth code exchange, /me profile, /google/callback
│   │   └── cnmc.py             [UPDATED] /catalog alias route for CNMC master registry
│   ├── database.py             [UPDATED] Pointed default DB to database/local.db with safe migrations
│   ├── models.py               [UPDATED] User model expanded (email, auth_provider, avatar_url)
│   └── schemas/auth.py         [UPDATED] Added GoogleExchangeRequest
├── database/
│   ├── .gitkeep                [NEW] Preserves database folder structure in git
│   └── local.db                [MOVED] Local SQLite database isolated from project root & git-ignored
├── docker/
│   ├── Dockerfile.backend      [MOVED & OPTIMIZED] Python 3.12-slim backend container
│   ├── Dockerfile.frontend     [MOVED & OPTIMIZED] Multi-stage Node 22 + Nginx Alpine build
│   └── nginx.conf              [NEW] SPA routing + reverse proxy for /api/ and /health
├── docs/
│   └── branch-frontend-changes/ [NEW] Complete technical change logs and documentation
├── frontend/                   [NEW APPLICATION] Complete React 18 + Vite + Tailwind CSS SPA
│   ├── src/
│   │   ├── api/                [NEW] Decoupled API services (client, auth, materials, governance, cnmc)
│   │   ├── components/         [NEW] RawBlock UI primitives + AuthModal + OAuthCallback + SectorGrid
│   │   ├── context/            [NEW] AuthContext with persona management & session persistence
│   │   └── views/              [NEW] LandingView, UserView, ReviewerView, AdminView
├── docker-compose.yml          [NEW/UPDATED] Multi-container orchestration (ports 8000 & 3000)
├── .dockerignore               [NEW] Excludes .venv, node_modules, cache, and secrets
├── .env.example                [NEW] Clean template for Supabase & Google Cloud Console setup
└── scripts/test_platform.py    [NEW] Automated end-to-end integration test runner
```

