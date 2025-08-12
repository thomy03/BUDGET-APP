#!/usr/bin/env python3
"""
Database migration to add secure user management tables
Replaces hardcoded authentication with database-backed users
"""

import logging
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from models.database import engine, Base, migrate_schema
from models.user import User, UserSession, create_default_admin_user
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_user_tables():
    """Create user management tables"""
    try:
        logger.info("Creating user management tables...")
        
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine, tables=[User.__table__, UserSession.__table__])
        
        logger.info("✅ User tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating user tables: {e}")
        return False


def migrate_existing_data():
    """Migrate any existing data if needed"""
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Create default admin user with secure password
        admin_user, generated_password = create_default_admin_user(db, force_new_password=True)
        
        if generated_password:
            logger.info("="*60)
            logger.info("🔐 DEFAULT ADMIN USER CREATED")
            logger.info("="*60)
            logger.info(f"Username: {admin_user.username}")
            logger.info(f"Password: {generated_password}")
            logger.info("="*60)
            logger.info("⚠️  IMPORTANT SECURITY NOTES:")
            logger.info("1. Store this password securely")
            logger.info("2. Change password on first login")
            logger.info("3. This password will not be shown again")
            logger.info("4. Password change is enforced on first login")
            logger.info("="*60)
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error migrating data: {e}")
        return False


def verify_migration():
    """Verify the migration was successful"""
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Check if tables exist and have data
        user_count = db.query(User).count()
        logger.info(f"✅ Users table verified: {user_count} users")
        
        # Verify admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user:
            logger.info(f"✅ Admin user verified: {admin_user.username} (ID: {admin_user.id})")
            logger.info(f"   - Active: {admin_user.is_active}")
            logger.info(f"   - Admin: {admin_user.is_admin}")
            logger.info(f"   - Force password change: {admin_user.force_password_change}")
        else:
            logger.error("❌ Admin user not found")
            return False
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying migration: {e}")
        return False


def main():
    """Main migration function"""
    logger.info("🚀 Starting user management migration...")
    logger.info(f"Database URL: {settings.database.database_url}")
    
    # Step 1: Create tables
    if not create_user_tables():
        logger.error("❌ Failed to create user tables")
        sys.exit(1)
    
    # Step 2: Migrate data
    if not migrate_existing_data():
        logger.error("❌ Failed to migrate data")
        sys.exit(1)
    
    # Step 3: Verify migration
    if not verify_migration():
        logger.error("❌ Migration verification failed")
        sys.exit(1)
    
    logger.info("🎉 User management migration completed successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Update your application to use the new authentication system")
    logger.info("2. Remove hardcoded credentials from auth.py")
    logger.info("3. Test login with the generated admin credentials")
    logger.info("4. Set up additional users as needed")


if __name__ == "__main__":
    main()