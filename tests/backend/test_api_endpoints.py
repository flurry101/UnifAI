import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from app.main import app
from app.database import get_db, Base
from app.models import ExternalIdentity, User, MatchProposal
import app.api.auth as auth_api

# Mock security before importing jwt
import app.security.jwt as jwt_module
jwt_module.get_password_hash = lambda x: x + "_hashed"
jwt_module.verify_password = lambda plain, hashed: plain + "_hashed" == hashed
auth_api.get_password_hash = jwt_module.get_password_hash
auth_api.verify_password = jwt_module.verify_password

# Setup in-memory SQLite for testing

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    from app.models import CpseTenant
    # Seed a tenant
    tenant = CpseTenant(id="tenant1", code="CPSE01", name="Test CPSE")
    db.add(tenant)

    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE material_retrieval (
                material_id TEXT PRIMARY KEY,
                cpse_id TEXT NOT NULL,
                original_material_code TEXT,
                normalized_description TEXT,
                source_system TEXT,
                source_type TEXT,
                source_record_id TEXT,
                source_file TEXT,
                source_row INTEGER,
                ingestion_timestamp TEXT,
                processing_version TEXT
            )
        """)
        connection.exec_driver_sql(
            "INSERT INTO material_retrieval (material_id, cpse_id, original_material_code, normalized_description, source_system) "
            "VALUES ('MAT_Q1', 'tenant1', 'Q1', 'Test material', 'TEST')"
        )
        connection.exec_driver_sql(
            "INSERT INTO material_retrieval (material_id, cpse_id, original_material_code, normalized_description, source_system) "
            "VALUES ('MAT_C1', 'tenant1', 'C1', 'Candidate material', 'TEST')"
        )
    
    # Seed a test user
    test_user = User(
        username="admin",
        hashed_password=jwt_module.get_password_hash("password123"),
        role="NATIONAL_ADMIN",
        cpse_id="tenant1"
    )
    db.add(test_user)
    
    # Seed a proposal
    proposal = MatchProposal(
        id="PROPOSAL_1",
        query_material_id="MAT_Q1",
        candidate_material_id="MAT_C1",
        predicted_relation="IDENTICAL",
        confidence_level="HIGH",
        decision_status="REVIEW",
        governance_state="PENDING",
        lane7_probabilities={"IDENTICAL": 0.9, "DISTINCT": 0.1},
        lane8_decision={"reason": "test"},
        model_version="v1"
    )
    db.add(proposal)
    db.commit()
    yield
    # Drop tables
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE material_retrieval")
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_token():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "password123"}
    )
    return response.json()["access_token"]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_login_success():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_google_identity_is_not_linked_by_email():
    db = TestingSessionLocal()
    db.add(User(
        username="local_user",
        email="owner@example.com",
        hashed_password="password_hashed",
        role="CPSE_USER",
        cpse_id="tenant1",
    ))
    db.commit()

    with pytest.raises(auth_api.HTTPException) as exc_info:
        auth_api._upsert_google_user(
            db,
            email="owner@example.com",
            name="Google User",
            avatar_url=None,
            role="CPSE_USER",
            cpse_id="tenant1",
            google_subject="google-subject",
        )

    assert exc_info.value.status_code == 409
    assert db.query(ExternalIdentity).count() == 0
    db.close()

def test_google_oauth_url_issues_signed_cookie_bound_state(monkeypatch):
    monkeypatch.setattr(auth_api, "GOOGLE_CLIENT_ID", "configured-client-id")
    redirect_uri = "https://public.example/auth/google/callback"
    monkeypatch.setattr(auth_api, "GOOGLE_REDIRECT_URI", redirect_uri)
    response = client.get(
        "/api/v1/auth/google/url",
        params={"redirect_uri": redirect_uri, "state": "browser-state"},
    )

    assert response.status_code == 200
    state = response.json()["state"]
    oauth_state = parse_qs(urlparse(response.json()["oauth_url"]).query)["state"][0]
    assert state == oauth_state
    assert response.cookies[auth_api.OAUTH_STATE_COOKIE] == state
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    payload = jwt_module.jwt.decode(state, jwt_module.SECRET_KEY, algorithms=[jwt_module.ALGORITHM])
    assert payload["purpose"] == "google_oauth_state"
    assert payload["redirect_uri"] == redirect_uri
    assert payload["client_state"] == "browser-state"
    client.cookies.clear()

def test_google_oauth_rejects_unconfigured_redirect_uri(monkeypatch):
    monkeypatch.setattr(auth_api, "GOOGLE_CLIENT_ID", "configured-client-id")
    monkeypatch.setattr(auth_api, "GOOGLE_REDIRECT_URI", "https://public.example/auth/google/callback")

    response = client.get(
        "/api/v1/auth/google/url",
        params={"redirect_uri": "https://attacker.example/callback"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "OAuth redirect URI does not match the configured callback"

def test_google_callback_uses_external_https_uri_for_state_exchange_and_cookies(monkeypatch):
    callback_uri = "https://public.example/api/v1/auth/google/callback"
    monkeypatch.setattr(auth_api, "GOOGLE_CLIENT_ID", "configured-client-id")
    monkeypatch.setattr(auth_api, "GOOGLE_CLIENT_SECRET", "configured-client-secret")
    monkeypatch.setattr(auth_api, "GOOGLE_REDIRECT_URI", callback_uri)
    monkeypatch.setattr(auth_api, "SSO_LOGIN_CALLBACK_URL", "https://public.example/auth/google/callback")

    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, data, headers):
            assert data["redirect_uri"] == callback_uri
            return FakeResponse({"access_token": "google-access-token"})

        async def get(self, url, headers):
            return FakeResponse({
                "email": "oauth@example.com",
                "verified_email": True,
                "sub": "google-subject",
                "name": "OAuth User",
            })

    monkeypatch.setattr(auth_api.httpx, "AsyncClient", lambda **kwargs: FakeAsyncClient())
    monkeypatch.setattr(
        auth_api,
        "_upsert_google_user",
        lambda **kwargs: SimpleNamespace(
            username="oauth_user",
            email="oauth@example.com",
            role="CPSE_USER",
        ),
    )
    state = auth_api._create_oauth_state("browser-state")

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "authorization-code", "state": state},
        headers={"cookie": f"{auth_api.OAUTH_STATE_COOKIE}={state}"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://public.example/auth/google/callback?")
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert len(set_cookie_headers) == 2
    assert all("Secure" in header for header in set_cookie_headers)
    assert any(header.startswith("unifai_session=") for header in set_cookie_headers)

def test_google_callback_rejects_missing_or_mismatched_state():
    client.cookies.clear()
    response = client.get("/api/v1/auth/google/callback", params={"code": "code", "state": "invalid"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing or mismatched OAuth state"

@pytest.mark.parametrize(
    ("query_description", "candidate_description", "expected_relation", "raw_score"),
    [
        ("PIPE A", "PIPE B", "EQUIVALENT", 1 / 3 + 0.1),
        ("VALVE A", "VALVE B", "VARIANT_OF", 1 / 3 + 0.1),
        ("PIPE A B", "PIPE A C D", "EQUIVALENT", 0.5),
    ],
)
def test_local_pipeline_probability_favors_selected_relation(
    query_description,
    candidate_description,
    expected_relation,
    raw_score,
):
    from app.services.pipeline_service import _local_match_candidates

    query = SimpleNamespace(
        material_id="query",
        normalized_description=query_description,
        original_material_code=None,
    )
    candidate = SimpleNamespace(
        material_id="candidate",
        normalized_description=candidate_description,
        original_material_code=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    proposal = _local_match_candidates(query, [candidate], db)[0]

    selected_score = proposal.lane7_probabilities[expected_relation]
    other_relation = "VARIANT_OF" if expected_relation == "EQUIVALENT" else "EQUIVALENT"
    assert proposal.predicted_relation == expected_relation
    assert selected_score == pytest.approx(max(raw_score, 1 - raw_score, 0.500001))
    assert proposal.lane7_probabilities[other_relation] == pytest.approx(1 - selected_score)
    assert selected_score > proposal.lane7_probabilities[other_relation]
    assert proposal.lane7_probabilities["IDENTICAL"] == 0.0
    assert proposal.lane7_probabilities["DISTINCT"] == 0.0

@patch("sqlalchemy.orm.Session.execute")
def test_get_material(mock_execute):
    mock_execute.return_value.fetchone.return_value = ("MAT123", "CPSE1", "CODE", "Desc", "ERP")
    response = client.get("/api/v1/materials/MAT123")
    assert response.status_code == 200
    assert response.json()["material_id"] == "MAT123"

@patch("app.api.matches.match_material")
def test_generate_matches(mock_match):
    mock_match.return_value = []
    response = client.post("/api/v1/materials/MAT123/matches")
    assert response.status_code == 200

def test_get_pending_reviews():
    response = client.get("/api/v1/reviews/pending")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_submit_decision_unauthorized():

    response = client.post(
        "/api/v1/reviews/PROPOSAL_1/decision",
        json={"action": "APPROVE"}
    )
    assert response.status_code == 401

def test_submit_decision_authorized(auth_token):
    response = client.post(
        "/api/v1/reviews/PROPOSAL_1/decision",
        json={"action": "APPROVE"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["governance_state"] == "APPROVED"
    assert response.json()["predicted_relation"] == "IDENTICAL"

def test_list_cnmc():
    response = client.get("/api/v1/cnmc/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
