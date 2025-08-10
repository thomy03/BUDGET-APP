#!/usr/bin/env python3
"""
Diagnostic test to identify the 400 Bad Request error in CSV import endpoint.
This script performs step-by-step validation to identify where the import fails.
"""

import requests
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin"
PASSWORD = "secret"
CSV_FILE = "01_happy_path_janvier_2024.csv"

def authenticate() -> str:
    """Authenticate and return JWT token"""
    logger.info("🔐 Authenticating...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/token",
            data={
                "username": USERNAME,
                "password": PASSWORD,
                "grant_type": "password"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            logger.info("✅ Authentication successful")
            return token
        else:
            logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return None

def check_csv_file(file_path: str) -> dict:
    """Analyze CSV file properties"""
    logger.info(f"📄 Analyzing CSV file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"❌ CSV file not found: {file_path}")
        return {"exists": False}
    
    file_info = {
        "exists": True,
        "size": os.path.getsize(file_path),
        "extension": Path(file_path).suffix.lower()
    }
    
    # Read first few lines to analyze content
    try:
        with open(file_path, 'rb') as f:
            first_bytes = f.read(1024)
            file_info["first_bytes_length"] = len(first_bytes)
            file_info["has_bom"] = first_bytes.startswith(b'\xef\xbb\xbf')
            
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            file_info["first_line"] = first_line
            file_info["separators_detected"] = []
            
            for sep in [',', ';', '\t', '|']:
                if sep in first_line:
                    file_info["separators_detected"].append(sep)
                    
            # Check for common CSV headers
            common_headers = ['date', 'dateop', 'dateval', 'label', 'libelle', 'description', 
                            'montant', 'amount', 'compte', 'account', 'category', 'categorie']
            file_info["has_common_headers"] = any(header in first_line.lower() for header in common_headers)
            
    except Exception as e:
        file_info["read_error"] = str(e)
        
    logger.info(f"📊 File analysis: {file_info}")
    return file_info

def test_import_endpoint(token: str, file_path: str) -> dict:
    """Test the import endpoint with detailed error analysis"""
    logger.info("🚀 Testing import endpoint...")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            headers = {'Authorization': f'Bearer {token}'}
            
            logger.info(f"📤 Uploading file: {os.path.basename(file_path)}")
            logger.info(f"📊 File size: {os.path.getsize(file_path)} bytes")
            
            response = requests.post(
                f"{BASE_URL}/import",
                files=files,
                headers=headers
            )
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get("content-type", ""),
            }
            
            # Try to parse response body
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    result["json_response"] = response.json()
                else:
                    result["text_response"] = response.text
            except Exception as e:
                result["response_parse_error"] = str(e)
                result["raw_response"] = response.text[:500]
            
            # Log detailed response
            logger.info(f"📊 Response Status: {response.status_code}")
            logger.info(f"📊 Response Headers: {result['headers']}")
            
            if response.status_code == 400:
                logger.error("❌ 400 Bad Request received")
                if "json_response" in result and "detail" in result["json_response"]:
                    logger.error(f"❌ Error detail: {result['json_response']['detail']}")
                elif "text_response" in result:
                    logger.error(f"❌ Error response: {result['text_response']}")
                    
            elif response.status_code == 200:
                logger.info("✅ Import successful!")
                if "json_response" in result:
                    import_data = result["json_response"]
                    logger.info(f"📊 Import ID: {import_data.get('importId')}")
                    logger.info(f"📊 Months detected: {len(import_data.get('months', []))}")
                    logger.info(f"📊 Duplicates: {import_data.get('duplicatesCount', 0)}")
                    
            return result
            
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return {"error": str(e)}

def check_server_logs():
    """Check if server logs are accessible"""
    logger.info("📋 Checking for server logs...")
    
    # Look for common log files
    log_files = [
        "server.log",
        "app.log", 
        "backend.log",
        "uvicorn.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            logger.info(f"📄 Found log file: {log_file}")
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 10:
                        logger.info(f"📄 Last 5 lines from {log_file}:")
                        for line in lines[-5:]:
                            logger.info(f"  {line.strip()}")
            except Exception as e:
                logger.error(f"❌ Error reading {log_file}: {e}")
        else:
            logger.info(f"❌ Log file not found: {log_file}")

def validate_expected_csv_format(file_path: str) -> bool:
    """Validate if CSV matches expected format from the application"""
    logger.info("🔍 Validating CSV format against application expectations...")
    
    expected_columns = [
        "dateOp", "dateVal", "label", "category", "categoryParent",
        "supplierFound", "amount", "comment", "accountNum", "accountLabel", "accountbalance"
    ]
    
    try:
        import pandas as pd
        import io
        
        # Try to read CSV with various separators
        content = open(file_path, 'r', encoding='utf-8').read()
        
        for sep in [',', ';', '\t', '|']:
            try:
                df = pd.read_csv(io.StringIO(content), sep=sep, dtype=str)
                if df.shape[1] >= 3:  # At least 3 columns
                    logger.info(f"✅ CSV readable with separator '{sep}', columns: {list(df.columns)}")
                    
                    # Check if columns match expected format
                    columns_lower = [col.lower() for col in df.columns]
                    expected_lower = [col.lower() for col in expected_columns]
                    
                    matches = []
                    for expected_col in expected_lower:
                        # Check for partial matches
                        for actual_col in columns_lower:
                            if expected_col in actual_col or actual_col in expected_col:
                                matches.append(f"{expected_col} ~ {actual_col}")
                                
                    logger.info(f"📊 Column matches found: {matches}")
                    
                    # Check if we have dateOp-like column
                    date_cols = [col for col in df.columns if 'date' in col.lower() or 'op' in col.lower()]
                    logger.info(f"📊 Date columns found: {date_cols}")
                    
                    # Check if we have amount-like column  
                    amount_cols = [col for col in df.columns if 'amount' in col.lower() or 'montant' in col.lower()]
                    logger.info(f"📊 Amount columns found: {amount_cols}")
                    
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️  Failed to read with separator '{sep}': {e}")
                
        logger.error("❌ CSV not readable with any separator")
        return False
        
    except Exception as e:
        logger.error(f"❌ CSV validation error: {e}")
        return False

def main():
    """Main diagnostic function"""
    logger.info("🚀 Starting CSV Import 400 Error Diagnostic")
    logger.info("=" * 60)
    
    # Step 1: Check CSV file
    csv_path = CSV_FILE
    if not os.path.exists(csv_path):
        # Try to find CSV file in common locations
        possible_paths = [
            f"../{CSV_FILE}",
            f"../data/{CSV_FILE}",
            f"./data/{CSV_FILE}",
            f"./test_data/{CSV_FILE}"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                csv_path = path
                break
        else:
            logger.error(f"❌ CSV file not found in any location: {CSV_FILE}")
            return
    
    file_info = check_csv_file(csv_path)
    
    if not file_info["exists"]:
        logger.error("❌ Cannot proceed without CSV file")
        return
        
    # Step 2: Validate CSV format
    is_valid_csv = validate_expected_csv_format(csv_path)
    
    # Step 3: Authenticate
    token = authenticate()
    if not token:
        logger.error("❌ Cannot proceed without authentication")
        return
    
    # Step 4: Test import endpoint
    import_result = test_import_endpoint(token, csv_path)
    
    # Step 5: Check server logs
    check_server_logs()
    
    # Summary
    logger.info("=" * 60)
    logger.info("📋 DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"📄 CSV File: {csv_path}")
    logger.info(f"📊 File Size: {file_info.get('size', 'unknown')} bytes")
    logger.info(f"📊 File Extension: {file_info.get('extension', 'unknown')}")
    logger.info(f"✅ CSV Format Valid: {is_valid_csv}")
    logger.info(f"🔐 Authentication: {'Success' if token else 'Failed'}")
    logger.info(f"📊 Import Status: {import_result.get('status_code', 'Error')}")
    
    if import_result.get('status_code') == 400:
        logger.error("❌ ROOT CAUSE: 400 Bad Request")
        if "json_response" in import_result:
            detail = import_result["json_response"].get("detail", "No detail provided")
            logger.error(f"❌ Error Detail: {detail}")
            
            # Provide specific guidance based on error detail
            if "Fichier non sécurisé" in detail:
                logger.info("💡 SOLUTION: File security validation failed")
                logger.info("   - Check if CSV has proper separators (,;|)")  
                logger.info("   - Verify CSV headers match expected format")
                logger.info("   - Ensure file is not corrupted")
            elif "CSV illisible" in detail:
                logger.info("💡 SOLUTION: CSV parsing failed")
                logger.info("   - Check file encoding (should be UTF-8)")
                logger.info("   - Verify CSV format and separators")
            elif "Format de fichier non autorisé" in detail:
                logger.info("💡 SOLUTION: File type not allowed")
                logger.info("   - Ensure file has .csv extension")
            elif "Aucune transaction avec date valide trouvée" in detail:
                logger.info("💡 SOLUTION: No valid dates found")
                logger.info("   - Check dateOp column exists and has valid dates")
        
    logger.info("=" * 60)

if __name__ == "__main__":
    main()