#!/usr/bin/env python3
"""
CSV File Validation Tool
Budget Famille v2.3

This tool allows you to test any CSV file against the application's validation logic
to diagnose why a file might be rejected with "Signature binaire invalide" error.

Usage:
    python3 validate_csv_file.py <path_to_csv_file>
    
Example:
    python3 validate_csv_file.py my_bank_export.csv
"""

import os
import sys
import io
from fastapi import UploadFile

# Add backend directory to path
sys.path.append('/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend')

try:
    from app import validate_file_security, robust_read_csv
    import magic_fallback
except ImportError as e:
    print(f"Error importing validation modules: {e}")
    sys.exit(1)


def create_upload_file_mock(file_path: str):
    """Create a mock UploadFile object from a real file"""
    with open(file_path, 'rb') as f:
        content = f.read()
    
    file_obj = io.BytesIO(content)
    upload_file = UploadFile(
        filename=os.path.basename(file_path),
        file=file_obj,
        headers={'content-type': 'text/csv'}
    )
    return upload_file, content


def analyze_csv_file(file_path: str):
    """Perform comprehensive analysis of a CSV file"""
    
    print(f"🔍 ANALYZING CSV FILE: {file_path}")
    print("=" * 80)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return False
    
    # Read file content
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Basic file information
    print(f"📁 File Information:")
    print(f"   File size: {len(content)} bytes")
    print(f"   File extension: {os.path.splitext(file_path)[1]}")
    
    # Content preview
    print(f"\n📄 Content Preview:")
    try:
        preview_text = content[:200].decode('utf-8', errors='ignore')
        print(f"   First 200 chars: {repr(preview_text)}")
    except:
        print(f"   Binary content: {content[:50].hex()}")
    
    print(f"   First 32 bytes (hex): {content[:32].hex()}")
    
    # MIME type detection
    print(f"\n🧩 MIME Type Detection:")
    try:
        mime_type = magic_fallback.from_buffer(content)
        print(f"   Detected MIME type: {mime_type}")
    except Exception as e:
        print(f"   MIME detection error: {e}")
        mime_type = "unknown"
    
    # Create upload file mock and test validation
    print(f"\n🛡️  Security Validation Test:")
    try:
        upload_file, _ = create_upload_file_mock(file_path)
        is_valid = validate_file_security(upload_file)
        
        if is_valid:
            print(f"   ✅ VALIDATION PASSED - File is accepted")
        else:
            print(f"   ❌ VALIDATION FAILED - File would be rejected")
            print(f"   🚨 This file would trigger 'Signature binaire invalide' error")
    except Exception as e:
        print(f"   💥 Validation error: {e}")
        return False
    
    # If validation passed, test CSV parsing
    if is_valid:
        print(f"\n📊 CSV Parsing Test:")
        try:
            upload_file, _ = create_upload_file_mock(file_path)
            df = robust_read_csv(upload_file)
            print(f"   ✅ PARSING PASSED")
            print(f"   Rows parsed: {len(df)}")
            print(f"   Columns: {list(df.columns)}")
            if len(df) > 0:
                print(f"   Sample row: {df.iloc[0].to_dict()}")
        except Exception as e:
            print(f"   ❌ PARSING FAILED: {e}")
    
    # Detailed validation breakdown
    print(f"\n🔬 Detailed Validation Analysis:")
    
    # Step 1: Filename
    filename = os.path.basename(file_path)
    filename_ok = filename and len(filename) <= 255
    print(f"   1. Filename check: {'✅' if filename_ok else '❌'} ('{filename}', {len(filename)} chars)")
    
    # Step 2: Extension
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = os.path.splitext(filename.lower())[1]
    ext_ok = file_ext in allowed_extensions
    print(f"   2. Extension check: {'✅' if ext_ok else '❌'} ('{file_ext}' in {allowed_extensions})")
    
    # Step 3: File size
    max_size = 10 * 1024 * 1024  # 10MB
    size_ok = len(content) <= max_size
    print(f"   3. Size check: {'✅' if size_ok else '❌'} ({len(content)} <= {max_size} bytes)")
    
    # Step 4: MIME type
    allowed_mimes = {
        'text/csv', 'text/plain',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip'
    }
    mime_ok = mime_type in allowed_mimes
    print(f"   4. MIME type check: {'✅' if mime_ok else '❌'} ('{mime_type}' in allowed set)")
    
    # Step 5: Binary signature
    first_bytes = content[:16] if content else b''
    print(f"   5. Binary signature analysis:")
    print(f"      First 16 bytes: {first_bytes.hex()}")
    
    # Check current signatures
    csv_signatures = [b'\xef\xbb\xbf', b'dateOp', b'Date']
    xlsx_signature = b'PK\x03\x04'
    xls_signature = b'\xd0\xcf\x11\xe0'
    
    signature_matches = []
    for sig in csv_signatures:
        if first_bytes.startswith(sig):
            signature_matches.append(f"CSV: {sig}")
    
    if first_bytes.startswith(xlsx_signature):
        signature_matches.append("XLSX")
    
    if first_bytes.startswith(xls_signature):
        signature_matches.append("XLS")
    
    # UTF-8 fallback check
    try:
        decoded = first_bytes.decode('utf-8', errors='ignore').strip()
        if decoded.startswith(('dateOp', 'Date')):
            signature_matches.append(f"UTF-8 header: {decoded[:20]}")
    except:
        pass
    
    signature_ok = len(signature_matches) > 0
    print(f"      Signature matches: {'✅' if signature_ok else '❌'} {signature_matches}")
    
    # Overall assessment
    all_checks_passed = all([filename_ok, ext_ok, size_ok, mime_ok, signature_ok])
    
    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"   Overall result: {'✅ SHOULD PASS' if all_checks_passed else '❌ WILL BE REJECTED'}")
    
    if not all_checks_passed:
        print(f"\n💡 ISSUES IDENTIFIED:")
        if not filename_ok:
            print(f"   - Invalid filename (too long or missing)")
        if not ext_ok:
            print(f"   - Invalid file extension (got '{file_ext}', expected one of {allowed_extensions})")
        if not size_ok:
            print(f"   - File too large ({len(content)} bytes > {max_size} bytes)")
        if not mime_ok:
            print(f"   - Invalid MIME type (got '{mime_type}', expected one of {allowed_mimes})")
        if not signature_ok:
            print(f"   - Invalid binary signature (first bytes don't match expected patterns)")
            print(f"   - To fix: ensure CSV starts with 'Date', 'dateOp', or UTF-8 BOM")
    
    return is_valid


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python3 validate_csv_file.py <path_to_csv_file>")
        print("\nExample:")
        print("  python3 validate_csv_file.py my_export.csv")
        print("  python3 validate_csv_file.py /path/to/bank_transactions.csv")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print("🔍 CSV FILE VALIDATION TOOL")
    print("Budget Famille v2.3 - Diagnostic Mode")
    print("=" * 80)
    
    result = analyze_csv_file(file_path)
    
    print(f"\n🎯 FINAL RESULT:")
    if result:
        print("✅ This CSV file should be accepted by Budget Famille")
        print("   If you're still getting rejection errors, please report this as a bug")
        print("   with your environment details.")
    else:
        print("❌ This CSV file will be rejected by Budget Famille")
        print("   Review the issues identified above to fix the file format.")
        print("\n💡 QUICK FIXES:")
        print("   - Ensure the file starts with 'Date' or 'dateOp' in the first column header")
        print("   - Use UTF-8 encoding")
        print("   - Keep file size under 10MB")
        print("   - Use .csv extension")
    
    print(f"\n📋 SUPPORT:")
    print("   If you need help fixing your CSV file, check the full QA report:")
    print("   CSV_VALIDATION_QA_REPORT.md")


if __name__ == "__main__":
    main()