"""
Conftest for tests folder - exclude tests with missing fixtures.
"""
collect_ignore = [
    "test_api_core.py",  # requires 'test_db' fixture
]
