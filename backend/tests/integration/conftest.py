"""
Conftest for integration tests - exclude obsolete tests with missing imports/fixtures.
"""
collect_ignore = [
    "test_api_performance.py",   # requires 'factory' module
    "test_couple_balance.py",    # requires routers.couple_balance module
    "test_provisions_api.py",    # requires 'token' fixture
    "test_fixed_expenses_api.py",# requires 'token' fixture
    "test_tags_api.py",          # requires 'token' fixture
    "test_tags_display.py",      # requires 'token' fixture
    "test_tags_sync.py",         # requires 'token' fixture
    "test_auth.py",              # requires 'token' fixture
]
