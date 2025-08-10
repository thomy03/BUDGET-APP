#!/usr/bin/env python3
"""
Final validation of the 400 Bad Request fix for CSV import
"""

import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"

def test_original_scenario():
    """Test the original failing scenario that was reported"""
    logger.info("🔍 Testing original failing scenario...")
    
    # 1. Authenticate
    auth_response = requests.post(
        f"{BASE_URL}/token",
        data={"username": "admin", "password": "secret", "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if auth_response.status_code != 200:
        logger.error(f"❌ Authentication failed: {auth_response.status_code}")
        return False
        
    token = auth_response.json()["access_token"]
    logger.info("✅ Authentication successful")
    
    # 2. Test import with the original CSV file
    csv_file = "01_happy_path_janvier_2024.csv"
    
    with open(csv_file, 'rb') as f:
        files = {'file': (csv_file, f, 'text/csv')}
        headers = {'Authorization': f'Bearer {token}'}
        
        import_response = requests.post(
            f"{BASE_URL}/import",
            files=files,
            headers=headers
        )
    
    # 3. Validate result
    logger.info(f"📊 Import response status: {import_response.status_code}")
    
    if import_response.status_code == 200:
        data = import_response.json()
        logger.info("✅ Import successful!")
        logger.info(f"📊 Import ID: {data.get('importId')}")
        logger.info(f"📊 Months detected: {len(data.get('months', []))}")
        logger.info(f"📊 Duplicates found: {data.get('duplicatesCount', 0)}")
        logger.info(f"📊 Suggested month: {data.get('suggestedMonth')}")
        return True
    else:
        logger.error(f"❌ Import failed with {import_response.status_code}")
        try:
            error_data = import_response.json()
            logger.error(f"❌ Error: {error_data.get('detail', 'Unknown error')}")
        except:
            logger.error(f"❌ Raw response: {import_response.text}")
        return False

def main():
    logger.info("🚀 FINAL VALIDATION: Budget Famille v2.3 CSV Import Fix")
    logger.info("=" * 60)
    logger.info("Testing scenario that originally returned 400 Bad Request...")
    logger.info("")
    
    success = test_original_scenario()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 VALIDATION RESULT")
    logger.info("=" * 60)
    
    if success:
        logger.info("🎉 SUCCESS: CSV Import 400 Error has been RESOLVED!")
        logger.info("")
        logger.info("✅ SUMMARY OF FIX:")
        logger.info("   - Issue: Column mapping missing French CSV headers")
        logger.info("   - Root cause: 'Date' column not mapped to 'dateOp'")
        logger.info("   - Solution: Added French column mappings in normalize_cols()")
        logger.info("   - Files modified: app.py (lines 360-362)")
        logger.info("")
        logger.info("🔧 TECHNICAL DETAILS:")
        logger.info("   - Added mapping: 'date' → 'dateOp'")
        logger.info("   - Added mapping: 'description' → 'label'") 
        logger.info("   - Added mapping: 'montant' → 'amount'")
        logger.info("   - Added mapping: 'compte' → 'accountLabel'")
        logger.info("   - Added mapping: 'categorie' → 'category'")
        logger.info("")
        logger.info("✅ The import endpoint now correctly processes French CSV files!")
        
    else:
        logger.error("❌ FAILURE: CSV Import still failing")
        logger.error("   Additional investigation required")
        
    logger.info("=" * 60)

if __name__ == "__main__":
    main()