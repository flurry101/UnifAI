from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .api import auth, materials, matches, governance, cnmc
from .api import auth, materials, matches, governance, cnmc, admin
from .database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all SQLAlchemy-managed tables exist (safe no-op if already present)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="UnifAI CPSE Harmonization Platform",
    description="Unified Enterprise Material Standardization and Harmonization Platform for CPSEs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(materials.router, prefix="/api/v1/materials", tags=["Materials"])
app.include_router(matches.router, prefix="/api/v1/materials", tags=["Matching"])
app.include_router(governance.router, prefix="/api/v1/reviews", tags=["Governance"])
app.include_router(cnmc.router, prefix="/api/v1/cnmc", tags=["CNMC"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "UnifAI Backend"}
