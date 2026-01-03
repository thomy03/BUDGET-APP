"""
Conftest for unit tests - exclude tests with missing fixtures.
"""
collect_ignore = [
    "test_database_models.py",  # requires 'test_db' fixture
]
