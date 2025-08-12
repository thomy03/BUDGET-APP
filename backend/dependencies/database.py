"""
Database dependencies for Budget Famille v2.3
"""
from sqlalchemy.orm import Session
from models.database import get_db

# Re-export get_db for use in routers
def get_database() -> Session:
    """
    Get database session
    Direct wrapper around models.database.get_db
    """
    yield from get_db()