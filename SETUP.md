## UnifAI — System Setup & Deployment Guide

This guide covers local development (SQLite / Local PostgreSQL + pgvector), cloud staging with Supabase, ML model artifact initialization, and the planned air-gapped enterprise production architecture.

---

## 1. Environment Configuration

Copy the template file to configure environment variables:

```bash
cp .env.example .env
```

### Key Environment Variables (`.env`)

| Variable | Scope | Default / Example | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Local / Dev | `sqlite:///./database/local.db` | Local zero-dependency database for rapid testing |
| `POSTGRES_DB` | Local Postgres / Prod | `unifai` | Postgres database name |
| `POSTGRES_USER` | Local Postgres / Prod | `unifai` | Postgres user |
| `POSTGRES_PASSWORD` | Local Postgres / Prod | `changeme` | Postgres password |
| `ALLOW_SQLITE_FALLBACK` | Dev / Offline | `1` | Automatically falls back to SQLite if Postgres is offline |
| `SUPABASE_URL` | Supabase Cloud | `https://xxxx.supabase.co` | Remote Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase Cloud | `your-anon-key` | Public client API key for frontend |
| `SUPABASE_SERVICE_ROLE_KEY`| Backend / Migrations | `your-service-key` | Admin service role key for backend syncing |
| `REMOTE_DATABASE_URL` | Supabase Cloud | `postgresql://postgres:[PW]@db.xxxx.supabase.co:5432/postgres` | Direct pooler/session connection string |
| `EMBEDDING_MODEL_ID` | ML Engine | `Qwen/Qwen3-Embedding-0.6B` | Sentence-transformer embedding backbone |
| `USE_LOCAL_PIPELINE` | ML Engine | `1` | `1` runs in-memory pipeline; `0` queries external endpoints |
| `SECRET_KEY` | Auth & Security | `openssl rand -hex 32` | JWT signing secret for RBAC session tokens |

---

## 2. Local Development Setup

### Option A: Zero-Setup Mode (Local SQLite + In-Memory Vector Search)
*No database installation or Docker required. Uses local SQLite and in-memory vector indexing.*

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database tables and seed sample data
python scripts/init_local_db.py

# 4. Start the FastAPI backend server
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API:** `http://127.0.0.1:8000`
- **Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Health Check:** `curl http://127.0.0.1:8000/health`

---

### Option B: Local Docker Compose (PostgreSQL + pgvector)
*Runs full enterprise stack locally with PostgreSQL 16 and HNSW vector index support.*

```bash
# Start PostgreSQL (pgvector), Backend, and Frontend containers
docker compose -f docker-compose.yml up --build

# Run in background
docker compose -f docker-compose.yml up -d
```
- **Backend Port:** `http://localhost:8000`
- **PostgreSQL Port:** `localhost:5432` (`unifai` / `changeme`)
- **Frontend App:** `http://localhost:3000`

To tear down:
```bash
docker compose down -v  # -v removes persistent volume if clean slate needed
```

---

## 3. Supabase Cloud Configuration

For managed cloud databases with native `pgvector` and OAuth:

### 1. Enable `pgvector` Extension
In your Supabase SQL Editor:
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is active
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 2. Run Database Migrations
Apply Alembic migrations to your remote Supabase instance:
```bash
# Export the remote connection URL
export DATABASE_URL="postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

# Execute Alembic migration head
alembic upgrade head

# Or run the custom migration runner
python scripts/run_migration.py
```

### 3. Configure Google OAuth via Supabase
1. In Google Cloud Console: create OAuth 2.0 Client ID with Redirect URI:
   `https://<your-project-ref>.supabase.co/auth/v1/callback`
2. In Supabase Dashboard: Navigate to **Authentication $\rightarrow$ Providers $\rightarrow$ Google**, insert Client ID and Secret.

---

## 4. ML Model & Pipeline Setup

UnifAI uses a dual-engine architecture: Dense Embeddings + Sparse BM25 + LightGBM Decision Forests.

### 1. Model Artifact Ingestion
The embedding model (`Qwen/Qwen3-Embedding-0.6B` or `all-MiniLM-L6-v2`) downloads automatically on first invocation via HuggingFace `sentence-transformers` and caches locally in `~/.cache/huggingface/hub`.

For air-gapped setups without internet access:
```bash
# Pre-download and cache model artifacts locally
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')"

# Verify LightGBM model and feature schema exist
ls -lh artifacts/matching_model/
# Expected: lightgbm_model.txt, feature_schema.json
```

### 2. Run Pipeline Benchmark & Extraction Tests
```bash
# Evaluate Lane 6 feature extraction and deterministic safety rules
python scripts/generate_final_report.py

# Run full matching engine evaluation on 1,046 ground-truth pairs
python scripts/evaluation/evaluate_matching_engine.py
```

---

## 5. Frontend Development Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install npm packages
npm install

# 3. Configure local frontend environment (.env)
cat <<EOF > .env
VITE_API_BASE_URL="http://localhost:8000/api/v1"
VITE_SUPABASE_URL="https://your-project.supabase.co"
VITE_SUPABASE_ANON_KEY="your-anon-key"
EOF

# 4. Start Vite dev server
npm run dev
```
- **Frontend URL:** `http://localhost:5173` (or `http://localhost:3000` via Docker)
- **Features Included:** Catalog Explorer, Side-by-side HITL Review Workbench, GeoRadar Inter-CPSE Logistics Map.

---

## 6. Verification & Test Suite

The test suite runs 100% offline with synthetic database and authentication mocks:

```bash
# Run all backend tests
PYTHONPATH=. pytest tests/backend/ -v

# Run targeted endpoint tests
PYTHONPATH=. pytest tests/backend/test_api_endpoints.py -v

# Verify platform readiness
python scripts/test_platform.py
```

---

## 7. Architecture

```
                       [ CPSE User / Browser ]
                                  │
                                  ▼
                   [ NGINX Reverse Proxy / HTTPS ]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ React + Vite Frontend ]                         [ FastAPI Backend ]
  (Static / CDN Host)                             (Uvicorn Workers)
                                                           │
                      ┌────────────────────────────────────┼──────────────────────────────────┐
                      ▼                                    ▼                                  ▼
        [ PostgreSQL 16 + pgvector ]            [ ML Inference Engine ]            [ SAP ERP Gateway ]
        • HNSW index on 384/1024-dim             • Qwen3 / MiniLM Embedding         • SAP RFC (pyrfc)
        • `halfvec` 16-bit quantization          • LightGBM Pair Classifier         • MATMAS05 IDoc XML
        • Append-only CNMC lineage               • Deterministic BIS Safety Gates   • S/4HANA OData
```

### Production Deployment Topologies

#### 1. On-Premise Air-Gapped Intranet (MoPNG / CPSE Sovereign Deployments)
* **Zero Cloud Egress:** Self-contained Docker Compose stack configured in `docker-compose.prod.yml`.
* **Database:** Dedicated PostgreSQL 16 container with local persistent volumes (`postgres_data`).
* **Model Storage:** Frozen weights bundled directly into `/app/artifacts` mount.
* **Network Isolation:** Runs on secure enterprise VLAN without access to public internet.

```bash
# Production launch command
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 2. Cloud Staging / Demo (Render & Managed Supabase)
* **Topology:** Managed PaaS deployment orchestrated via `render.yaml`.
* **Backend:** Render Web Service running `uvicorn app.main:app` with auto-scaling.
* **Database:** Managed Supabase PostgreSQL with pooler connection strings and encrypted secrets.
* **Frontend:** Static site build deployed to Render / Vercel Edge.
```