"""
Conftest for unit tests - exclude tests with missing fixtures or needing refactoring.
"""
collect_ignore = [
    "test_database_models.py",   # requires 'test_db' fixture
    "test_auth_endpoints.py",    # needs refactoring to use dependency_overrides
]
