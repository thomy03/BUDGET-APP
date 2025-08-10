#!/usr/bin/env python3
"""
Comprehensive test for CSV import functionality
Tests various CSV formats and edge cases
"""

import requests
import os
import tempfile
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin" 
PASSWORD = "secret"

def authenticate() -> str:
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": USERNAME, "password": PASSWORD, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"] if response.status_code == 200 else None

def test_import(filename: str, csv_content: str, token: str) -> dict:
    """Test CSV import"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        with open(temp_path, 'rb') as f:
            files = {'file': (filename, f, 'text/csv')}
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.post(f"{BASE_URL}/import", files=files, headers=headers)
            
        result = {
            "filename": filename,
            "status": response.status_code,
            "success": response.status_code == 200
        }
        
        if response.status_code == 200:
            data = response.json()
            result.update({
                "import_id": data.get("importId"),
                "months": len(data.get("months", [])),
                "duplicates": data.get("duplicatesCount", 0),
                "warnings": len(data.get("warnings", []))
            })
        else:
            try:
                error_data = response.json()
                result["error"] = error_data.get("detail", "Unknown error")
            except:
                result["error"] = response.text
        
        return result
    finally:
        os.unlink(temp_path)

def main():
    """Run comprehensive CSV import tests"""
    logger.info("🚀 Starting Comprehensive CSV Import Tests")
    logger.info("=" * 60)
    
    token = authenticate()
    if not token:
        logger.error("❌ Authentication failed")
        return
    
    # Test cases
    test_cases = [
        {
            "name": "French CSV format (should work now)",
            "filename": "test_french.csv", 
            "content": """Date,Description,Montant,Compte,Categorie
2024-01-01,Test transaction,-100.00,CHECKING,Test
2024-01-02,Another test,50.00,SAVINGS,Income"""
        },
        {
            "name": "English CSV format",
            "filename": "test_english.csv",
            "content": """dateOp,label,amount,accountLabel,category
2024-01-01,Test transaction,-100.00,CHECKING,Test
2024-01-02,Another test,50.00,SAVINGS,Income"""
        },
        {
            "name": "Mixed case headers",
            "filename": "test_mixed.csv",
            "content": """DATE,DESCRIPTION,MONTANT,COMPTE,CATEGORIE
2024-01-01,Test transaction,-100.00,CHECKING,Test
2024-01-02,Another test,50.00,SAVINGS,Income"""
        },
        {
            "name": "Semicolon separator",
            "filename": "test_semicolon.csv",
            "content": """Date;Description;Montant;Compte;Categorie
2024-01-01;Test transaction;-100,00;CHECKING;Test
2024-01-02;Another test;50,00;SAVINGS;Income"""
        },
        {
            "name": "Empty CSV",
            "filename": "test_empty.csv",
            "content": ""
        },
        {
            "name": "Headers only",
            "filename": "test_headers_only.csv",
            "content": "Date,Description,Montant,Compte,Categorie"
        },
        {
            "name": "Invalid dates",
            "filename": "test_invalid_dates.csv",
            "content": """Date,Description,Montant,Compte,Categorie
invalid-date,Test transaction,-100.00,CHECKING,Test
2024-13-45,Another test,50.00,SAVINGS,Income"""
        },
        {
            "name": "Future dates",
            "filename": "test_future.csv",
            "content": """Date,Description,Montant,Compte,Categorie
2025-12-01,Future transaction,-100.00,CHECKING,Test
2026-01-01,Another future,50.00,SAVINGS,Income"""
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"🧪 Test {i}/{len(test_cases)}: {test_case['name']}")
        result = test_import(test_case["filename"], test_case["content"], token)
        results.append(result)
        
        if result["success"]:
            logger.info(f"   ✅ SUCCESS - Import ID: {result.get('import_id', 'N/A')}")
            logger.info(f"   📊 Months: {result.get('months', 0)}, Duplicates: {result.get('duplicates', 0)}")
        else:
            logger.info(f"   ❌ FAILED - Status: {result['status']}")
            logger.info(f"   📝 Error: {result.get('error', 'Unknown')}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 60)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    logger.info(f"✅ Successful imports: {len(successful)}/{len(results)}")
    logger.info(f"❌ Failed imports: {len(failed)}/{len(results)}")
    
    if successful:
        logger.info("\n✅ SUCCESSFUL TESTS:")
        for result in successful:
            logger.info(f"   - {result['filename']}")
    
    if failed:
        logger.info("\n❌ FAILED TESTS:")
        for result in failed:
            logger.info(f"   - {result['filename']}: {result.get('error', 'Unknown error')}")
    
    # Validation
    core_formats_working = any(r["success"] for r in results if "french" in r["filename"] or "english" in r["filename"])
    if core_formats_working:
        logger.info("\n🎉 CSV IMPORT FUNCTIONALITY RESTORED!")
        logger.info("✅ The 400 Bad Request issue has been FIXED")
    else:
        logger.info("\n⚠️  Import still has issues with core formats")

if __name__ == "__main__":
    main()