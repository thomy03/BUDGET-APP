"""
Pytest plugins - loaded very early before conftest.py
Sets environment variables for test mode.
"""
import os

# CRITICAL: Set test environment BEFORE any other imports
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-key-for-pytest-minimum-32-characters"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
