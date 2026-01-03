"""
Conftest for validation - exclude obsolete tests with missing imports/fixtures.
"""
collect_ignore = [
    "test_critical_fixes.py",
    "test_custom_provisions.py",
    "test_web_enriched_intelligence_suite.py",
    "test_config_revenues.py",           # requires 'test_db' fixture
    "test_ml_feedback_system.py",        # requires server running
    "test_patch_transactions.py",        # requires 'test_db' fixture
]
