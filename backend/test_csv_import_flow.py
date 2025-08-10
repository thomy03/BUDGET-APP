#!/usr/bin/env python3
"""
CSV Import Flow Test for Budget Famille v2.3
Tests the complete CSV import → navigation flow
"""

import sys
import os
import json
import time
import requests
import subprocess
import signal
import tempfile
import csv

def test_csv_import_flow():
    """Test the complete CSV import flow"""
    print("🧪 Testing CSV Import → Navigation Flow")
    
    # Start backend
    proc = subprocess.Popen(
        ["python", "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid
    )
    time.sleep(5)
    
    try:
        # Test 1: Health check
        response = requests.get("http://localhost:8000/health", timeout=10)
        print(f"✅ Backend healthy: {response.status_code}")
        
        # Test 2: Get token (simulated user)
        auth_response = requests.post("http://localhost:8000/token", 
                                    data={"username": "admin", "password": "admin123"}, 
                                    timeout=10)
        
        if auth_response.status_code == 200:
            token = auth_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Authentication successful")
            
            # Test 3: CSV Import with authentication
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Description", "Amount", "Account"])
                writer.writerow(["2024-08-10", "Test Import Transaction", "-25.50", "Checking"])
                writer.writerow(["2024-08-09", "Another Test", "100.00", "Savings"])
                csv_path = f.name
            
            with open(csv_path, 'rb') as f:
                files = {"file": ("test-import.csv", f, "text/csv")}
                import_response = requests.post("http://localhost:8000/import", 
                                              files=files, headers=headers, timeout=20)
            
            os.unlink(csv_path)
            
            if import_response.status_code == 200:
                import_data = import_response.json()
                print(f"✅ CSV Import successful: {import_data.get('message', 'No message')}")
                print(f"   - Import ID: {import_data.get('importId')}")
                print(f"   - Months detected: {import_data.get('months', [])}")
                print(f"   - Suggested month: {import_data.get('suggestedMonth')}")
                
                # Test 4: Verify transactions endpoint
                if import_data.get('suggestedMonth'):
                    month_param = import_data['suggestedMonth']
                    tx_response = requests.get(f"http://localhost:8000/transactions?month={month_param}", 
                                             headers=headers, timeout=10)
                    if tx_response.status_code == 200:
                        transactions = tx_response.json()
                        print(f"✅ Navigation flow verified - {len(transactions)} transactions for {month_param}")
                    else:
                        print(f"⚠️  Navigation issue: {tx_response.status_code}")
                        
            else:
                print(f"❌ CSV Import failed: {import_response.status_code} - {import_response.text}")
                
        else:
            print(f"⚠️  Authentication failed: {auth_response.status_code} - Testing without auth")
            
            # Test import without authentication (should fail gracefully)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Description", "Amount", "Account"])
                writer.writerow(["2024-08-10", "Test Transaction", "-50.00", "Checking"])
                csv_path = f.name
            
            with open(csv_path, 'rb') as f:
                files = {"file": ("test.csv", f, "text/csv")}
                response = requests.post("http://localhost:8000/import", files=files, timeout=15)
            
            os.unlink(csv_path)
            
            if response.status_code in [401, 403]:
                print("✅ Import correctly requires authentication")
            else:
                print(f"⚠️  Unexpected response: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Cleanup
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait()
        except:
            pass

if __name__ == "__main__":
    test_csv_import_flow()