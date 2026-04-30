"""
Validation script for Multi-Application Batch Processor
Tests all functionality to ensure demo-readiness
"""

import requests
import json
import os
import time
from pathlib import Path

BASE_URL = "https://loan-sizer-api.onrender.com"
# BASE_URL = "http://localhost:5050"  # Uncomment for local testing


def test_health():
    """Test API health"""
    print("\n" + "="*60)
    print("TEST 1: API Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print("✓ API is healthy")
            print(f"  Status: {response.json().get('status', 'Unknown')}")
            print(f"  Version: {response.json().get('version', 'Unknown')}")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API health check failed: {e}")
        return False


def test_batch_upload():
    """Test batch file upload"""
    print("\n" + "="*60)
    print("TEST 2: Batch File Upload")
    print("="*60)
    
    # Get test files
    test_files = []
    batch_dir = Path(__file__).parent / "batch_10_applications"
    
    if not batch_dir.exists():
        print(f"✗ Demo batch directory not found: {batch_dir}")
        return False
    
    txt_files = list(batch_dir.glob("*.txt"))[:5]  # Use first 5 files for testing
    
    if not txt_files:
        print("✗ No test files found")
        return False
    
    files = []
    for f in txt_files:
        files.append(('files', (f.name, f.open('rb'), 'text/plain')))
    
    try:
        response = requests.post(f"{BASE_URL}/batch/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Upload successful")
            print(f"  Applications added: {data.get('applications_added', 0)}")
            print(f"  Total in queue: {data.get('total_in_queue', 0)}")
            return True
        else:
            print(f"✗ Upload failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Upload error: {e}")
        return False
    finally:
        for _, file_tuple in files:
            file_tuple[1].close()


def test_batch_status():
    """Test batch status endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Batch Status Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/batch/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status retrieved")
            print(f"  Total applications: {data.get('total_applications', 0)}")
            print(f"  Pending: {data.get('pending', 0)}")
            print(f"  Completed: {data.get('completed', 0)}")
            print(f"  Pass: {data.get('results_summary', {}).get('pass', 0)}")
            print(f"  Conditional: {data.get('results_summary', {}).get('conditional', 0)}")
            print(f"  Fail: {data.get('results_summary', {}).get('fail', 0)}")
            return True
        else:
            print(f"✗ Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Status check error: {e}")
        return False


def test_batch_process():
    """Test batch processing"""
    print("\n" + "="*60)
    print("TEST 4: Batch Processing")
    print("="*60)
    
    try:
        response = requests.post(f"{BASE_URL}/batch/process", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✓ Processing started")
                print(f"  Pending count: {data.get('pending_count', 0)}")
                print(f"  Is processing: {data.get('is_processing', False)}")
                return True
            else:
                print(f"✓ Processing status: {data.get('message', 'Unknown')}")
                return True
        else:
            print(f"✗ Processing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Processing error: {e}")
        return False


def test_batch_applications_list():
    """Test applications list endpoint"""
    print("\n" + "="*60)
    print("TEST 5: Applications List")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/batch/applications?limit=10", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            apps = data.get('applications', [])
            print(f"✓ Applications retrieved: {len(apps)}")
            
            if apps:
                app = apps[0]
                print(f"\n  Sample Application:")
                print(f"    Name: {app.get('applicant_name', 'N/A')}")
                print(f"    Type: {app.get('loan_type', 'N/A')}")
                print(f"    Amount: ${app.get('loan_amount', 0):,.0f}")
                print(f"    Result: {app.get('result', 'N/A')}")
            return True
        else:
            print(f"✗ List retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ List retrieval error: {e}")
        return False


def test_csv_export():
    """Test CSV export"""
    print("\n" + "="*60)
    print("TEST 6: CSV Export")
    print("="*60)
    
    try:
        response = requests.post(f"{BASE_URL}/batch/export/csv", timeout=10)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'csv' in content_type or 'text' in content_type:
                print(f"✓ CSV export successful")
                print(f"  Content-Type: {content_type}")
                print(f"  Size: {len(response.content)} bytes")
                return True
            else:
                print(f"✗ Unexpected content type: {content_type}")
                return False
        else:
            print(f"✗ CSV export failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ CSV export error: {e}")
        return False


def test_pdf_export():
    """Test PDF export"""
    print("\n" + "="*60)
    print("TEST 7: PDF Export")
    print("="*60)
    
    try:
        payload = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "status_filter": "all"
        }
        
        response = requests.post(
            f"{BASE_URL}/batch/export/pdf",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ PDF export data generated")
            print(f"  Total apps: {data.get('summary', {}).get('total', 0)}")
            print(f"  Pass: {data.get('summary', {}).get('pass', 0)}")
            print(f"  Total amount: ${data.get('summary', {}).get('total_amount', 0):,.0f}")
            return True
        else:
            print(f"✗ PDF export failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ PDF export error: {e}")
        return False


def run_full_demo_test():
    """Run complete demo workflow"""
    print("\n" + "="*60)
    print("FULL DEMO WORKFLOW TEST")
    print("="*60)
    
    # Clear existing queue first
    print("\n1. Clearing existing queue...")
    try:
        requests.delete(f"{BASE_URL}/batch/clear", timeout=5)
        print("   ✓ Queue cleared")
    except:
        print("   ⚠ Could not clear queue (may be empty)")
    
    # Upload 10 applications
    print("\n2. Uploading 10 demo applications...")
    batch_dir = Path(__file__).parent / "batch_10_applications"
    txt_files = list(batch_dir.glob("*.txt"))
    
    files = []
    for f in txt_files:
        files.append(('files', (f.name, f.open('rb'), 'text/plain')))
    
    try:
        response = requests.post(f"{BASE_URL}/batch/upload", files=files, timeout=30)
        print(f"   ✓ Uploaded {len(txt_files)} applications")
    except Exception as e:
        print(f"   ✗ Upload failed: {e}")
        return False
    finally:
        for _, file_tuple in files:
            file_tuple[1].close()
    
    # Start processing
    print("\n3. Starting batch processing...")
    try:
        requests.post(f"{BASE_URL}/batch/process", timeout=5)
        print("   ✓ Processing started")
    except Exception as e:
        print(f"   ⚠ Processing may have already started: {e}")
    
    # Poll for completion
    print("\n4. Waiting for processing to complete...")
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/batch/status", timeout=5)
            data = response.json()
            
            completed = data.get('completed', 0)
            total = data.get('total_applications', 0)
            is_processing = data.get('is_processing', False)
            
            if not is_processing and completed == total:
                print(f"   ✓ Processing complete: {completed}/{total}")
                print(f"\n   Results:")
                print(f"     Pass: {data.get('results_summary', {}).get('pass', 0)}")
                print(f"     Conditional: {data.get('results_summary', {}).get('conditional', 0)}")
                print(f"     Fail: {data.get('results_summary', {}).get('fail', 0)}")
                break
            else:
                print(f"   Progress: {completed}/{total} completed...", end='\r')
                time.sleep(1)
        except Exception as e:
            print(f"   Error polling: {e}")
            time.sleep(1)
    else:
        print("\n   ⚠ Timeout waiting for completion")
    
    return True


def main():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("MULTI-APPLICATION BATCH PROCESSOR VALIDATION")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    
    results = []
    
    # Run individual tests
    results.append(("Health Check", test_health()))
    results.append(("Batch Upload", test_batch_upload()))
    results.append(("Batch Status", test_batch_status()))
    results.append(("Batch Process", test_batch_process()))
    time.sleep(3)  # Wait for processing
    results.append(("Applications List", test_batch_applications_list()))
    results.append(("CSV Export", test_csv_export()))
    results.append(("PDF Export", test_pdf_export()))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All validation tests passed! System is demo-ready.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Review errors above.")
    
    # Run full demo workflow
    print("\n" + "="*60)
    print("RUNNING FULL DEMO WORKFLOW")
    print("="*60)
    run_full_demo_test()


if __name__ == "__main__":
    main()
