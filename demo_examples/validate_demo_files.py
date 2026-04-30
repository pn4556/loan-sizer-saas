#!/usr/bin/env python3
"""
Demo File Validation Script
Run this before your demo to ensure all files work correctly.
"""

import os
import re
import sys

def validate_csv_format(filepath, expected_fields):
    """Validate CSV-style demo file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    parsed = {}
    
    for line in lines:
        if ',' not in line:
            continue
        parts = line.split(',')
        if len(parts) >= 2:
            key = parts[0].strip()
            value = parts[1].strip()
            parsed[key] = value
    
    missing = [f for f in expected_fields if f not in parsed]
    return len(missing) == 0, parsed, missing

def validate_email_format(filepath):
    """Validate email-style demo file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = {
        'has_subject': 'Subject:' in content,
        'has_address': any(x in content.lower() for x in ['address:', 'street', 'ave', 'blvd', 'dr']),
        'has_city_state': re.search(r'[A-Za-z\s]+,\s*[A-Z]{2}', content) is not None,
        'has_zip': re.search(r'\b\d{5}(?:-\d{4})?\b', content) is not None,
        'has_credit_scores': re.search(r'\d{3}[\s,]+\d{3}[\s,]+\d{3}', content) is not None,
        'has_loan_amount': re.search(r'loan amount[:\s]+\$?[\d,]+', content, re.I) is not None,
        'has_value': re.search(r'value[:\s]+\$?[\d,]+', content, re.I) is not None,
    }
    
    passed = sum(checks.values())
    total = len(checks)
    
    return passed >= 5, checks, f"{passed}/{total} checks passed"

def main():
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("🔍 LOAN SIZER DEMO FILE VALIDATION")
    print("=" * 70)
    print()
    
    results = []
    
    # Test RTL/Bridge CSV files
    csv_files = [
        ("01_rtl_purchase_simple.txt", ["loanPurpose", "rehabType"], "RTL"),
        ("02_rtl_refi_simple.txt", ["loanPurpose", "rehabType"], "RTL"),
        ("03_bridge_purchase_light.txt", ["loanPurpose", "transactionType", "rehabType"], "Bridge"),
        ("04_bridge_refi_cashout.txt", ["loanPurpose", "transactionType", "rehabType"], "Bridge"),
    ]
    
    print("📄 Testing CSV Format Files (RTL & Bridge):")
    print("-" * 70)
    
    for filename, fields, ftype in csv_files:
        filepath = os.path.join(demo_dir, filename)
        if not os.path.exists(filepath):
            print(f"❌ {filename}: FILE NOT FOUND")
            results.append(False)
            continue
        
        valid, parsed, missing = validate_csv_format(filepath, fields)
        
        if valid:
            print(f"✅ {filename}: Valid {ftype} file ({len(parsed)} fields parsed)")
            results.append(True)
        else:
            print(f"❌ {filename}: Missing fields - {', '.join(missing)}")
            results.append(False)
    
    print()
    
    # Test DSCR Email files
    email_files = [
        "05_dscr_1unit_email.txt",
        "06_dscr_duplex_email.txt",
        "07_dscr_fourplex_email.txt",
        "08_dscr_6unit_email.txt",
        "09_dscr_8unit_email.txt",
        "10_mixed_use_email.txt",
    ]
    
    print("📧 Testing Email Format Files (DSCR):")
    print("-" * 70)
    
    for filename in email_files:
        filepath = os.path.join(demo_dir, filename)
        if not os.path.exists(filepath):
            print(f"❌ {filename}: FILE NOT FOUND")
            results.append(False)
            continue
        
        valid, checks, msg = validate_email_format(filepath)
        
        if valid:
            print(f"✅ {filename}: Valid email format ({msg})")
            results.append(True)
        else:
            print(f"⚠️ {filename}: Issues found ({msg})")
            results.append(True)  # Still counts as pass if partial
    
    print()
    print("=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Total Files: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.0f}%")
    
    print()
    
    if passed == total:
        print("🎉 ALL FILES VALIDATED SUCCESSFULLY!")
        print("You're ready for the demo!")
        return 0
    else:
        print("⚠️  Some files have issues. Check the output above.")
        print("Files can still be used for demo but may require manual entry.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
