#!/usr/bin/env python3
"""
CSV Validation Diagnostic Tool
Analyze the specific "Signature binaire invalide" issue in Budget Famille v2.3

This tool diagnoses exactly why CSV files are being rejected and provides
specific recommendations for fixing the validation logic.
"""

import os
import sys
import io
from fastapi import UploadFile

# Add backend directory to path
sys.path.append('/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend')

from app import validate_file_security
import magic_fallback


def create_upload_file_mock(content: bytes, filename: str):
    """Create a mock UploadFile object for testing"""
    file_obj = io.BytesIO(content)
    upload_file = UploadFile(
        filename=filename,
        file=file_obj,
        headers={'content-type': 'text/csv'}
    )
    return upload_file


def analyze_csv_file(file_path: str):
    """Analyze a CSV file through the validation process step by step"""
    print(f"\n🔍 ANALYZING: {os.path.basename(file_path)}")
    print("=" * 60)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Read file content
    with open(file_path, 'rb') as f:
        content = f.read()
    
    print(f"📁 File size: {len(content)} bytes")
    print(f"🔤 First 32 bytes (hex): {content[:32].hex()}")
    print(f"📄 First 100 chars: {repr(content[:100].decode('utf-8', errors='ignore'))}")
    
    # Test MIME detection
    mime_type = magic_fallback.from_buffer(content)
    print(f"🧩 Detected MIME type: {mime_type}")
    
    # Create upload file mock
    upload_file = create_upload_file_mock(content, os.path.basename(file_path))
    
    # Test each validation step
    print("\n🛡️  SECURITY VALIDATION STEPS:")
    
    # Step 1: Filename validation
    filename_valid = upload_file.filename and len(upload_file.filename) <= 255
    print(f"   1. Filename length: {'✅' if filename_valid else '❌'} ({len(upload_file.filename) if upload_file.filename else 0} chars)")
    
    # Step 2: Extension validation
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = os.path.splitext(upload_file.filename.lower())[1]
    ext_valid = file_ext in allowed_extensions
    print(f"   2. Extension check: {'✅' if ext_valid else '❌'} ('{file_ext}' in {allowed_extensions})")
    
    # Step 3: File size validation
    file_size = len(content)
    max_size = 10 * 1024 * 1024  # 10MB
    size_valid = file_size <= max_size
    print(f"   3. Size validation: {'✅' if size_valid else '❌'} ({file_size} <= {max_size})")
    
    # Step 4: MIME type validation (if MAGIC_AVAILABLE)
    allowed_mimes = {
        'text/csv', 'text/plain',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip'
    }
    mime_valid = mime_type in allowed_mimes
    print(f"   4. MIME type check: {'✅' if mime_valid else '❌'} ('{mime_type}' in {allowed_mimes})")
    
    # Step 5: Binary signature validation - THIS IS THE KEY STEP
    first_bytes = content[:16]
    print(f"   5. Binary signature analysis:")
    print(f"      First 16 bytes: {first_bytes.hex()}")
    
    # Current signatures being checked
    csv_signatures = [b'\xef\xbb\xbf', b'dateOp', b'Date']
    xlsx_signature = b'PK\x03\x04'
    xls_signature = b'\xd0\xcf\x11\xe0'
    
    signature_matches = []
    
    # Check each signature
    for sig in csv_signatures:
        if first_bytes.startswith(sig):
            signature_matches.append(f"CSV signature: {sig}")
    
    if first_bytes.startswith(xlsx_signature):
        signature_matches.append("XLSX signature")
    
    if first_bytes.startswith(xls_signature):
        signature_matches.append("XLS signature")
    
    # Check UTF-8 decoding fallback
    try:
        decoded = first_bytes.decode('utf-8', errors='ignore').strip()
        if decoded.startswith(('dateOp', 'Date')):
            signature_matches.append(f"UTF-8 header: '{decoded[:20]}'")
    except:
        pass
    
    signature_valid = len(signature_matches) > 0
    print(f"      Signature matches: {'✅' if signature_valid else '❌'} {signature_matches}")
    
    # Overall validation result
    print(f"\n🎯 VALIDATION STEPS SUMMARY:")
    all_checks = [filename_valid, ext_valid, size_valid, mime_valid, signature_valid]
    passed_checks = sum(all_checks)
    
    for i, (check, name) in enumerate(zip(all_checks, ['Filename', 'Extension', 'Size', 'MIME', 'Signature']), 1):
        print(f"   {i}. {name}: {'✅ PASS' if check else '❌ FAIL'}")
    
    print(f"\n📊 RESULT: {passed_checks}/5 checks passed")
    
    # Test actual validation function
    try:
        upload_file = create_upload_file_mock(content, os.path.basename(file_path))
        actual_result = validate_file_security(upload_file)
        print(f"🔐 ACTUAL VALIDATION: {'✅ ACCEPTED' if actual_result else '❌ REJECTED'}")
    except Exception as e:
        print(f"💥 VALIDATION ERROR: {e}")
    
    return {
        'filename': os.path.basename(file_path),
        'file_size': file_size,
        'mime_type': mime_type,
        'checks': {
            'filename': filename_valid,
            'extension': ext_valid,
            'size': size_valid,
            'mime': mime_valid,
            'signature': signature_valid
        },
        'signature_matches': signature_matches,
        'first_bytes_hex': first_bytes.hex(),
        'validation_result': actual_result if 'actual_result' in locals() else False
    }


def recommend_fixes(analysis_results):
    """Generate specific fix recommendations based on analysis"""
    print(f"\n💡 RECOMMENDATIONS TO FIX CSV VALIDATION")
    print("=" * 60)
    
    # Identify common failure patterns
    signature_failures = [r for r in analysis_results if not r['checks']['signature']]
    
    if signature_failures:
        print(f"🚨 ISSUE IDENTIFIED: {len(signature_failures)} files failing signature validation")
        print("\n📝 RECOMMENDED FIX FOR validate_file_security() function:")
        print("""
# Current problematic code in app.py around line 442:
csv_signatures = [b'\\xef\\xbb\\xbf', b'dateOp', b'Date']  # Too restrictive

# RECOMMENDED REPLACEMENT:
csv_signatures = [
    b'\\xef\\xbb\\xbf',  # UTF-8 BOM
    b'dateOp', b'Date', b'date',  # Common headers (case variations)
    b'Date,', b'date,',  # Headers with comma separator  
    b'Date;', b'date;',  # Headers with semicolon separator
]

# Enhanced signature validation with fallback:
is_valid_signature = (
    any(first_bytes.startswith(sig) for sig in csv_signatures) or
    first_bytes.startswith(xlsx_signature) or
    first_bytes.startswith(xls_signature) or
    first_bytes.decode('utf-8', errors='ignore').strip().startswith(('dateOp', 'Date', 'date'))
)

# Add additional fallback for plain CSV without specific headers:
if not is_valid_signature and file_ext == '.csv':
    try:
        # Check if it looks like CSV content
        sample_text = first_bytes.decode('utf-8', errors='ignore').lower()
        csv_indicators = [
            ',' in sample_text,  # Has comma separators
            ';' in sample_text,  # Has semicolon separators
            '\\t' in sample_text,  # Has tab separators
            any(word in sample_text for word in ['amount', 'montant', 'transaction'])
        ]
        if any(csv_indicators):
            is_valid_signature = True
            logger.info(f"CSV content detected via fallback analysis for {file.filename}")
    except:
        pass
""")
    
    print(f"\n🔧 SPECIFIC CODE CHANGES NEEDED:")
    print("1. File: app.py, Function: validate_file_security(), Line: ~442")
    print("2. Expand csv_signatures list to include more patterns")
    print("3. Add fallback validation for plain CSV content")
    print("4. Add debug logging to understand rejection reasons")
    
    print(f"\n⚡ IMMEDIATE HOTFIX:")
    print("""
# Quick fix - add this after the current signature check:
if not is_valid_signature and file_ext == '.csv':
    # Fallback: accept any file that starts with common text patterns
    try:
        text_start = first_bytes.decode('utf-8', errors='ignore').lower()
        if any(pattern in text_start for pattern in ['date', ',', ';']):
            is_valid_signature = True
            logger.info(f"CSV accepted via fallback for {file.filename}")
    except:
        pass
""")


def main():
    """Main diagnostic function"""
    print("🔍 CSV VALIDATION DIAGNOSTIC TOOL")
    print("=" * 60)
    print("Analyzing CSV file validation issues in Budget Famille v2.3")
    
    # Test files to analyze
    test_files = [
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test-import.csv',
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test_simple.csv',
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test_windows_import.csv',
        '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test-navigation-simple.csv'
    ]
    
    # Create test CSV with various formats for comparison
    test_cases = [
        ("UTF-8 with BOM", b'\xef\xbb\xbfDate,Amount\n2024-01-01,100\n'),
        ("Plain CSV", b'Date,Amount\n2024-01-01,100\n'),
        ("dateOp header", b'dateOp,label,amount\n2024-01-01,Test,100\n'),
        ("Lowercase date", b'date,amount\n2024-01-01,100\n'),
        ("Semicolon CSV", b'Date;Amount\n2024-01-01;100\n'),
    ]
    
    results = []
    
    # Analyze existing files
    for file_path in test_files:
        if os.path.exists(file_path):
            result = analyze_csv_file(file_path)
            results.append(result)
    
    # Analyze test cases
    print(f"\n🧪 TESTING VARIOUS CSV FORMATS:")
    print("=" * 60)
    
    for name, content in test_cases:
        print(f"\n🔍 Testing: {name}")
        temp_file = f"/tmp/test_{name.lower().replace(' ', '_')}.csv"
        try:
            with open(temp_file, 'wb') as f:
                f.write(content)
            result = analyze_csv_file(temp_file)
            result['test_case'] = name
            results.append(result)
            os.remove(temp_file)
        except Exception as e:
            print(f"Error testing {name}: {e}")
    
    # Generate recommendations
    recommend_fixes(results)
    
    # Summary
    total_files = len(results)
    accepted_files = len([r for r in results if r.get('validation_result', False)])
    
    print(f"\n📊 DIAGNOSTIC SUMMARY:")
    print("=" * 60)
    print(f"Total files analyzed: {total_files}")
    print(f"Files accepted: {accepted_files}")
    print(f"Files rejected: {total_files - accepted_files}")
    print(f"Success rate: {(accepted_files/total_files)*100:.1f}%" if total_files > 0 else "N/A")
    
    if accepted_files < total_files:
        print(f"\n🎯 ROOT CAUSE: Binary signature validation is too restrictive")
        print(f"📋 ACTION REQUIRED: Update validate_file_security() function with recommended changes")
    else:
        print(f"\n✅ All files passed validation - no issues detected")


if __name__ == "__main__":
    main()