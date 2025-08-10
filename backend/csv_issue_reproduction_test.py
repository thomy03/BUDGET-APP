#!/usr/bin/env python3
"""
CSV Issue Reproduction Test
Specifically targeting "Signature binaire invalide" error reported by users

This test creates edge cases and problematic CSV formats that might trigger
the validation failure mentioned in the issue.
"""

import os
import sys
import io
import tempfile
from fastapi import UploadFile
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.append('/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend')

from app import validate_file_security, app
import magic_fallback


def create_upload_file_mock(content: bytes, filename: str, content_type='text/csv'):
    """Create a mock UploadFile object"""
    file_obj = io.BytesIO(content)
    upload_file = UploadFile(
        filename=filename,
        file=file_obj,
        headers={'content-type': content_type}
    )
    return upload_file


def test_problematic_csv_formats():
    """Test CSV formats that might trigger the 'Signature binaire invalide' error"""
    
    print("🚨 REPRODUCING 'Signature binaire invalide' ERROR")
    print("=" * 70)
    
    # These are CSV formats that might cause issues
    test_cases = [
        {
            'name': 'CSV with lowercase headers only',
            'content': b'date,description,amount,account\n2024-01-01,Test,-50.00,Checking\n',
            'expected_issue': 'Lowercase headers not in signature list'
        },
        {
            'name': 'CSV starting with non-standard header',
            'content': b'Transaction Date,Description,Amount\n2024-01-01,Test,100\n',
            'expected_issue': 'Header not in predefined signature list'
        },
        {
            'name': 'CSV with BOM but weird content type',
            'content': b'\xef\xbb\xbfdate,amount\n2024-01-01,100\n',
            'content_type': 'application/octet-stream',
            'expected_issue': 'Conflicting content type'
        },
        {
            'name': 'CSV with tab separation only',
            'content': b'Date\tAmount\tDescription\n2024-01-01\t100\tTest\n',
            'expected_issue': 'Tab separator not detected as CSV'
        },
        {
            'name': 'CSV with special characters in headers',
            'content': 'Période,Montant,Compté\n2024-01-01,-50.00,Compte\n'.encode('utf-8'),
            'expected_issue': 'Accented characters in headers'
        },
        {
            'name': 'CSV with Windows line endings',
            'content': b'Date,Amount\r\n2024-01-01,100\r\n',
            'expected_issue': 'Windows CRLF line endings'
        },
        {
            'name': 'CSV with quoted headers',
            'content': b'"Date","Description","Amount"\n2024-01-01,"Test",100\n',
            'expected_issue': 'Quoted CSV headers'
        },
        {
            'name': 'Empty CSV file',
            'content': b'',
            'expected_issue': 'Zero-length file'
        },
        {
            'name': 'CSV with only whitespace',
            'content': b'   \n\n  \n',
            'expected_issue': 'Whitespace-only content'
        },
        {
            'name': 'Bank export format (French)',
            'content': 'Date opération;Date valeur;Libellé;Montant;Solde\n01/01/2024;01/01/2024;Virement;-100,50;1500,00\n'.encode('latin-1'),
            'expected_issue': 'French bank format with Latin-1 encoding'
        },
        {
            'name': 'CSV with very long first line',
            'content': b'Date,' + b'VeryLongColumnName' * 20 + b',Amount\n2024-01-01,Test,100\n',
            'expected_issue': 'Long headers might exceed signature check buffer'
        }
    ]
    
    failures = []
    successes = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print("-" * 50)
        
        try:
            # Create upload file
            content_type = test_case.get('content_type', 'text/csv')
            upload_file = create_upload_file_mock(
                test_case['content'], 
                f"test_{i}.csv",
                content_type
            )
            
            # Show content preview
            preview = test_case['content'][:50]
            try:
                preview_text = preview.decode('utf-8', errors='ignore')
            except:
                preview_text = preview.hex()
            
            print(f"Content preview: {repr(preview_text)}")
            print(f"Content size: {len(test_case['content'])} bytes")
            print(f"Expected issue: {test_case['expected_issue']}")
            
            # Test MIME detection
            mime_type = magic_fallback.from_buffer(test_case['content'])
            print(f"Detected MIME: {mime_type}")
            
            # Test validation
            is_valid = validate_file_security(upload_file)
            print(f"Validation result: {'✅ ACCEPTED' if is_valid else '❌ REJECTED'}")
            
            if is_valid:
                successes.append(test_case['name'])
            else:
                failures.append({
                    'name': test_case['name'],
                    'expected_issue': test_case['expected_issue'],
                    'content_preview': preview_text,
                    'mime_type': mime_type
                })
                print(f"🚨 REPRODUCED ISSUE: {test_case['name']}")
            
        except Exception as e:
            print(f"💥 ERROR: {e}")
            failures.append({
                'name': test_case['name'],
                'expected_issue': test_case['expected_issue'],
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 ISSUE REPRODUCTION SUMMARY")
    print("=" * 70)
    print(f"Total tests: {len(test_cases)}")
    print(f"Successful validations: {len(successes)}")
    print(f"Failed validations (issues reproduced): {len(failures)}")
    
    if failures:
        print(f"\n🚨 REPRODUCED ISSUES ({len(failures)}):")
        for failure in failures:
            print(f"  ❌ {failure['name']}")
            print(f"     Expected: {failure['expected_issue']}")
            if 'error' in failure:
                print(f"     Error: {failure['error']}")
    
    if successes:
        print(f"\n✅ SUCCESSFUL VALIDATIONS ({len(successes)}):")
        for success in successes:
            print(f"  ✅ {success}")
    
    return failures


def test_api_endpoint_integration():
    """Test the actual API endpoint to see if it reproduces the issue"""
    print(f"\n🌐 TESTING API ENDPOINT INTEGRATION")
    print("=" * 70)
    
    client = TestClient(app)
    
    # Test problematic CSV content through API
    problematic_csv = b'date,amount\n2024-01-01,100\n'  # lowercase 'date'
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_file.write(problematic_csv)
            temp_file.flush()
            
            # Test API call
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/import",
                    files={"file": ("test.csv", f, "text/csv")},
                    headers={"Authorization": "Bearer fake_token"}  # This will fail auth, but should get to validation
                )
            
            print(f"API Response Status: {response.status_code}")
            print(f"API Response: {response.text[:200]}")
            
            if response.status_code == 401:
                print("ℹ️  Got authentication error - this is expected")
                print("   The file validation happens before auth, so if we get 401, validation passed")
            elif "Signature binaire invalide" in response.text or "non sécurisé" in response.text:
                print("🚨 REPRODUCED: Signature validation error in API!")
                return True
            
    except Exception as e:
        print(f"💥 API Test Error: {e}")
    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass
    
    return False


def create_sample_csv_for_testing():
    """Create a CSV sample that should trigger the issue based on typical user scenarios"""
    print(f"\n📄 CREATING PROBLEMATIC CSV SAMPLE")
    print("=" * 70)
    
    # This mimics a real bank export that might cause issues
    problematic_content = """date,description,amount,balance
2024-01-15,"Payment to AMAZON",-45.99,1234.56
2024-01-16,"Salary deposit",2500.00,3734.56
2024-01-17,"ATM withdrawal",-100.00,3634.56
""".encode('utf-8')
    
    sample_file = '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/problematic_sample.csv'
    
    with open(sample_file, 'wb') as f:
        f.write(problematic_content)
    
    print(f"Created sample file: {sample_file}")
    print(f"Content preview: {problematic_content[:100].decode('utf-8')}")
    
    # Test this sample
    print(f"\nTesting sample file...")
    upload_file = create_upload_file_mock(problematic_content, 'problematic_sample.csv')
    is_valid = validate_file_security(upload_file)
    
    print(f"Sample validation: {'✅ ACCEPTED' if is_valid else '❌ REJECTED'}")
    
    if not is_valid:
        print("🎯 SUCCESS: Reproduced the signature validation issue!")
        return sample_file
    else:
        print("ℹ️  Sample was accepted - issue may be more specific")
        return None


def main():
    """Main test function"""
    print("🔬 CSV VALIDATION ISSUE REPRODUCTION")
    print("=" * 70)
    print("Attempting to reproduce 'Signature binaire invalide' error")
    
    # Test 1: Try various problematic formats
    failures = test_problematic_csv_formats()
    
    # Test 2: Test API integration
    api_reproduced = test_api_endpoint_integration()
    
    # Test 3: Create and test a problematic sample
    sample_file = create_sample_csv_for_testing()
    
    # Final summary
    print(f"\n🎯 REPRODUCTION RESULTS")
    print("=" * 70)
    
    if failures:
        print(f"✅ Successfully reproduced {len(failures)} validation failures:")
        for failure in failures:
            print(f"  - {failure['name']}")
        
        print(f"\n💡 MOST LIKELY ROOT CAUSE:")
        print("  CSV files with lowercase 'date' headers or non-standard headers")
        print("  are being rejected by the binary signature validation.")
        
        print(f"\n🔧 RECOMMENDED FIX:")
        print("  Update the csv_signatures list in validate_file_security() to include:")
        print("  - b'date' (lowercase)")
        print("  - More flexible header detection")
        print("  - Fallback validation for CSV-like content")
        
    elif api_reproduced:
        print("✅ Reproduced issue through API endpoint")
    elif sample_file and not os.path.exists(sample_file):
        print("✅ Created problematic sample that fails validation")
    else:
        print("ℹ️  Could not reproduce the specific issue")
        print("    All tested CSV formats passed validation")
        print("    The issue might be environmental or version-specific")
    
    print(f"\n📋 NEXT STEPS:")
    print("1. Review the failed test cases above")
    print("2. Implement the recommended signature validation improvements")
    print("3. Add comprehensive CSV format support")
    print("4. Test with real user CSV files")


if __name__ == "__main__":
    main()