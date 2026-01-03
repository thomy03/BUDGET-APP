"""
Pytest configuration and fixtures for Budget Famille v2.3 testing.
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

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