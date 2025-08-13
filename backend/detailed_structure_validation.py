#!/usr/bin/env python3
"""
Detailed structure validation for Budget API dashboard endpoints
Validates exact data structure and checks for undefined/null values
"""

import json
import requests
from typing import Dict, Any, List, Union

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

def validate_totals_object(data: Dict[str, Any], endpoint_name: str) -> Dict[str, Any]:
    """Validate totals object structure"""
    
    # Expected structure based on request
    expected_totals_fields = {
        "total_expenses": {"type": "number", "required": True},
        "total_fixed": {"type": "number", "required": True}, 
        "total_variable": {"type": "number", "required": True}
    }
    
    validation = {
        "endpoint": endpoint_name,
        "has_totals_object": False,
        "totals_structure_valid": False,
        "missing_totals_fields": [],
        "invalid_totals_values": [],
        "actual_totals_structure": None
    }
    
    # Check if totals object exists
    if "totals" in data:
        validation["has_totals_object"] = True
        totals = data["totals"]
        validation["actual_totals_structure"] = totals
        
        if isinstance(totals, dict):
            validation["totals_structure_valid"] = True
            
            # Check each expected field
            for field, config in expected_totals_fields.items():
                if field not in totals:
                    validation["missing_totals_fields"].append(field)
                else:
                    value = totals[field]
                    if value is None or value == "undefined":
                        validation["invalid_totals_values"].append({
                            "field": field,
                            "value": value,
                            "issue": "null_or_undefined"
                        })
                    elif not isinstance(value, (int, float)):
                        validation["invalid_totals_values"].append({
                            "field": field,
                            "value": value,
                            "issue": "not_numeric"
                        })
        else:
            validation["totals_structure_valid"] = False
    
    return validation

def validate_numeric_defaults(data: Union[Dict[str, Any], List[Any]], endpoint_name: str) -> List[Dict[str, Any]]:
    """Validate that all numeric fields have proper defaults (not None/undefined)"""
    
    issues = []
    
    def check_value(key: str, value: Any, path: str = ""):
        full_path = f"{path}.{key}" if path else key
        
        # Fields that are allowed to be null/None
        allowed_null_fields = [
            "start_date", "end_date", "updated_at", "last_login", 
            "locked_until", "description", "progress_percentage"
        ]
        
        # Check for problematic values
        if value is None:
            # Skip validation for fields that are allowed to be null
            if key not in allowed_null_fields:
                issues.append({
                    "endpoint": endpoint_name,
                    "field": full_path,
                    "value": None,
                    "issue": "null_value",
                    "severity": "error"
                })
        elif isinstance(value, str) and value.lower() in ['undefined', 'null', 'none']:
            issues.append({
                "endpoint": endpoint_name,
                "field": full_path,
                "value": value,
                "issue": "string_undefined",
                "severity": "error"
            })
        elif isinstance(value, dict):
            # Recursively check nested objects
            for nested_key, nested_value in value.items():
                check_value(nested_key, nested_value, full_path)
        elif isinstance(value, list) and len(value) > 0:
            # Check first few items in arrays
            for i, item in enumerate(value[:3]):
                if isinstance(item, dict):
                    for nested_key, nested_value in item.items():
                        check_value(nested_key, nested_value, f"{full_path}[{i}]")
    
    # Check all fields in the data
    if isinstance(data, dict):
        for key, value in data.items():
            check_value(key, value)
    elif isinstance(data, list):
        for i, item in enumerate(data[:5]):  # Check first 5 items
            if isinstance(item, dict):
                for key, value in item.items():
                    check_value(key, value, f"[{i}]")
            else:
                check_value(f"item_{i}", item, "")
    
    return issues

def test_detailed_endpoint(endpoint: str, token: str) -> Dict[str, Any]:
    """Test endpoint with detailed validation"""
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    
    result = {
        "endpoint": endpoint,
        "status_code": response.status_code,
        "success": response.status_code == 200,
        "data": None,
        "validation_issues": [],
        "totals_validation": None
    }
    
    if response.status_code == 200:
        data = response.json()
        result["data"] = data
        
        # Validate numeric defaults
        numeric_issues = validate_numeric_defaults(data, endpoint)
        result["validation_issues"].extend(numeric_issues)
        
        # Validate totals object if it should exist
        if endpoint in ["/summary/enhanced", "/summary"]:
            totals_validation = validate_totals_object(data, endpoint)
            result["totals_validation"] = totals_validation
            
            if not totals_validation["totals_structure_valid"]:
                result["validation_issues"].append({
                    "endpoint": endpoint,
                    "field": "totals",
                    "issue": "missing_or_invalid_totals_object",
                    "severity": "error"
                })
    else:
        result["validation_issues"].append({
            "endpoint": endpoint,
            "field": "response",
            "issue": f"http_error_{response.status_code}",
            "severity": "error"
        })
    
    return result

def main():
    """Main validation function"""
    print("🔬 Detailed Structure Validation for Dashboard Endpoints")
    print("=" * 60)
    
    # Get authentication token
    token = get_auth_token()
    
    # Define endpoints to test
    endpoints = [
        f"/summary/enhanced?month={TEST_MONTH}",
        f"/summary?month={TEST_MONTH}",
        "/config",
        "/fixed-lines",
        "/custom-provisions"
    ]
    
    all_results = []
    total_issues = 0
    
    # Test each endpoint in detail
    for endpoint in endpoints:
        print(f"\n🔍 Detailed validation: {endpoint}")
        result = test_detailed_endpoint(endpoint, token)
        all_results.append(result)
        
        if result["success"]:
            print(f"  ✅ HTTP Status: {result['status_code']}")
            
            # Check for validation issues
            issues = result["validation_issues"]
            if issues:
                print(f"  ⚠️  Found {len(issues)} validation issues:")
                for issue in issues:
                    severity_icon = "🚨" if issue["severity"] == "error" else "⚠️"
                    print(f"    {severity_icon} {issue['field']}: {issue['issue']}")
                    if "value" in issue:
                        print(f"       Value: {issue['value']}")
                total_issues += len(issues)
            else:
                print("  ✅ No validation issues found")
            
            # Check totals validation
            if result["totals_validation"]:
                tv = result["totals_validation"]
                if tv["has_totals_object"]:
                    print("  📊 Totals object: Present")
                    if tv["totals_structure_valid"]:
                        print("  ✅ Totals structure: Valid")
                    else:
                        print("  ❌ Totals structure: Invalid")
                    
                    if tv["missing_totals_fields"]:
                        print(f"  ❌ Missing totals fields: {tv['missing_totals_fields']}")
                    
                    if tv["invalid_totals_values"]:
                        print(f"  ❌ Invalid totals values: {tv['invalid_totals_values']}")
                else:
                    print("  ❌ Totals object: Missing")
        else:
            print(f"  ❌ HTTP Status: {result['status_code']}")
            total_issues += 1
    
    # Summary report
    print("\n" + "=" * 60)
    print("📋 Detailed Validation Summary")
    print("=" * 60)
    
    successful_endpoints = sum(1 for r in all_results if r["success"])
    
    print(f"✅ Successful endpoints: {successful_endpoints}/{len(endpoints)}")
    print(f"⚠️  Total validation issues found: {total_issues}")
    
    if total_issues == 0:
        print("\n🎉 All endpoints return proper data structure with valid defaults!")
        print("   ✅ No null/undefined values found")
        print("   ✅ All required fields present")
        print("   ✅ All numeric fields have proper defaults")
    else:
        print(f"\n🔧 {total_issues} issues need to be fixed:")
        
        # Group issues by type
        issue_types = {}
        for result in all_results:
            for issue in result["validation_issues"]:
                issue_type = issue["issue"]
                if issue_type not in issue_types:
                    issue_types[issue_type] = []
                issue_types[issue_type].append(f"{result['endpoint']}.{issue['field']}")
        
        for issue_type, locations in issue_types.items():
            print(f"  - {issue_type}: {len(locations)} occurrences")
            for location in locations[:3]:  # Show first 3
                print(f"    • {location}")
            if len(locations) > 3:
                print(f"    • ... and {len(locations) - 3} more")
    
    # Detailed data structure samples
    print("\n" + "=" * 60)
    print("📊 Sample Data Structures")
    print("=" * 60)
    
    for result in all_results:
        if result["success"] and result["data"]:
            print(f"\n🔍 {result['endpoint']}:")
            data = result["data"]
            
            # Show structure overview
            if isinstance(data, dict):
                print(f"  Type: dict with {len(data)} keys")
                for key, value in list(data.items())[:5]:  # First 5 keys
                    value_type = type(value).__name__
                    if isinstance(value, dict):
                        detail = f"({len(value)} keys)"
                    elif isinstance(value, list):
                        detail = f"({len(value)} items)"
                    elif isinstance(value, str):
                        detail = f"'{value[:30]}...'" if len(str(value)) > 30 else f"'{value}'"
                    else:
                        detail = str(value)
                    
                    print(f"    {key}: {value_type} {detail}")
                
                if len(data) > 5:
                    print(f"    ... and {len(data) - 5} more keys")
            elif isinstance(data, list):
                print(f"  Type: list with {len(data)} items")
                if len(data) > 0:
                    first_item = data[0]
                    if isinstance(first_item, dict):
                        print(f"    First item keys: {list(first_item.keys())}")
    
    return 0 if total_issues == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)