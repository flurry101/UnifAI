# 02. Frontend Architecture & Modular Component Design

## 1. Technological Stack & Setup
- **Framework**: React 18 (Functional Components, Hooks)
- **Bundler**: Vite 5 (ESBuild for lightning-fast HMR and minified builds)
- **Styling**: Tailwind CSS 3.4 (Extended with RawBlock design tokens)
- **Routing**: Lightweight state-driven view routing integrated with URL OAuth callback parsing
- **HTTP Client**: Decoupled asynchronous Fetch API service layer

---

## 2. Component Hierarchy

```
App.jsx (Main Container & View Router)
│
├── Header.jsx (Persistent Navigation, Persona Badge, Auth Actions, Connection Pill)
│
├── [View Layer] (Mutually Exclusive State or Callback Handler)
│   ├── LandingView.jsx (Hero Section + Simplified SectorGrid)
│   │   └── SectorGrid.jsx (Clean 5-Track Sector Industrial Matrix)
│   │
│   ├── UserView.jsx (CPSE Operational Workspace)
│   │   ├── RawInput (Material Query / Prefix Search)
│   │   ├── Benchmark Quick Selector Chips
│   │   ├── Specification & Normalized Attribute Inspector (Lanes 2-3)
│   │   ├── Pipeline Execution Action (Gated by RBAC)
│   │   └── Match Candidate Cards (Lanes 5-8 Results + Probability Vectors)
│   │
│   ├── ReviewerView.jsx (Technical Governance Workspace)
│   │   ├── Review Queue Sidebar (Filterable Proposal Pairs)
│   │   ├── Side-by-Side Candidate Comparison (Material A vs Material B)
│   │   ├── Lane 6 Technical Attribute Conflict Table (Match vs Conflict)
│   │   └── Arbitration Decision Form (Override Radio, Evidence Tags, Notes)
│   │
│   ├── AdminView.jsx (National Master Catalog Workspace)
│   │   ├── Metric Strip (Total CNMC, Approved Masters, Proposed, Mappings)
│   │   ├── Filterable CNMC Directory Table
│   │   └── Selected CNMC Lineage & Cross-CPSE Mapping Inspector
│   │
│   └── OAuthCallback.jsx (Google Identity Callback Handler)
│       └── Token capture, profile resolution, role navigation
│
├── Footer.jsx (Industrial Brutalist Footer with Status Diagnostics)
│
└── AuthModal.jsx (Platform Sign In & Enterprise Registration Modal)
    ├── Google Cloud Identity Button
    ├── Email / Username Login Form
    ├── CPSE Organization Dropdown (All 14 CPSEs across 6 Sectors)
    ├── Assigned Role Dropdown (CPSE User, Reviewer, Admin)
    └── One-Click Seeded Credential Strip
```

---

## 3. Decoupled Service Layer (`frontend/src/api/`)

To preserve backend decoupling and enable clean API contracts, all backend network interactions are abstracted into dedicated client services:

### 1. `client.js`
- Centrally handles `apiFetch()` wrapper.
- Automatic backend URL resolution (`VITE_BACKEND_API_URL` or fallback to relative `/api/` for Docker reverse proxy).
- Automatically attaches `Authorization: Bearer <token>` when a session token is present.
- Provides `checkBackendHealth()` for the header liveness indicator.

### 2. `auth.js`
- `loginWithCredentials(usernameOrEmail, password)`
- `registerUser({ username, email, password, role, cpse_id })`
- `getGoogleOAuthUrl(redirectUri)`
- `exchangeGoogleCode({ code, redirectUri, role, cpseId })`
- `getUserProfile()` — queries `/api/v1/auth/me`
- `getCurrentSession()`, `saveSession()`, and `clearSession()` with JWT base64 decoding.

### 3. `materials.js`
- `fetchMaterialById(id)`: Looks up material specifications from SQLite/Postgres.
- `triggerAiMatch(materialId)`: Initiates Lane 5–8 candidate matching pipeline.
- `SAMPLE_MATERIALS`: Built-in verified benchmark test fixtures (`MAT-IOCL-PIPE-001`, `1236/1231`, `ONGC_PIPE_4IN_CS_A106`, etc.).

### 4. `governance.js`
- `fetchPendingReviews()`: Fetches unreviewed pair proposals from `match_proposal`.
- `submitReviewDecision(proposalId, { action, relationship_override })`: Commits reviewer approval or rejection to the governance state machine.

### 5. `cnmc.js`
- `fetchCnmcCatalog()`: Queries national catalog directory from `/api/v1/cnmc/`.
- `fetchCnmcDetail(id)`: Queries specific CNMC record lineage and cross-CPSE mappings.

---

## 4. State Management (`AuthContext.jsx`)

The frontend state is managed via React Context (`useAuth()`):
- **`session`**: Tracks `token`, `username`, `email`, `role`, `auth_provider`, `avatar_url`, and `isAuthenticated`.
- **`activePersona`**: Controls current active view (`'user'`, `'reviewer'`, `'admin'`).
- **`health`**: Background health check polling every 15 seconds against `/health`.
- **`switchPersona(personaKey)`**: Updates active workspace without logging out.
- **`exchangeOAuthCode(payload)`**: Handles Google OAuth code completion and updates session.

