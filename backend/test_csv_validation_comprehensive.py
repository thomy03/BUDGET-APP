"""
Comprehensive test suite for CSV file validation in Budget Famille v2.3
Testing MIME types, binary signatures, and various CSV encodings

Current issue: CSV files being rejected by security validation with "Signature binaire invalide"
This test suite validates file security logic and provides detailed analysis.
"""

import os
import io
import tempfile
import pytest
from unittest.mock import Mock, patch
from fastapi import UploadFile, HTTPException
from fastapi.testclient import TestClient
import pandas as pd
import csv
from typing import List, Dict, Any
import json
import sys

# Import the modules we're testing
sys.path.append('/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend')

try:
    from app import validate_file_security, robust_read_csv, app
    from magic_fallback import from_buffer, from_file
    import magic_fallback
except ImportError as e:
    print(f"Import error: {e}")
    raise


class TestCSVValidation:
    """Comprehensive CSV validation test suite"""
    
    def __init__(self):
        """Initialize test suite"""
        self.test_results = []
        self.client = TestClient(app)
    
    def setup_method(self):
        """Setup for each test"""
        if not hasattr(self, 'test_results'):
            self.test_results = []
        if not hasattr(self, 'client'):
            self.client = TestClient(app)
    
    # Test Data Generators
    def create_csv_content(self, encoding='utf-8', add_bom=False, separator=',', headers=None, data_rows=None):
        """Create CSV content with specified encoding and format"""
        if headers is None:
            headers = ['Date', 'Description', 'Montant', 'Compte']
        if data_rows is None:
            data_rows = [
                ['2024-01-01', 'Test transaction 1', '12.34', 'CHECKING'],
                ['2024-01-02', 'Test transaction 2', '-5.00', 'CHECKING']
            ]
        
        # Build CSV content
        csv_lines = [separator.join(headers)]
        csv_lines.extend([separator.join(row) for row in data_rows])
        csv_text = '\n'.join(csv_lines)
        
        # Encode with specified encoding
        content = csv_text.encode(encoding)
        
        # Add BOM if requested
        if add_bom and encoding.lower() == 'utf-8':
            content = b'\xef\xbb\xbf' + content
        
        return content
    
    def create_upload_file(self, content: bytes, filename: str, content_type: str = 'text/csv'):
        """Create a mock UploadFile object"""
        file_obj = io.BytesIO(content)
        upload_file = UploadFile(
            filename=filename,
            file=file_obj,
            headers={'content-type': content_type}
        )
        return upload_file
    
    # Test Cases
    def test_csv_formats_basic(self):
        """Test basic CSV formats that should be accepted"""
        test_cases = [
            {
                'name': 'UTF-8 without BOM',
                'encoding': 'utf-8',
                'add_bom': False,
                'filename': 'test_utf8.csv',
                'expected_valid': True
            },
            {
                'name': 'UTF-8 with BOM',
                'encoding': 'utf-8',
                'add_bom': True,
                'filename': 'test_utf8_bom.csv',
                'expected_valid': True
            },
            {
                'name': 'ISO-8859-1 (Latin-1)',
                'encoding': 'iso-8859-1',
                'add_bom': False,
                'filename': 'test_latin1.csv',
                'expected_valid': True
            },
            {
                'name': 'Windows-1252',
                'encoding': 'windows-1252',
                'add_bom': False,
                'filename': 'test_win1252.csv',
                'expected_valid': True
            }
        ]
        
        results = []
        for case in test_cases:
            try:
                content = self.create_csv_content(
                    encoding=case['encoding'],
                    add_bom=case['add_bom']
                )
                upload_file = self.create_upload_file(content, case['filename'])
                
                # Test validation
                is_valid = validate_file_security(upload_file)
                
                result = {
                    'test_name': case['name'],
                    'filename': case['filename'],
                    'encoding': case['encoding'],
                    'has_bom': case['add_bom'],
                    'content_size': len(content),
                    'content_preview': content[:50].hex(),
                    'validation_result': is_valid,
                    'expected': case['expected_valid'],
                    'status': 'PASS' if is_valid == case['expected_valid'] else 'FAIL'
                }
                results.append(result)
                
            except Exception as e:
                results.append({
                    'test_name': case['name'],
                    'filename': case['filename'],
                    'validation_result': False,
                    'error': str(e),
                    'status': 'ERROR'
                })
        
        self.test_results.extend(results)
        return results
    
    def test_mime_type_detection(self):
        """Test MIME type detection for various CSV formats"""
        test_cases = [
            {
                'name': 'CSV with BOM',
                'content': b'\xef\xbb\xbfDate,Amount\n2024-01-01,100',
                'expected_mime': 'text/csv'
            },
            {
                'name': 'Plain CSV',
                'content': b'Date,Amount\n2024-01-01,100',
                'expected_mime': 'text/csv'
            },
            {
                'name': 'CSV with dateOp header',
                'content': b'dateOp,label,amount\n2024-01-01,Test,100',
                'expected_mime': 'text/csv'
            },
            {
                'name': 'Semicolon separated',
                'content': b'Date;Amount\n2024-01-01;100',
                'expected_mime': 'text/csv'
            },
            {
                'name': 'Tab separated',
                'content': b'Date\tAmount\n2024-01-01\t100',
                'expected_mime': 'text/csv'
            }
        ]
        
        results = []
        for case in test_cases:
            try:
                # Test with magic_fallback
                detected_mime = magic_fallback.from_buffer(case['content'])
                
                result = {
                    'test_name': case['name'],
                    'content_preview': case['content'][:50].decode('utf-8', errors='ignore'),
                    'detected_mime': detected_mime,
                    'expected_mime': case['expected_mime'],
                    'status': 'PASS' if case['expected_mime'] in detected_mime else 'FAIL'
                }
                results.append(result)
                
            except Exception as e:
                results.append({
                    'test_name': case['name'],
                    'error': str(e),
                    'status': 'ERROR'
                })
        
        self.test_results.extend(results)
        return results
    
    def test_binary_signature_validation(self):
        """Test binary signature validation logic"""
        test_signatures = [
            {
                'name': 'UTF-8 BOM signature',
                'content': b'\xef\xbb\xbfDate,Amount\n2024-01-01,100',
                'should_pass': True,
                'signature_desc': 'UTF-8 BOM'
            },
            {
                'name': 'dateOp header',
                'content': b'dateOp,label,amount\n2024-01-01,Test,100',
                'should_pass': True,
                'signature_desc': 'dateOp CSV header'
            },
            {
                'name': 'Date header',
                'content': b'Date,Amount\n2024-01-01,100',
                'should_pass': True,
                'signature_desc': 'Date CSV header'
            },
            {
                'name': 'XLSX signature',
                'content': b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00',
                'should_pass': True,
                'signature_desc': 'XLSX/ZIP signature'
            },
            {
                'name': 'XLS signature',
                'content': b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
                'should_pass': True,
                'signature_desc': 'XLS OLE2 signature'
            },
            {
                'name': 'Invalid binary',
                'content': b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR',
                'should_pass': False,
                'signature_desc': 'PNG image signature (should be rejected)'
            }
        ]
        
        results = []
        for case in test_signatures:
            try:
                upload_file = self.create_upload_file(
                    case['content'], 
                    f"test_{case['name'].lower().replace(' ', '_')}.csv"
                )
                
                is_valid = validate_file_security(upload_file)
                
                result = {
                    'test_name': case['name'],
                    'signature_desc': case['signature_desc'],
                    'content_hex': case['content'][:16].hex(),
                    'validation_result': is_valid,
                    'expected': case['should_pass'],
                    'status': 'PASS' if is_valid == case['should_pass'] else 'FAIL'
                }
                results.append(result)
                
            except Exception as e:
                results.append({
                    'test_name': case['name'],
                    'error': str(e),
                    'status': 'ERROR'
                })
        
        self.test_results.extend(results)
        return results
    
    def test_existing_csv_samples(self):
        """Test validation of existing CSV sample files"""
        sample_files = [
            '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test-import.csv',
            '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test_simple.csv',
            '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test_windows_import.csv',
            '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/test-navigation-simple.csv'
        ]
        
        results = []
        for file_path in sample_files:
            try:
                if not os.path.exists(file_path):
                    results.append({
                        'filename': os.path.basename(file_path),
                        'status': 'SKIP',
                        'reason': 'File not found'
                    })
                    continue
                
                # Read file content
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Create upload file mock
                upload_file = self.create_upload_file(content, os.path.basename(file_path))
                
                # Test validation
                is_valid = validate_file_security(upload_file)
                
                # Additional analysis
                mime_type = magic_fallback.from_buffer(content)
                encoding_info = self._detect_encoding(content)
                
                result = {
                    'filename': os.path.basename(file_path),
                    'file_size': len(content),
                    'validation_result': is_valid,
                    'mime_type': mime_type,
                    'encoding_info': encoding_info,
                    'content_preview': content[:100].decode('utf-8', errors='ignore'),
                    'binary_signature': content[:16].hex(),
                    'status': 'PASS' if is_valid else 'FAIL'
                }
                results.append(result)
                
            except Exception as e:
                results.append({
                    'filename': os.path.basename(file_path) if 'file_path' in locals() else 'unknown',
                    'error': str(e),
                    'status': 'ERROR'
                })
        
        self.test_results.extend(results)
        return results
    
    def test_csv_parsing_robustness(self):
        """Test CSV parsing with various edge cases"""
        test_cases = [
            {
                'name': 'Empty file',
                'content': b'',
                'should_parse': False
            },
            {
                'name': 'Only headers',
                'content': b'Date,Description,Montant,Compte',
                'should_parse': False  # No data rows
            },
            {
                'name': 'Valid minimal CSV',
                'content': b'Date,Description,Montant,Compte\n2024-01-01,Test,100,ACC',
                'should_parse': True
            },
            {
                'name': 'CSV with quotes',
                'content': b'Date,Description,Montant,Compte\n2024-01-01,"Test, with comma",100,ACC',
                'should_parse': True
            },
            {
                'name': 'CSV with special characters',
                'content': 'Date,Description,Montant,Compte\n2024-01-01,Café français,-50.50,Compte'.encode('utf-8'),
                'should_parse': True
            }
        ]
        
        results = []
        for case in test_cases:
            try:
                if len(case['content']) == 0:
                    # Empty file handling
                    result = {
                        'test_name': case['name'],
                        'content_size': 0,
                        'parse_result': False,
                        'expected': case['should_parse'],
                        'status': 'PASS' if False == case['should_parse'] else 'FAIL'
                    }
                else:
                    upload_file = self.create_upload_file(case['content'], f"test_{case['name']}.csv")
                    
                    try:
                        df = robust_read_csv(upload_file)
                        parse_success = not df.empty
                    except HTTPException:
                        parse_success = False
                    except Exception:
                        parse_success = False
                    
                    result = {
                        'test_name': case['name'],
                        'content_size': len(case['content']),
                        'content_preview': case['content'][:100].decode('utf-8', errors='ignore'),
                        'parse_result': parse_success,
                        'expected': case['should_parse'],
                        'status': 'PASS' if parse_success == case['should_parse'] else 'FAIL'
                    }
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    'test_name': case['name'],
                    'error': str(e),
                    'status': 'ERROR'
                })
        
        self.test_results.extend(results)
        return results
    
    def _detect_encoding(self, content: bytes) -> dict:
        """Helper method to detect encoding information"""
        info = {
            'has_bom': False,
            'likely_encoding': 'utf-8',
            'is_ascii': True
        }
        
        # Check for BOM
        if content.startswith(b'\xef\xbb\xbf'):
            info['has_bom'] = True
            info['bom_type'] = 'UTF-8'
        elif content.startswith(b'\xff\xfe'):
            info['has_bom'] = True
            info['bom_type'] = 'UTF-16 LE'
        elif content.startswith(b'\xfe\xff'):
            info['has_bom'] = True
            info['bom_type'] = 'UTF-16 BE'
        
        # Check if pure ASCII
        try:
            content.decode('ascii')
            info['is_ascii'] = True
            info['likely_encoding'] = 'ascii'
        except UnicodeDecodeError:
            info['is_ascii'] = False
            
            # Try UTF-8
            try:
                content.decode('utf-8')
                info['likely_encoding'] = 'utf-8'
            except UnicodeDecodeError:
                # Try Latin-1
                try:
                    content.decode('latin-1')
                    info['likely_encoding'] = 'latin-1'
                except UnicodeDecodeError:
                    info['likely_encoding'] = 'unknown'
        
        return info
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests and return comprehensive results"""
        print("🧪 Running comprehensive CSV validation tests...")
        
        # Run all test suites
        basic_format_results = self.test_csv_formats_basic()
        mime_detection_results = self.test_mime_type_detection()
        signature_validation_results = self.test_binary_signature_validation()
        existing_files_results = self.test_existing_csv_samples()
        parsing_results = self.test_csv_parsing_robustness()
        
        # Compile comprehensive report
        report = {
            'test_summary': {
                'total_tests': len(self.test_results),
                'passed': len([r for r in self.test_results if r.get('status') == 'PASS']),
                'failed': len([r for r in self.test_results if r.get('status') == 'FAIL']),
                'errors': len([r for r in self.test_results if r.get('status') == 'ERROR']),
                'skipped': len([r for r in self.test_results if r.get('status') == 'SKIP'])
            },
            'test_categories': {
                'basic_formats': {
                    'description': 'Testing various CSV encodings and formats',
                    'results': basic_format_results
                },
                'mime_detection': {
                    'description': 'Testing MIME type detection accuracy',
                    'results': mime_detection_results
                },
                'signature_validation': {
                    'description': 'Testing binary signature validation',
                    'results': signature_validation_results
                },
                'existing_files': {
                    'description': 'Testing existing CSV sample files',
                    'results': existing_files_results
                },
                'parsing_robustness': {
                    'description': 'Testing CSV parsing with edge cases',
                    'results': parsing_results
                }
            },
            'issues_identified': self._identify_issues(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _identify_issues(self) -> List[Dict[str, Any]]:
        """Analyze test results to identify validation issues"""
        issues = []
        
        # Check for failed validations
        failed_tests = [r for r in self.test_results if r.get('status') == 'FAIL']
        
        for test in failed_tests:
            if 'validation_result' in test and not test['validation_result']:
                issues.append({
                    'type': 'validation_failure',
                    'test_name': test.get('test_name', 'Unknown'),
                    'description': f"File validation failed for {test.get('filename', 'unknown file')}",
                    'details': test
                })
        
        # Check for encoding-specific issues
        encoding_failures = [r for r in self.test_results 
                           if 'encoding' in r and r.get('status') == 'FAIL']
        
        if encoding_failures:
            issues.append({
                'type': 'encoding_issue',
                'description': 'Some CSV encodings are being rejected by validation',
                'affected_encodings': [r.get('encoding') for r in encoding_failures],
                'count': len(encoding_failures)
            })
        
        # Check for signature validation issues
        signature_failures = [r for r in self.test_results 
                            if 'signature_desc' in r and r.get('status') == 'FAIL']
        
        if signature_failures:
            issues.append({
                'type': 'signature_validation_issue',
                'description': 'Binary signature validation is too restrictive',
                'failing_signatures': [r.get('signature_desc') for r in signature_failures]
            })
        
        return issues
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Analyze results to provide specific recommendations
        failed_validations = [r for r in self.test_results 
                            if r.get('status') == 'FAIL' and 'validation_result' in r]
        
        if failed_validations:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Security Validation',
                'title': 'Relax binary signature validation for legitimate CSV files',
                'description': 'The current signature validation is too restrictive and rejects valid CSV files.',
                'implementation': '''
                Modify validate_file_security() function to:
                1. Accept CSV files that start with common headers (Date, dateOp, etc.)
                2. Allow plain text CSV without BOM
                3. Improve detection of CSV content patterns
                4. Add more flexible signature matching for various CSV formats
                ''',
                'code_changes': '''
                # In app.py, update csv_signatures list:
                csv_signatures = [
                    b'\\xef\\xbb\\xbf',  # UTF-8 BOM
                    b'dateOp', b'Date', b'date',  # Common CSV headers
                    b'Date,', b'date,',  # CSV with comma separator
                    b'Date;', b'date;',  # CSV with semicolon separator
                ]
                
                # Add fallback for plain text CSV detection:
                if not is_valid_signature:
                    try:
                        decoded = first_bytes.decode('utf-8', errors='ignore').lower()
                        if any(pattern in decoded for pattern in ['date', 'amount', 'montant', ',']):
                            is_valid_signature = True
                    except:
                        pass
                '''
            })
        
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'MIME Type Detection',
            'title': 'Enhance MIME type detection for various CSV encodings',
            'description': 'Improve magic_fallback.py to better detect CSV files with different encodings.',
            'implementation': '''
            1. Add more CSV header patterns to magic_fallback.py
            2. Improve encoding detection for non-UTF-8 files
            3. Add support for different CSV separators (semicolon, tab)
            '''
        })
        
        recommendations.append({
            'priority': 'LOW',
            'category': 'Testing',
            'title': 'Add automated CSV validation tests to CI/CD pipeline',
            'description': 'Ensure CSV validation continues to work correctly across different file formats.',
            'implementation': '''
            1. Include this test suite in automated testing
            2. Add test cases for customer-specific CSV formats
            3. Monitor validation failure rates in production
            '''
        })
        
        return recommendations


def main():
    """Main function to run comprehensive CSV validation tests"""
    print("=" * 80)
    print("CSV FILE VALIDATION COMPREHENSIVE TEST SUITE")
    print("Budget Famille v2.3 - Quality Assurance Report")
    print("=" * 80)
    
    # Initialize test suite
    tester = TestCSVValidation()
    
    # Run all tests
    report = tester.run_all_tests()
    
    # Display summary
    summary = report['test_summary']
    print(f"\n📊 TEST EXECUTION SUMMARY:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   ✅ Passed: {summary['passed']}")
    print(f"   ❌ Failed: {summary['failed']}")
    print(f"   💥 Errors: {summary['errors']}")
    print(f"   ⏭️  Skipped: {summary['skipped']}")
    
    # Calculate success rate
    if summary['total_tests'] > 0:
        success_rate = (summary['passed'] / summary['total_tests']) * 100
        print(f"   📈 Success Rate: {success_rate:.1f}%")
    
    # Display issues if any
    if report['issues_identified']:
        print(f"\n🚨 ISSUES IDENTIFIED ({len(report['issues_identified'])}):")
        for i, issue in enumerate(report['issues_identified'], 1):
            print(f"   {i}. {issue['type'].upper()}: {issue['description']}")
    
    # Display recommendations
    print(f"\n💡 RECOMMENDATIONS ({len(report['recommendations'])}):")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"   {i}. [{rec['priority']}] {rec['title']}")
    
    # Save detailed report
    report_file = '/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend/csv_validation_test_report.json'
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"\n❌ Failed to save report: {e}")
    
    print("=" * 80)
    
    return report


if __name__ == "__main__":
    report = main()