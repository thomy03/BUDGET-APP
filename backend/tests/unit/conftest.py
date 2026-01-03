"""
Conftest for unit tests.

Note: test_database_models.py works when run alone but has isolation issues
when run with other tests that import the app (Base metadata conflict).
Run separately with: pytest tests/unit/test_database_models.py -v
"""
collect_ignore = [
    "test_database_models.py",   # Run separately to avoid Base metadata conflict
]
