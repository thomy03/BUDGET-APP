"""
Pytest configuration and fixtures for Budget Famille v2.3 testing.
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Exclude legacy test files at root level (not in tests/ folder)
# These files have missing fixtures or import obsolete modules
collect_ignore = [f for f in os.listdir(backend_dir) if f.startswith("test_") and f.endswith(".py")]

@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        temp_path = tmp.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture
def mock_database():
    """Mock database connection for unit tests."""
    return MagicMock()

@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return {
        'id': 1,
        'date': '2024-01-15',
        'description': 'Test transaction',
        'amount': -50.0,
        'category': 'Alimentation',
        'membre': 'Thomas'
    }

@pytest.fixture
def sample_provision_data():
    """Sample provision data for testing."""
    return {
        'id': 1,
        'nom': 'Épargne vacances',
        'montant_mensuel': 200.0,
        'actif': True,
        'thomas_part': 100.0,
        'katia_part': 100.0
    }

@pytest.fixture
def sample_fixed_expense_data():
    """Sample fixed expense data for testing."""
    return {
        'id': 1,
        'nom': 'Loyer',
        'montant': 1200.0,
        'actif': True,
        'thomas_part': 600.0,
        'katia_part': 600.0
    }

@pytest.fixture
def sample_csv_data():
    """Sample CSV data for import testing."""
    return """Date,Libellé,Montant,Catégorie,Membre
2024-01-15,Courses Carrefour,-75.50,Alimentation,Thomas
2024-01-16,Salaire,3000.00,Revenus,Thomas
2024-01-17,Restaurant,-45.00,Sorties,Katia"""

@pytest.fixture
def auth_headers():
    """Mock authentication headers."""
    return {
        'Authorization': 'Bearer mock-jwt-token',
        'Content-Type': 'application/json'
    }


# --- Database Fixtures ---

@pytest.fixture(scope="function")
def test_db():
    """
    Create an in-memory SQLite database for testing.
    Creates all tables and provides a session, then cleans up after test.
    """
    from models.database import Base

    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """
    Create a FastAPI TestClient with database dependency override.
    """
    from fastapi.testclient import TestClient
    from app import app
    from models.database import get_db

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def token(client):
    """
    Get a valid JWT token for authenticated requests.
    Uses the test client to login and retrieve a token.
    """
    from unittest.mock import patch

    # Mock the authenticate_user to return a valid user
    mock_user = MagicMock()
    mock_user.username = "admin"
    mock_user.email = "admin@test.com"
    mock_user.full_name = "Test Admin"
    mock_user.disabled = False

    with patch('routers.auth.authenticate_user') as mock_auth, \
         patch('routers.auth.check_rate_limit', return_value=True):
        mock_auth.return_value = mock_user

        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "secret"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            # Fallback: return a mock token
            return "mock-test-jwt-token"


@pytest.fixture(scope="function")
def authenticated_client(client, token):
    """
    Create a client helper that includes authentication headers.
    """
    class AuthenticatedClient:
        def __init__(self, test_client, auth_token):
            self._client = test_client
            self._headers = {"Authorization": f"Bearer {auth_token}"}

        def get(self, url, **kwargs):
            headers = {**self._headers, **kwargs.pop("headers", {})}
            return self._client.get(url, headers=headers, **kwargs)

        def post(self, url, **kwargs):
            headers = {**self._headers, **kwargs.pop("headers", {})}
            return self._client.post(url, headers=headers, **kwargs)

        def put(self, url, **kwargs):
            headers = {**self._headers, **kwargs.pop("headers", {})}
            return self._client.put(url, headers=headers, **kwargs)

        def delete(self, url, **kwargs):
            headers = {**self._headers, **kwargs.pop("headers", {})}
            return self._client.delete(url, headers=headers, **kwargs)

        def patch(self, url, **kwargs):
            headers = {**self._headers, **kwargs.pop("headers", {})}
            return self._client.patch(url, headers=headers, **kwargs)

    return AuthenticatedClient(client, token)