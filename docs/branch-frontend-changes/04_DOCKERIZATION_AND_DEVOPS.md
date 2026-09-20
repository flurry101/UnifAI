# 04. Dockerization, Container Architecture & DevOps

## 1. Directory Organization
Per architectural best practices and consolidation requirements:
- All build definitions and proxy configuration are consolidated under [`docker/`]
- Orchestration and build ignore configurations remain at the repository root.

```
unifAI/
├── docker/
│   ├── Dockerfile.backend      # Python 3.12 FastAPI backend container
│   ├── Dockerfile.frontend     # Multi-stage Node 22 + Nginx Alpine frontend
│   └── nginx.conf              # Reverse proxy & SPA routing configuration
├── docker-compose.yml          # Multi-service container orchestration
├── .dockerignore               # Build context exclusions
├── .env                        # Local active secrets & environment variables
└── .env.example                # Sanitized deployment configuration template
```

---

## 2. Container Specifications

### Backend Container (`docker/Dockerfile.backend`)
- **Base Image**: `python:3.12-slim`
- **Dependencies**: Installs `build-essential` and `curl` for container health monitoring.
- **Source Copies**: Copies `app/`, `artifacts/`, `data/`, `database/`, and `requirements.txt`.
- **Health Check**:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
  ```
- **Entrypoint**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Frontend Container (`docker/Dockerfile.frontend`)
- **Stage 1 (Builder)**: `node:22-alpine`
  - Installs npm dependencies via `npm ci`.
  - Runs `npm run build` using Vite to compile minified HTML, CSS, and JS bundles into `/app/dist`.
- **Stage 2 (Runtime Web Server)**: `nginx:alpine`
  - Copies compiled SPA assets to `/usr/share/nginx/html`.
  - Copies custom [`docker/nginx.conf`] to `/etc/nginx/conf.d/default.conf`.
  - Serves static assets on port 80.

---

## 3. Nginx Reverse Proxy Configuration (`docker/nginx.conf`)

The Nginx configuration eliminates CORS issues and unifies API routing:

1. **SPA Routing Fallback**:
   ```nginx
   location / {
       try_files $uri $uri/ /index.html;
   }
   ```
2. **API Reverse Proxy**:
   ```nginx
   location /api/ {
       proxy_pass http://backend:8000/api/;
       proxy_http_version 1.1;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   }
   ```
3. **Health Check Proxy**:
   ```nginx
   location /health {
       proxy_pass http://backend:8000/health;
   }
   ```
4. **Performance & Compression**:
   - Gzip enabled for text, css, json, javascript, and svg assets.
   - Long-term caching headers (`1y`) for immutable fingerprinted Vite static assets.

---

## 4. Docker Compose Orchestration (`docker-compose.yml`)

```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    container_name: unifai-backend
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:///./database/local.db
      - USE_LOCAL_PIPELINE=1
    volumes:
      - ./database:/app/database
      - ./artifacts:/app/artifacts:ro
    ports:
      - "8000:8000"
    networks:
      - unifai-network

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
    container_name: unifai-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - unifai-network

networks:
  unifai-network:
    driver: bridge
```

---

## 5. Environment Configuration Template (`.env.example`)

```ini
# ==========================================
# unifAI Platform - Environment Configuration Example
# ==========================================

# 1. Database Configuration
DATABASE_URL="sqlite:///./database/local.db"
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"
REMOTE_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres"

# 2. Google Cloud Console OAuth 2.0 Integration
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:5173/auth/google/callback"

# 3. Security & JWT Configuration
SECRET_KEY="generate-with-openssl-rand-hex-32"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 4. Pipeline & ML Engine Settings
USE_LOCAL_PIPELINE=1
EMBEDDING_MODEL_ID="Qwen/Qwen3-Embedding-0.6B"
```

