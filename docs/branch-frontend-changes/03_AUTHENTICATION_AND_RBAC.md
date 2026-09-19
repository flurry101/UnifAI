# 03. Authentication, Google OAuth 2.0 & Role-Based Access Control (RBAC)

## 1. Overview
The `frontend` branch transforms unifAI's authentication system into a secure enterprise dual-engine supporting:
1. Traditional credential-based sign-in (via either **Email** or **Username**).
2. **Google OAuth 2.0 Enterprise SSO**, modeled directly after the architectural references.
3. Strict **Role-Based Access Control (RBAC)** gating with pre-seeded read-only audit views.

---

## 2. Google OAuth 2.0 Implementation

### Flow Architecture
```
[User Browser]
   │
   ├─ 1. Clicks "SIGN IN WITH GOOGLE" in AuthModal.jsx
   │     - Saves preferred role & CPSE in localStorage
   │     - Requests /api/v1/auth/google/url?redirect_uri=...
   │
   ├─ 2. Browser redirects to accounts.google.com consent screen
   │
   ├─ 3. User approves; Google redirects to /auth/google/callback?code=...
   │
   ├─ 4. OAuthCallback.jsx activates
   │     - Captures code parameter
   │     - Dispatches POST /api/v1/auth/google/exchange
   │
   ├─ 5. FastAPI Backend (app/api/auth.py)
   │     - Exchanges authorization code at https://oauth2.googleapis.com/token
   │     - Fetches verified email, name, picture from Google UserInfo API
   │     - Finds existing user or provisions new user with CPSE Tenant
   │     - Issues signed unifAI platform JWT access token
   │
   └─ 6. Frontend receives JWT token
         - Persists to localStorage (unifai_token, unifai_username, unifai_role)
         - Switches active persona based on role
         - Smoothly navigates to authorized workspace (/user, /reviewer, or /admin)
```

### Dev Simulation Modal Removed
The development mock modal (`GOOGLE OAUTH ENTERPRISE VERIFICATION: Simulating Google Cloud Console authentication...`) was **completely removed**. The flow now uses the live, compliant Google Cloud Identity consent screen with automatic callback exchange.

---

## 3. Database Schema & Migration Changes

### `User` Model Expansion (`app/models.py`)
Three new columns were added to the `User` model to support OAuth and profile identity:
- `email`: `String(255)`, nullable, unique, indexed.
- `auth_provider`: `String(50)`, default `"local"` (`"local"` vs `"google"`).
- `avatar_url`: `String(500)`, nullable (stores Google profile photo URI).

### SQLite Zero-Downtime Safe Column Migration (`app/database.py`)
To prevent `OperationalError: no such column` when running against existing SQLite files, an automated dynamic column migration helper `_migrate_columns()` inspects `PRAGMA table_info(users)` on startup and executes `ALTER TABLE users ADD COLUMN ...` if columns are absent.

### Sentinel Hash for OAuth Accounts
To satisfy SQLite's `NOT NULL` constraint on `users.hashed_password` without exposing credentials, Google OAuth users are provisioned with a secure sentinel value: `hashed_password = "OAUTH_GOOGLE"`.

### Database Relocation & Isolation
- Moved `local.db` $\rightarrow$ `database/local.db`.
- Added `database/*.db`, `*.sqlite`, `*.sqlite3` to `.gitignore` to keep binary database files out of git tracking.
- Added `database/.gitkeep` to preserve the folder structure in version control.

---

## 4. Role-Based Access Control (RBAC) Matrix

unifAI enforces 3 core enterprise stakeholder roles:

| Role Identifier | Display Title | Scope & Authority |
|-----------------|---------------|-------------------|
| **`CPSE_USER`** | CPSE User | Operational catalog management for specific CPSE (IOCL, ONGC, GAIL, etc.). Ingests materials, audits normalized attributes, and triggers AI matching pipelines. |
| **`TECHNICAL_REVIEWER`** | Technical Reviewer | Central Technical Governance Board. Arbitrates attribute conflicts (Lane 6) and commits binding decisions to the CNMC registry. |
| **`NATIONAL_ADMIN`** | National Admin | National Harmonization Cell. Full governance over the global CNMC directory and cross-CPSE linkage registry. |

---

## 5. Pre-Seeded Read-Only Security Gating

Per user requirements, unauthenticated users or users viewing another persona's workspace operate in **Strict Read-Only Mode**:

1. **User Workspace (`UserView.jsx`)**:
   - If user is not authenticated as `CPSE_USER`, a high-contrast banner appears:  
     `[SECURITY AUDIT VIEW] Active persona is REVIEWER/ADMIN/GUEST. Material catalog is in READ-ONLY mode for oversight security.`
   - The execution button is disabled:  
     `▶ PIPELINE EXECUTION (RESTRICTED TO CPSE USERS)`

2. **Reviewer Workspace (`ReviewerView.jsx`)**:
   - Only authenticated `TECHNICAL_REVIEWER` or `NATIONAL_ADMIN` accounts can submit decisions.
   - For all other roles, a warning displays:  
     `[READ-ONLY AUDIT MODE] Review queue is in READ-ONLY mode. Sign in as TECHNICAL_REVIEWER to record decisions.`
   - `APPROVE` and `REJECT` action buttons are strictly disabled.

3. **Admin Workspace (`AdminView.jsx`)**:
   - Non-admin sessions display:  
     `[READ-ONLY REGISTRY VIEW] Viewing national CNMC catalog in READ-ONLY mode. Master modifications are restricted to NATIONAL_ADMIN.`

---

## 6. CPSE Organization Coverage (Registration Matrix)

The registration modal features all 14 mandatory CPSE public sector undertakings grouped by industrial sector:

```
├── OIL & GAS
│   ├── ONGC — Oil & Natural Gas Corporation
│   ├── IOCL — Indian Oil Corporation
│   ├── GAIL — Gas Authority of India
│   ├── HPCL — Hindustan Petroleum
│   ├── BPCL — Bharat Petroleum
│   └── CPCL — Chennai Petroleum
├── POWER
│   ├── NTPC — National Thermal Power
│   ├── NHPC — National Hydroelectric Power
│   └── POWERGRID — Power Grid Corporation
├── STEEL
│   ├── SAIL — Steel Authority of India
│   └── RINL — Rashtriya Ispat Nigam
├── MINING
│   ├── COAL INDIA — Coal India Limited
│   └── NMDC — National Mineral Development
├── HEAVY ENGINEERING
│   └── BHEL — Bharat Heavy Electricals
└── DEFENCE ELECTRONICS
    └── BEL — Bharat Electronics
```

