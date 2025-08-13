#!/usr/bin/env python3
"""
Totals structure verification for Budget API dashboard endpoints
Validates that the totals object contains the expected fields with proper defaults
"""

import json
import requests
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TEST_MONTH = "2025-08"

def get_auth_token() -> str:
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": "admin", "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]

def validate_totals_structure(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the totals object structure as requested by the user"""
    
    expected_totals_fields = {
        "total_expenses": {"type": "number", "required": True},
        "total_fixed": {"type": "number", "required": True}, 
        "total_variable": {"type": "number", "required": True}
    }
    
    validation = {
        "endpoint": endpoint,
        "has_totals_object": False,
        "totals_structure_correct": False,
        "all_required_fields_present": False,
        "all_fields_have_valid_defaults": False,
        "missing_fields": [],
        "invalid_values": [],
        "totals_data": None
    }
    
    if "totals" in data:
        validation["has_totals_object"] = True
        totals = data["totals"]
        validation["totals_data"] = totals
        
        if isinstance(totals, dict):
            validation["totals_structure_correct"] = True
            
            # Check required fields
            missing_fields = []
            invalid_values = []
            
            for field, config in expected_totals_fields.items():
                if field not in totals:
                    missing_fields.append(field)
                else:
                    value = totals[field]
                    if value is None:
                        invalid_values.append(f"{field}: null (should have default 0)")
                    elif isinstance(value, str) and value.lower() in ['undefined', 'null', 'none']:
                        invalid_values.append(f"{field}: '{value}' (should be numeric)")
                    elif not isinstance(value, (int, float)):
                        invalid_values.append(f"{field}: {type(value).__name__} (should be numeric)")
            
            validation["missing_fields"] = missing_fields
            validation["invalid_values"] = invalid_values
            validation["all_required_fields_present"] = len(missing_fields) == 0
            validation["all_fields_have_valid_defaults"] = len(invalid_values) == 0
    
    return validation

def main():
    """Main verification function"""
    print("🔍 Totals Object Structure Verification")
    print("=" * 50)
    print("Verifying that dashboard endpoints return totals object with:")
    print("  - total_expenses: number with default value (0)")
    print("  - total_fixed: number with default value (0)")
    print("  - total_variable: number with default value (0)")
    print("  - Never return undefined for required fields")
    print()
    
    # Get authentication token
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test the required endpoints
    endpoints_to_test = [
        f"/summary/enhanced?month={TEST_MONTH}",
        f"/summary?month={TEST_MONTH}"
    ]
    
    all_passed = True
    
    for endpoint in endpoints_to_test:
        print(f"🧪 Testing {endpoint}")
        
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                validation = validate_totals_structure(endpoint, data)
                
                if validation["has_totals_object"]:
                    print(f"  ✅ Has totals object")
                    
                    if validation["totals_structure_correct"]:
                        print(f"  ✅ Totals is a proper object (dict)")
                        
                        if validation["all_required_fields_present"]:
                            print(f"  ✅ All required fields present")
                        else:
                            print(f"  ❌ Missing required fields: {validation['missing_fields']}")
                            all_passed = False
                        
                        if validation["all_fields_have_valid_defaults"]:
                            print(f"  ✅ All fields have valid numeric defaults")
                        else:
                            print(f"  ❌ Invalid field values: {validation['invalid_values']}")
                            all_passed = False
                        
                        # Show actual values
                        totals = validation["totals_data"]
                        print(f"  📊 Actual totals values:")
                        for field in ["total_expenses", "total_fixed", "total_variable"]:
                            if field in totals:
                                value = totals[field]
                                print(f"    {field}: {value} ({type(value).__name__})")
                            else:
                                print(f"    {field}: MISSING")
                        
                    else:
                        print(f"  ❌ Totals object is not a dict: {type(validation['totals_data'])}")
                        all_passed = False
                else:
                    print(f"  ❌ No totals object found")
                    all_passed = False
                    
            else:
                print(f"  ❌ HTTP Error: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            all_passed = False
        
        print()
    
    # Final report
    print("=" * 50)
    if all_passed:
        print("🎉 SUCCESS: All endpoints return proper totals object structure!")
        print("✅ totals object with total_expenses, total_fixed, total_variable")
        print("✅ All numeric fields have proper defaults (not undefined)")
        print("✅ Never return undefined for required fields")
        return 0
    else:
        print("❌ FAILED: Some endpoints have issues with totals structure")
        print("🔧 Fix required for proper dashboard data structure")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)