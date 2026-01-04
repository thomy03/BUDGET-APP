#!/usr/bin/env python3
"""
Test script for provisions and couple balance API endpoints
"""
import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8743"

def get_token():
    """Authenticate and get token"""
    response = requests.post(f"{API_BASE}/token", data={
        "username": "admin",
        "password": "admin123"
    })
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Authentication failed: {response.status_code}")
        print(response.text)
        return None

def test_config_update(token):
    """Test updating configuration with tax rates"""
    headers = {"Authorization": f"Bearer {token}"}
    
    config_data = {
        "member1": "Diana",
        "member2": "Thomas",
        "rev1": 36000,  # Diana's annual gross
        "rev2": 48000,  # Thomas's annual gross
        "tax_rate1": 15,  # Diana's tax rate
        "tax_rate2": 20,  # Thomas's tax rate
        "split_mode": "revenus",  # Proportional to income
        "split1": 0.5,
        "split2": 0.5,
        "other_split_mode": "clé",
        "var_percent": 30,
        "max_var": 0,
        "min_fixed": 0
    }
    
    print("\n=== Testing Config Update ===")
    response = requests.put(f"{API_BASE}/config", json=config_data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Config updated successfully")
        data = response.json()
        print(f"Member 1: {data['member1']} - Gross: {data['rev1']}€, Tax: {data['tax_rate1']}%")
        print(f"Member 2: {data['member2']} - Gross: {data['rev2']}€, Tax: {data['tax_rate2']}%")
        return True
    else:
        print(f"❌ Config update failed: {response.status_code}")
        print(response.text)
        return False

def test_couple_balance(token):
    """Test couple balance endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== Testing Couple Balance ===")
    month = datetime.now().strftime("%Y-%m")
    response = requests.get(f"{API_BASE}/balance/couple?month={month}", headers=headers)
    
    if response.status_code == 200:
        print("✅ Couple balance retrieved successfully")
        data = response.json()
        
        print(f"\n📅 Month: {data['month']} ({data['month_progression']})")
        print(f"💰 Total net income: {data['total_net_income']:.2f}€")
        print(f"🏠 Total fixed charges: {data['total_fixed_charges']:.2f}€")
        print(f"💎 Total provisions: {data['total_custom_provisions']:.2f}€")
        print(f"📊 Total required: {data['total_provisions_required']:.2f}€")
        print(f"🔄 Distribution mode: {data['distribution_mode']}")
        
        print(f"\n👤 {data['member1']['member_name']}:")
        print(f"  - Net income: {data['member1']['net_income']:.2f}€")
        print(f"  - To provision: {data['member1']['total_provision_required']:.2f}€")
        print(f"  - Done: {data['member1']['provision_done']:.2f}€")
        print(f"  - Remaining: {data['member1']['provision_remaining']:.2f}€")
        
        print(f"\n👤 {data['member2']['member_name']}:")
        print(f"  - Net income: {data['member2']['net_income']:.2f}€")
        print(f"  - To provision: {data['member2']['total_provision_required']:.2f}€")
        print(f"  - Done: {data['member2']['provision_done']:.2f}€")
        print(f"  - Remaining: {data['member2']['provision_remaining']:.2f}€")
        
        if data['balance_status'] == 'balanced':
            print("\n✅ Balance is equilibrated")
        elif data['balance_status'] == 'member1_owes':
            print(f"\n⚠️ {data['member1']['member_name']} owes {data['balance_amount']:.2f}€")
        else:
            print(f"\n⚠️ {data['member2']['member_name']} owes {data['balance_amount']:.2f}€")
        
        return True
    else:
        print(f"❌ Failed to get couple balance: {response.status_code}")
        print(response.text)
        return False

def test_provisions_calculation(token):
    """Test provisions calculation endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== Testing Provisions Calculation ===")
    
    calc_data = {
        "month": datetime.now().strftime("%Y-%m"),
        "include_provisions": True,
        "include_fixed": True
    }
    
    response = requests.post(f"{API_BASE}/balance/provisions/calculate", json=calc_data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Provisions calculated successfully")
        data = response.json()
        
        print(f"\n📊 Calculation for: {data['month']}")
        print(f"🏠 Fixed charges: {data['fixed_charges_total']:.2f}€")
        print(f"💎 Custom provisions: {data['custom_provisions_total']:.2f}€")
        print(f"💰 Total required: {data['total_required']:.2f}€")
        print(f"🔄 Distribution: {data['distribution_mode']}")
        
        print(f"\n{data['member1']['name']}:")
        print(f"  - Required: {data['member1']['provision_required']:.2f}€")
        print(f"  - % of income: {data['member1']['percentage_of_income']:.2f}%")
        
        print(f"\n{data['member2']['name']}:")
        print(f"  - Required: {data['member2']['provision_required']:.2f}€")
        print(f"  - % of income: {data['member2']['percentage_of_income']:.2f}%")
        
        return True
    else:
        print(f"❌ Failed to calculate provisions: {response.status_code}")
        print(response.text)
        return False

def test_provisions_status(token):
    """Test provisions status endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== Testing Provisions Status ===")
    
    response = requests.get(f"{API_BASE}/balance/provisions/status", headers=headers)
    
    if response.status_code == 200:
        print("✅ Provisions status retrieved successfully")
        data = response.json()
        
        print(f"\n📅 Month: {data['month']}")
        print(f"✅ Total completion: {data['total_completion']:.1f}%")
        print(f"🎯 All done: {data['all_provisions_done']}")
        
        for member, status in data['status'].items():
            print(f"\n{member}:")
            print(f"  - Required: {status['required']:.2f}€")
            print(f"  - Done: {status['done']:.2f}€")
            print(f"  - Remaining: {status['remaining']:.2f}€")
            print(f"  - Completion: {status['completion_percentage']:.1f}%")
        
        return True
    else:
        print(f"❌ Failed to get provisions status: {response.status_code}")
        print(response.text)
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("TESTING PROVISIONS AND COUPLE BALANCE API")
    print("=" * 60)
    
    # Get authentication token
    token = get_token()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    print("✅ Authenticated successfully")
    
    # Run tests
    tests_passed = 0
    tests_total = 4
    
    if test_config_update(token):
        tests_passed += 1
    
    if test_couple_balance(token):
        tests_passed += 1
    
    if test_provisions_calculation(token):
        tests_passed += 1
    
    if test_provisions_status(token):
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("✅ All tests passed successfully!")
        print("\n🎉 The provisions and couple balance system is fully operational!")
        print(f"📱 You can now access the enhanced frontend at:")
        print(f"   http://localhost:45679/index-enhanced.html")
    else:
        print(f"⚠️ {tests_total - tests_passed} test(s) failed")
        print("Please check the error messages above")

if __name__ == "__main__":
    main()