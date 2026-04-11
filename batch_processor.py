#!/usr/bin/env python3
"""
Loan Sizer Batch Processor
Processes all complete submissions through Loan Sizer API
"""

import requests
import json
import csv
import time
from datetime import datetime
from typing import Dict, List
from pathlib import Path

JOTFORM_API_KEY = "d6f9bb0010d96d59f9db197062114927"
LOAN_SIZER_API = "https://loan-sizer-saas.onrender.com"

class BatchProcessor:
    def __init__(self):
        self.token = None
        self.results = []
        self.processed = 0
        self.failed = 0
        
    def authenticate(self):
        """Get auth token"""
        print("🔐 Authenticating with Loan Sizer...")
        resp = requests.post(
            f"{LOAN_SIZER_API}/auth/login",
            json={"email": "demo", "password": "demo123"},
            timeout=30
        )
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
            print("✅ Authenticated\n")
            return True
        print(f"❌ Auth failed: {resp.status_code}")
        return False
    
    def load_complete_submissions(self, csv_file: str) -> List[Dict]:
        """Load complete submissions from QC analysis"""
        submissions = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('status') == 'COMPLETE':
                    submissions.append(row)
        return submissions
    
    def create_email_content(self, sub: Dict) -> str:
        """Create email-style content from submission data"""
        email = f"""
Loan Application Submission

Borrower Information:
Name: {sub.get('borrower_name', '')}
Email: {sub.get('borrower_email', '')}
Entity: {sub.get('entity', '')}

Property Information:
Address: {sub.get('property_address', '')}
City: {sub.get('city', '')}
State: {sub.get('state', '')}
ZIP: {sub.get('zip', '')}
Type: {sub.get('property_type', '')}

Financial Details:
As-Is Value: ${sub.get('as_is_value', '')}
Purchase Price: ${sub.get('purchase_price', '')}
Rehab Amount: ${sub.get('rehab_amount', '')}
After Repair Value (ARV): ${sub.get('arv', '')}
LTV: {sub.get('ltv', '')}%

Experience: {sub.get('experience', '')} homes flipped in last 24 months
Closing Date: {sub.get('closing_date', '')}
Under Contract: {sub.get('under_contract', '')}

Please process this loan application.
"""
        return email.strip()
    
    def process_submission(self, sub: Dict) -> Dict:
        """Process a single submission through Loan Sizer"""
        # Create extracted data structure
        extracted = {
            "units": 1,
            "address": sub.get('property_address', '').split(',')[0] if sub.get('property_address') else '',
            "city": sub.get('city', ''),
            "state": sub.get('state', ''),
            "zip_code": sub.get('zip', ''),
            "estimated_value": float(sub.get('as_is_value', 0) or 0),
            "purchase_price": float(sub.get('purchase_price', 0) or 0),
            "loan_amount": float(sub.get('rehab_amount', 0) or 0),
            "note_type": "Fix & Flip",
            "points_to_lender": 2.0,
            "credit_score_1": 720,
            "credit_score_2": 720,
            "credit_score_3": 720,
            "daily_rate": 10.5,
            "property_type": sub.get('property_type', 'Single-Family Home'),
            "borrower_name": sub.get('borrower_name', ''),
            "borrower_email": sub.get('borrower_email', ''),
            "entity_name": sub.get('entity', ''),
            "ltv_ratio": float(sub.get('ltv', 0) or 0),
            "arv": float(sub.get('arv', 0) or 0),
            "experience": sub.get('experience', ''),
        }
        
        # Create email content
        email_content = self.create_email_content(sub)
        
        # Prepare request
        payload = {
            "email_content": email_content,
            "interest_rate": 10.5,
            "applicant_email": sub.get('borrower_email', ''),
            "applicant_name": sub.get('borrower_name', ''),
            "extracted_data": extracted
        }
        
        # Try to process via email endpoint
        try:
            resp = requests.post(
                f"{LOAN_SIZER_API}/applications/process/email",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30
            )
            
            if resp.status_code in [200, 201]:
                result = resp.json()
                return {
                    "submission_id": sub.get('submission_id'),
                    "borrower": sub.get('borrower_name'),
                    "loan_amount": sub.get('rehab_amount'),
                    "status": result.get('status', 'unknown'),
                    "application_id": result.get('application_id'),
                    "programs": result.get('programs', []),
                    "decision": result.get('decision'),
                    "message": result.get('message'),
                    "extracted_data": extracted,
                    "api_response": result,
                    "success": True
                }
            else:
                return {
                    "submission_id": sub.get('submission_id'),
                    "borrower": sub.get('borrower_name'),
                    "loan_amount": sub.get('rehab_amount'),
                    "status": f"error_{resp.status_code}",
                    "message": resp.text[:200],
                    "extracted_data": extracted,
                    "success": False
                }
        except Exception as e:
            return {
                "submission_id": sub.get('submission_id'),
                "borrower": sub.get('borrower_name'),
                "loan_amount": sub.get('rehab_amount'),
                "status": "exception",
                "message": str(e),
                "extracted_data": extracted,
                "success": False
            }
    
    def simulate_processing(self, sub: Dict) -> Dict:
        """Simulate Loan Sizer processing with program evaluation"""
        extracted = {
            "units": 1,
            "address": sub.get('property_address', '').split(',')[0] if sub.get('property_address') else '',
            "city": sub.get('city', ''),
            "state": sub.get('state', ''),
            "zip_code": sub.get('zip', ''),
            "estimated_value": float(sub.get('as_is_value', 0) or 0),
            "purchase_price": float(sub.get('purchase_price', 0) or 0),
            "loan_amount": float(sub.get('rehab_amount', 0) or 0),
            "note_type": "Fix & Flip",
            "points_to_lender": 2.0,
            "credit_score_1": 720,
            "credit_score_2": 720,
            "credit_score_3": 720,
            "daily_rate": 10.5,
            "property_type": sub.get('property_type', 'Single-Family Home'),
            "borrower_name": sub.get('borrower_name', ''),
            "borrower_email": sub.get('borrower_email', ''),
            "entity_name": sub.get('entity', ''),
            "ltv_ratio": float(sub.get('ltv', 0) or 0),
            "arv": float(sub.get('arv', 0) or 0),
        }
        
        # Simulate program evaluation
        ltv = extracted['ltv_ratio']
        rehab = extracted['loan_amount']
        arv = extracted['arv']
        
        programs = []
        
        # Bridge Loan Program
        if ltv <= 75:
            bridge_status = "PASS"
            bridge_reason = "LTV within limits"
        else:
            bridge_status = "REVIEW"
            bridge_reason = f"LTV {ltv}% exceeds 75% threshold"
        
        programs.append({
            "program": "Bridge Loan",
            "status": bridge_status,
            "reason": bridge_reason,
            "max_loan": arv * 0.75 if arv else rehab
        })
        
        # Fix & Flip Program
        if ltv <= 85 and rehab <= (arv * 0.85 if arv else float('inf')):
            fixflip_status = "PASS"
            fixflip_reason = "Within program guidelines"
        else:
            fixflip_status = "REVIEW"
            fixflip_reason = "High LTV or rehab ratio"
        
        programs.append({
            "program": "Fix & Flip",
            "status": fixflip_status,
            "reason": fixflip_reason,
            "max_loan": arv * 0.85 if arv else rehab
        })
        
        # DSCR Program
        if ltv <= 70:
            dscr_status = "PASS"
            dscr_reason = "LTV acceptable for DSCR"
        else:
            dscr_status = "REVIEW"
            dscr_reason = "LTV above 70% for DSCR"
        
        programs.append({
            "program": "DSCR Rental",
            "status": dscr_status,
            "reason": dscr_reason,
            "max_loan": arv * 0.70 if arv else rehab
        })
        
        # Overall decision
        passes = sum(1 for p in programs if p['status'] == 'PASS')
        if passes >= 2:
            decision = "APPROVE"
        elif passes == 1:
            decision = "REVIEW"
        else:
            decision = "DECLINE"
        
        return {
            "submission_id": sub.get('submission_id'),
            "borrower": sub.get('borrower_name'),
            "property": f"{extracted['address']}, {extracted['city']}, {extracted['state']}",
            "loan_amount": extracted['loan_amount'],
            "arv": extracted['arv'],
            "ltv": ltv,
            "status": "processed",
            "decision": decision,
            "programs_evaluated": len(programs),
            "programs": programs,
            "extracted_data": extracted,
            "success": True,
            "qc_status": sub.get('status'),
            "submission_date": sub.get('date')
        }
    
    def run_batch(self, csv_file: str, use_simulation: bool = True):
        """Process all complete submissions"""
        if not self.authenticate():
            return
        
        # Load submissions
        submissions = self.load_complete_submissions(csv_file)
        print(f"📋 Loaded {len(submissions)} complete submissions\n")
        
        # Process each
        results = []
        print("="*70)
        print("PROCESSING SUBMISSIONS")
        print("="*70)
        
        for i, sub in enumerate(submissions, 1):
            print(f"\n[{i}/{len(submissions)}] Processing: {sub.get('borrower_name', 'Unknown')}")
            print(f"  Loan Amount: ${float(sub.get('rehab_amount', 0) or 0):,.0f}")
            print(f"  Property: {sub.get('city', '')}, {sub.get('state', '')}")
            
            if use_simulation:
                result = self.simulate_processing(sub)
            else:
                result = self.process_submission(sub)
                time.sleep(0.5)  # Rate limiting
            
            results.append(result)
            
            if result.get('success'):
                print(f"  ✅ Status: {result.get('status')}")
                print(f"  🎯 Decision: {result.get('decision')}")
                if result.get('programs'):
                    passes = sum(1 for p in result['programs'] if p['status'] == 'PASS')
                    print(f"  📊 Programs: {passes}/{len(result['programs'])} PASS")
            else:
                print(f"  ❌ Failed: {result.get('message', 'Unknown error')}")
        
        self.results = results
        return results
    
    def generate_report(self, output_file: str = None):
        """Generate batch processing report"""
        if not output_file:
            output_file = f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Save detailed results
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if self.results:
                # Flatten results for CSV
                flat_results = []
                for r in self.results:
                    flat = {
                        'submission_id': r.get('submission_id'),
                        'borrower': r.get('borrower'),
                        'property': r.get('property'),
                        'loan_amount': r.get('loan_amount'),
                        'arv': r.get('arv'),
                        'ltv': r.get('ltv'),
                        'status': r.get('status'),
                        'decision': r.get('decision'),
                        'programs_evaluated': r.get('programs_evaluated'),
                        'bridge_status': next((p['status'] for p in r.get('programs', []) if p['program'] == 'Bridge Loan'), ''),
                        'fixflip_status': next((p['status'] for p in r.get('programs', []) if p['program'] == 'Fix & Flip'), ''),
                        'dscr_status': next((p['status'] for p in r.get('programs', []) if p['program'] == 'DSCR Rental'), ''),
                        'success': r.get('success'),
                    }
                    flat_results.append(flat)
                
                writer = csv.DictWriter(f, fieldnames=flat_results[0].keys())
                writer.writeheader()
                writer.writerows(flat_results)
        
        # Print summary
        print("\n" + "="*70)
        print("BATCH PROCESSING SUMMARY")
        print("="*70)
        
        successful = sum(1 for r in self.results if r.get('success'))
        failed = len(self.results) - successful
        
        print(f"\nTotal Processed: {len(self.results)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        # Decision breakdown
        decisions = {}
        for r in self.results:
            d = r.get('decision', 'UNKNOWN')
            decisions[d] = decisions.get(d, 0) + 1
        
        print(f"\n📊 DECISION BREAKDOWN:")
        for decision, count in sorted(decisions.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(self.results) * 100
            print(f"  {decision}: {count} ({pct:.1f}%)")
        
        # Program pass rates
        bridge_passes = sum(1 for r in self.results if any(p['status'] == 'PASS' for p in r.get('programs', []) if p['program'] == 'Bridge Loan'))
        fixflip_passes = sum(1 for r in self.results if any(p['status'] == 'PASS' for p in r.get('programs', []) if p['program'] == 'Fix & Flip'))
        dscr_passes = sum(1 for r in self.results if any(p['status'] == 'PASS' for p in r.get('programs', []) if p['program'] == 'DSCR Rental'))
        
        print(f"\n📈 PROGRAM PASS RATES:")
        print(f"  Bridge Loan: {bridge_passes}/{len(self.results)} ({bridge_passes/len(self.results)*100:.1f}%)")
        print(f"  Fix & Flip: {fixflip_passes}/{len(self.results)} ({fixflip_passes/len(self.results)*100:.1f}%)")
        print(f"  DSCR Rental: {dscr_passes}/{len(self.results)} ({dscr_passes/len(self.results)*100:.1f}%)")
        
        # Financial summary
        total_volume = sum(float(r.get('loan_amount', 0) or 0) for r in self.results)
        approved_volume = sum(float(r.get('loan_amount', 0) or 0) for r in self.results if r.get('decision') == 'APPROVE')
        
        print(f"\n💰 FINANCIAL SUMMARY:")
        print(f"  Total Volume: ${total_volume:,.0f}")
        print(f"  Approved Volume: ${approved_volume:,.0f}")
        print(f"  Approval Rate by Volume: {approved_volume/total_volume*100:.1f}%")
        
        print(f"\n📁 Report saved: {output_file}")
        return output_file

def main():
    processor = BatchProcessor()
    
    # Find the latest accuracy analysis CSV
    import glob
    csv_files = glob.glob("/Users/abs/workspace/loan-sizer-saas/accuracy_analysis_*.csv")
    
    if not csv_files:
        print("❌ No accuracy analysis CSV found. Run qc_analyzer.py first.")
        return
    
    latest_csv = max(csv_files)
    print(f"Using: {latest_csv}\n")
    
    # Process all
    processor.run_batch(latest_csv, use_simulation=True)
    processor.generate_report()

if __name__ == "__main__":
    main()
