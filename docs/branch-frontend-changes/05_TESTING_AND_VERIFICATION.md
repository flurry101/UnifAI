# 05. Testing, Automated Verification & QA Results

## 1. Automated Test Suite (`scripts/test_platform.py`)

A comprehensive automated test harness was developed to validate full-stack backend functionality across database interactions, authentication, AI pipelines, governance queues, and catalog lookups.

### Execution Command
```bash
cd /home/flux/hack/unifAI
USE_LOCAL_PIPELINE=1 PYTHONPATH="." .venv/bin/python scripts/test_platform.py
```

### Verified Output (100% Passing)
```
============================================================
unifAI PLATFORM — AUTOMATED SYSTEM TEST
============================================================

[1] Testing: Backend Service Health Check (/health)...
    Response: {'status': 'ok', 'service': 'UnifAI Backend'}
    ✓ PASS

[2] Testing: CPSE User Authentication (/api/v1/auth/login)...
    Authenticated as: cpse_user (Role: CPSE_USER)
    ✓ PASS

[3] Testing: Protected Profile Endpoint (/api/v1/auth/me)...
    Verified Profile: cpse_user | Role: CPSE_USER | CPSE: IOCL
    ✓ PASS

[4] Testing: Google OAuth Consent URL (/api/v1/auth/google/url)...
    OAuth Config Status: configured=True, redirect_uri=http://localhost:5173/auth/google/callback
    ✓ PASS

[5] Testing: Material Retrieval Engine (/api/v1/materials/{id})...
    Found Material: MAT-IOCL-PIPE-001 — SEAMLESS CARBON STEEL LINE PIPE ASTM A106 GRADE B SCH 40 DN ...
    ✓ PASS

[6] Testing: AI Harmonization Matching Pipeline (Lanes 5-8)...
    AI Candidate: MAT-GAIL-PIPE-12IN-X65 | Relation: EQUIVALENT | Routing: REVIEW
    ✓ PASS

[7] Testing: Reviewer Governance Queue (/api/v1/reviews/pending)...
    Pending Arbitration Pairs in Queue: 4
    ✓ PASS

[8] Testing: CNMC National Master Catalog (/api/v1/cnmc/catalog)...
    Registry Item: CNMC-3196-CYL-142 — CYLINDER LPG LOW CARBON STEEL DOMESTIC 14.2 KG CAP...
    ✓ PASS

============================================================
TEST RESULTS: 8/8 TESTS PASSED
============================================================
```

---

## 2. Frontend Production Build Verification

Executed via Vite in `frontend/`:

```bash
cd frontend && npm run build
```

### Build Log Output
```
> unifai-frontend@1.0.0 build
> vite build

vite v5.4.21 building for production...
✓ 50 modules transformed.
dist/index.html                   0.95 kB │ gzip:  0.53 kB
dist/assets/index-CF0Y1KD5.css   21.70 kB │ gzip:  4.52 kB
dist/assets/index-CUaMvCs4.js   211.00 kB │ gzip: 62.75 kB
✓ built in 1.62s
```

---

## 3. Manual Browser Verification Matrix

| Test Case | Scenario / Steps | Expected Result | Status |
|-----------|------------------|-----------------|--------|
| **TC-01** | Open Landing Page at `http://localhost:5173` | Headline reads "ONE NATION — ONE MATERIAL CODE". Sector grid displays 5 clean tracks without long component strings. Top-left logo is clean. | **PASS** |
| **TC-02** | Click "SIGN IN" $\rightarrow$ Seeded "USER" button | Logs in as `cpse_user`. Navigates to User Workspace. Header indicates active role and connection health. | **PASS** |
| **TC-03** | Click Benchmark Chip `[IOCL] MAT-IOCL-PIPE-001` | Displays normalized Lane 2 description and Lane 3 extracted attributes. | **PASS** |
| **TC-04** | Click `▶ EXECUTE AI HARMONIZATION PIPELINE` | Calls Lanes 5–8 engine. Generates candidates with multi-class probability vectors and decision routing. | **PASS** |
| **TC-05** | Switch to Reviewer Workspace as `CPSE_USER` | Red banner shows `[READ-ONLY AUDIT MODE]`. `APPROVE` and `REJECT` buttons are disabled. | **PASS** |
| **TC-06** | Sign in as `reviewer` $\rightarrow$ Submit decision | Decision form unlocks. Clicking `APPROVE AND COMMIT TO CNMC ✓` commits update to database and updates badge. | **PASS** |
| **TC-07** | Sign in as `admin` $\rightarrow$ Filter CNMC records | Filters codes by query string. Clicking `INSPECT` renders lineage record and cross-CPSE mapped entities. | **PASS** |
| **TC-08** | Click "SIGN IN WITH GOOGLE" in AuthModal | Redirects browser to Google Cloud Identity consent screen with client ID and redirect URI. | **PASS** |
| **TC-09** | Google OAuth Callback (`/auth/google/callback`) | Captures code/token, provisions user, and redirects to authorized role workspace. | **PASS** |

