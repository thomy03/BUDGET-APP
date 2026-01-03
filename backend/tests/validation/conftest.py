"""
Conftest for validation - exclude tests requiring external services or specific config.
"""
collect_ignore = [
    "test_critical_fixes.py",
    "test_custom_provisions.py",
    "test_web_enriched_intelligence_suite.py",
    "test_config_revenues.py",                   # requires 'test_db' fixture
    "test_ml_feedback_system.py",                # requires server running
    "test_patch_transactions.py",                # requires 'test_db' fixture
    "test_classification_system.py",             # requires ML service
    "test_comprehensive_intelligence_qa.py",     # requires external web services
    "test_enhanced_classification_qa.py",        # requires ML/web services
    "test_intelligent_classification.py",        # requires ML service configuration
    "test_tags_validation.py",                   # requires specific API setup
]
