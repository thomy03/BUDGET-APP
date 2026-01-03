"""
Conftest for archive folder - disable all test collection.
These are archived/legacy tests that should not be run.
"""
import os

# Collect ignore - exclude all test files in this directory
collect_ignore_glob = ["test_*.py"]

# Alternative: list all files explicitly
collect_ignore = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith("test_")]
