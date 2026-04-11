#!/usr/bin/env python3
"""
Loan Sizer QC Pipeline
Pulls submissions from Jotform, processes through Loan Sizer API, generates QC report
"""

import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Configuration
JOTFORM_API_KEY = "d6f9bb0010d96d59f9db197062114927"
LOAN_SIZER_API = "https://loan-sizer-saas.onrender.com"
DEMO_CREDENTIALS = {"email": "demo", "password": "demo123"}

class LoanSizerQC:
    def __init__(self):
        self.jotform_base = "https://api.jotform.com"
        self.loan_sizer_token = None
        self.qc_results = []
        
    def get_loan_sizer_token(self) -> str:
        """Authenticate with Loan Sizer and get access token"""
        response = requests.post(
            f"{LOAN_SIZER_API}/auth/login",
            json=DEMO_CREDENTIALS,
            timeout=30
        )
        if response.status_code == 200:
            self.loan_sizer_token = response.json()["access_token"]
            print("✅ Authenticated with Loan Sizer API")
            return self.loan_sizer_token
        else:
            raise Exception(f"Auth failed: {response.status_code}")
    
    def get_jotform_submissions(self, form_id: str, limit: int = 50) -> List[Dict]:
        """Fetch submissions from Jotform"""
        print(f"📥 Fetching submissions from Jotform form {form_id}...")
        
        all_submissions = []
        offset = 0
        
        while len(all_submissions) < limit:
            response = requests.get(
                f"{self.jotform_base}/form/{form_id}/submissions",
                headers={"APIKEY": JOTFORM_API_KEY},
                params={
                    "limit": min(100, limit - len(all_submissions)),
                    "offset": offset,
                    "orderby": "created_at",
                    "direction": "desc"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"⚠️ Error fetching: {response.status_code}")
                break
                
            submissions = response.json().get("content", [])
            if not submissions:
                break
                
            all_submissions.extend(submissions)
            offset += len(submissions)
            
            if len(submissions) < 100:
                break
        
        print(f"✅ Retrieved {len(all_submissions)} submissions")
        return all_submissions[:limit]
    
    def parse_jotform_submission(self, submission: Dict) -> Dict:
        """Parse Jotform submission into structured loan data"""
        answers = submission.get("answers", {})
        
        def get_answer(qid: str, default=None):
            ans = answers.get(qid, {})
            val = ans.get("answer", default)
            if isinstance(val, dict):
                # Handle address fields
                if "addr_line1" in val:
                    addr = val.get("addr_line1", "")
                    if val.get("addr_line2"):
                        addr += f", {val['addr_line2']}"
                    addr += f", {val.get('city', '')}, {val.get('state', '')} {val.get('postal', '')}"
                    return addr.strip(", ")
                # Handle name fields
                if "first" in val:
                    return f"{val.get('first', '')} {val.get('last', '')}".strip()
                # Handle phone
                if "full" in val:
                    return val["full"]
                # Handle date
                if "month" in val:
                    return f"{val['month']}/{val['day']}/{val['year']}"
            return val
        
        # Extract property address components
        prop_addr = answers.get("57", {}).get("answer", {})
        
        loan_data = {
            "submission_id": submission.get("id"),
            "submission_date": submission.get("created_at"),
            "borrower_name": get_answer("39"),
            "borrower_email": get_answer("41"),
            "borrower_phone": get_answer("40"),
            "entity_name": get_answer("29"),
            "entity_type": get_answer("30"),
            "ein": get_answer("63"),
            
            # Property Info
            "property_address": get_answer("57"),
            "property_type": get_answer("11"),
            "purchase_price": self._parse_number(get_answer("55")),
            "as_is_value": self._parse_number(get_answer("7")),
            "arv": self._parse_number(get_answer("10")),
            "rehab_amount": self._parse_number(get_answer("8")),
            "under_contract": get_answer("71"),
            
            # Borrower Info
            "ssn": get_answer("45"),
            "dob": get_answer("47"),
            "marital_status": get_answer("46"),
            "residency": get_answer("44"),
            "experience": get_answer("13"),
            
            # Closing Info
            "closing_date": get_answer("12"),
            "closing_agent": get_answer("59"),
            "closing_agent_phone": get_answer("24"),
            "closing_agent_email": get_answer("26"),
            
            # Insurance
            "insurance_agent": get_answer("65"),
            "insurance_agent_phone": get_answer("66"),
        }
        
        return loan_data
    
    def _parse_number(self, val) -> Optional[float]:
        """Parse numeric value from string"""
        if val is None:
            return None
        try:
            # Remove commas and currency symbols
            cleaned = str(val).replace(",", "").replace("$", "").strip()
            return float(cleaned)
        except:
            return None
    
    def process_with_loan_sizer(self, loan_data: Dict) -> Dict:
        """Send loan data to Loan Sizer API for processing"""
        # Map to Loan Sizer format
        payload = {
            "units": 1,
            "address": loan_data.get("property_address", "").split(",")[0] if loan_data.get("property_address") else "",
            "city": self._extract_city(loan_data.get("property_address", "")),
            "state": self._extract_state(loan_data.get("property_address", "")),
            "zip_code": self._extract_zip(loan_data.get("property_address", "")),
            "estimated_value": loan_data.get("as_is_value") or loan_data.get("purchase_price", 0),
            "purchase_price": loan_data.get("purchase_price", 0),
            "loan_amount": loan_data.get("rehab_amount", 0),
            "note_type": "Fix & Flip",
            "points_to_lender": 2.0,
            "credit_score_1": 700,  # Default since Jotform doesn't collect credit scores
            "credit_score_2": 700,
            "credit_score_3": 700,
            "daily_rate": 10.5,
            "property_type": loan_data.get("property_type", ""),
            "borrower_name": loan_data.get("borrower_name", ""),
            "borrower_email": loan_data.get("borrower_email", ""),
            "entity_name": loan_data.get("entity_name", ""),
            "experience": loan_data.get("experience", ""),
        }
        
        # Call Loan Sizer API
        try:
            response = requests.post(
                f"{LOAN_SIZER_API}/applications",
                json=payload,
                headers={"Authorization": f"Bearer {self.loan_sizer_token}"},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": "processed",
                    "loan_sizer_id": result.get("id"),
                    "programs_evaluated": result.get("programs", []),
                    "decision": result.get("decision"),
                    "errors": None
                }
            else:
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "errors": response.text[:500]
                }
        except Exception as e:
            return {
                "status": "exception",
                "errors": str(e)
            }
    
    def _extract_city(self, address: str) -> str:
        parts = address.split(",")
        return parts[1].strip() if len(parts) > 1 else ""
    
    def _extract_state(self, address: str) -> str:
        parts = address.split(",")
        if len(parts) > 2:
            return parts[2].strip().split()[0]
        return ""
    
    def _extract_zip(self, address: str) -> str:
        parts = address.split(",")
        if len(parts) > 2:
            state_zip = parts[2].strip()
            zip_parts = state_zip.split()
            return zip_parts[1] if len(zip_parts) > 1 else ""
        return ""
    
    def run_qc(self, form_id: str, limit: int = 10) -> pd.DataFrame:
        """Run full QC pipeline"""
        print("="*60)
        print("LOAN SIZER QC PIPELINE")
        print("="*60)
        
        # Authenticate
        self.get_loan_sizer_token()
        
        # Get submissions
        submissions = self.get_jotform_submissions(form_id, limit)
        
        # Process each submission
        results = []
        for i, sub in enumerate(submissions, 1):
            print(f"\n[{i}/{len(submissions)}] Processing submission {sub.get('id')}...")
            
            # Parse Jotform data
            loan_data = self.parse_jotform_submission(sub)
            
            # Process with Loan Sizer
            ls_result = self.process_with_loan_sizer(loan_data)
            
            # Combine results
            qc_record = {
                **loan_data,
                "ls_status": ls_result.get("status"),
                "ls_decision": ls_result.get("decision"),
                "ls_errors": ls_result.get("errors"),
                "qc_passed": ls_result.get("status") == "processed"
            }
            results.append(qc_record)
            
            print(f"  Status: {ls_result.get('status')}")
            if ls_result.get('decision'):
                print(f"  Decision: {ls_result.get('decision')}")
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Generate summary
        print("\n" + "="*60)
        print("QC SUMMARY")
        print("="*60)
        print(f"Total processed: {len(df)}")
        print(f"Successful: {df['qc_passed'].sum()}")
        print(f"Failed: {(~df['qc_passed']).sum()}")
        print(f"Success rate: {df['qc_passed'].mean()*100:.1f}%")
        
        return df
    
    def export_report(self, df: pd.DataFrame, filename: str = None):
        """Export QC report to Excel"""
        if filename is None:
            filename = f"qc_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Create Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Summary sheet
            df.to_excel(writer, sheet_name='QC Results', index=False)
            
            # Summary stats
            summary_data = {
                'Metric': ['Total Processed', 'Successful', 'Failed', 'Success Rate %'],
                'Value': [
                    len(df),
                    df['qc_passed'].sum(),
                    (~df['qc_passed']).sum(),
                    f"{df['qc_passed'].mean()*100:.1f}%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"\n📄 Report exported to: {filename}")
        return filename


def main():
    """Main entry point"""
    qc = LoanSizerQC()
    
    # Form IDs
    LOAN_APP_FORM = "242686259921063"  # 205 submissions
    DSCR_FORM = "242686120690053"      # 20 submissions
    FIX_FLIP_FORM = "242685475165062"  # 10 submissions
    
    print("Which form to QC?")
    print("1. Loan Application (205 submissions)")
    print("2. DSCR Questionnaire (20 submissions)")
    print("3. Fix & Flip Funding (10 submissions)")
    
    choice = input("\nSelect (1-3) or 'all': ").strip()
    
    if choice == "1":
        form_id = LOAN_APP_FORM
    elif choice == "2":
        form_id = DSCR_FORM
    elif choice == "3":
        form_id = FIX_FLIP_FORM
    elif choice.lower() == "all":
        # Process all forms
        for name, fid in [("Loan App", LOAN_APP_FORM), ("DSCR", DSCR_FORM), ("Fix & Flip", FIX_FLIP_FORM)]:
            print(f"\n{'='*60}")
            print(f"Processing {name}")
            print('='*60)
            df = qc.run_qc(fid, limit=5)
            qc.export_report(df, f"qc_report_{name.lower().replace(' ', '_')}.xlsx")
        return
    else:
        print("Invalid choice")
        return
    
    limit = input("How many submissions to process? (default 10): ").strip()
    limit = int(limit) if limit.isdigit() else 10
    
    # Run QC
    df = qc.run_qc(form_id, limit=limit)
    
    # Export
    qc.export_report(df)


if __name__ == "__main__":
    main()
