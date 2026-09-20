import sys
import os

if "pytest" in sys.modules:
    import pytest
    pytest.skip("Manual platform smoke test; run scripts/test_platform.py directly", allow_module_level=True)

# Set environment for local test execution
os.environ["DATABASE_URL"] = "sqlite:///./database/local.db"
os.environ["USE_LOCAL_PIPELINE"] = "1"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 60)
print("unifAI PLATFORM — AUTOMATED SYSTEM TEST")
print("=" * 60)

passed = 0
total = 0

def test_step(name, fn):
    global passed, total
    total += 1
    print(f"\n[{total}] Testing: {name}...")
    try:
        fn()
        print(f"    ✓ PASS")
        passed += 1
    except Exception as e:
        print(f"    ✗ FAIL: {e}")

# 1. Health Check
def t_health():
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data.get("status") == "ok", f"Expected status ok, got {data}"
    print(f"    Response: {data}")

test_step("Backend Service Health Check (/health)", t_health)

# 2. Login as cpse_user
token = None
def t_login():
    global token
    res = client.post("/api/v1/auth/login", data={"username": "cpse_user", "password": "password123"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    token = data.get("access_token")
    assert token, "Token missing in response"
    assert data.get("role") == "CPSE_USER", f"Expected role CPSE_USER, got {data.get('role')}"
    print(f"    Authenticated as: {data.get('username')} (Role: {data.get('role')})")

test_step("CPSE User Authentication (/api/v1/auth/login)", t_login)

# 3. Profile Endpoint (/api/v1/auth/me)
def t_profile():
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data.get("username") == "cpse_user"
    print(f"    Verified Profile: {data.get('username')} | Role: {data.get('role')} | CPSE: {data.get('cpse_id')}")

test_step("Protected Profile Endpoint (/api/v1/auth/me)", t_profile)

# 4. Google OAuth URL Endpoint
def t_google_url():
    res = client.get("/api/v1/auth/google/url?redirect_uri=http://localhost:5173/auth/google/callback")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    print(f"    OAuth Config Status: configured={data.get('configured')}, redirect_uri={data.get('redirect_uri')}")

test_step("Google OAuth Consent URL (/api/v1/auth/google/url)", t_google_url)

# 5. Material Lookup
def t_material():
    res = client.get("/api/v1/materials/MAT-IOCL-PIPE-001")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "PIPE" in data.get("material_id", "")
    print(f"    Found Material: {data.get('material_id')} — {data.get('normalized_description')[:60]}...")

test_step("Material Retrieval Engine (/api/v1/materials/{id})", t_material)

# 6. AI Harmonization Pipeline Match Trigger
def t_match():
    res = client.post("/api/v1/materials/MAT-IOCL-PIPE-001/matches")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    candidates = res.json()
    assert isinstance(candidates, list) and len(candidates) > 0, "No candidates returned"
    c = candidates[0]
    print(f"    AI Candidate: {c.get('candidate_material_id')} | Relation: {c.get('predicted_relation')} | Routing: {c.get('decision_status')}")

test_step("AI Harmonization Matching Pipeline (Lanes 5-8)", t_match)

# 7. Governance Queue Inspection
def t_governance():
    res = client.get("/api/v1/reviews/pending")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    queue = res.json()
    assert isinstance(queue, list), "Expected list response"
    print(f"    Pending Arbitration Pairs in Queue: {len(queue)}")

test_step("Reviewer Governance Queue (/api/v1/reviews/pending)", t_governance)

# 8. CNMC Catalog Master Registry
def t_cnmc():
    res = client.get("/api/v1/cnmc/catalog")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    cat = res.json()
    assert isinstance(cat, list) and len(cat) > 0, "Expected non-empty catalog"
    item = cat[0]
    print(f"    Registry Item: {item.get('cnmc_code')} — {item.get('standardized_description')[:50]}...")

test_step("CNMC National Master Catalog (/api/v1/cnmc/catalog)", t_cnmc)

print("\n" + "=" * 60)
print(f"TEST RESULTS: {passed}/{total} TESTS PASSED")
print("=" * 60)

if passed != total:
    sys.exit(1)

