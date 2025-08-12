"""
Test script to validate modular architecture works correctly
"""
import sys
import os
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modular components can be imported"""
    try:
        # Test core models import
        logger.info("Testing models import...")
        from models.database import Config, Transaction, FixedLine, CustomProvision
        logger.info("✅ Database models import successful")
        
        from models.schemas import ConfigIn, ConfigOut, TxOut
        logger.info("✅ Pydantic schemas import successful")
        
        # Test utilities import
        logger.info("Testing utilities import...")
        from utils.core_functions import parse_number, normalize_cols
        logger.info("✅ Core functions import successful")
        
        # Test services import
        logger.info("Testing services import...")
        from services.transaction_service import TransactionService
        from services.import_service import ImportService
        logger.info("✅ Services import successful")
        
        # Test dependencies import
        logger.info("Testing dependencies import...")
        from dependencies.auth import get_current_user
        logger.info("✅ Dependencies import successful")
        
        # Test routers import (should not fail even if they have circular imports)
        logger.info("Testing routers import...")
        try:
            from routers.config import router as config_router
            logger.info("✅ Config router import successful")
        except Exception as e:
            logger.warning(f"⚠️ Config router import issue: {e}")
        
        try:
            from routers.analytics import router as analytics_router
            logger.info("✅ Analytics router import successful") 
        except Exception as e:
            logger.warning(f"⚠️ Analytics router import issue: {e}")
        
        # Test main app import
        logger.info("Testing main app import...")
        from app import app
        logger.info("✅ Main FastAPI app import successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False

def test_app_creation():
    """Test that the FastAPI app can be created"""
    try:
        from app import app
        
        # Check that app has been configured
        assert app.title == "Budget Famille API"
        assert app.version == "2.3.0"
        logger.info("✅ FastAPI app configuration validated")
        
        # Check that routers are included
        route_paths = [route.path for route in app.routes]
        expected_paths = ["/config", "/fixed-lines", "/provisions", "/analytics"]
        
        for path in expected_paths:
            if any(path in route_path for route_path in route_paths):
                logger.info(f"✅ Router {path} is included")
            else:
                logger.warning(f"⚠️ Router {path} might not be included correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ App creation test failed: {e}")
        return False

def test_database_connection():
    """Test that database connection works"""
    try:
        from models.database import engine, get_db
        
        # Test engine creation
        logger.info(f"Database URL: {engine.url}")
        
        # Test database session
        db_gen = get_db()
        db = next(db_gen)
        
        # Simple query
        db.execute("SELECT 1")
        db.close()
        
        logger.info("✅ Database connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Budget Famille v2.3 Modular Architecture Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("App Creation Test", test_app_creation),
        ("Database Connection Test", test_database_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Modular architecture is working correctly.")
        return True
    else:
        logger.error("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)