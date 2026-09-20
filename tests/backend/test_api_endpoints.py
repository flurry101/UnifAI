import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.main import app
from app.database import get_db, Base
from app.models import User, MatchProposal
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
                normalized_description TEXT
            )
        """)
        connection.exec_driver_sql(
            "INSERT INTO material_retrieval (material_id, normalized_description) VALUES ('MAT_Q1', 'Test material')"
        )
        connection.exec_driver_sql(
            "INSERT INTO material_retrieval (material_id, normalized_description) VALUES ('MAT_C1', 'Candidate material')"
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
