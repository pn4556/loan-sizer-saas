#!/usr/bin/env python3
"""
Loan Sizer QC Analyzer
Analyzes Jotform submissions and validates data quality
"""

import requests
import json
import csv
from datetime import datetime
from typing import Dict, List

JOTFORM_API_KEY = "d6f9bb0010d96d59f9db197062114927"

class QCAnalyzer:
    def __init__(self):
        self.base_url = "https://api.jotform.com"
        self.results = []
        
    def fetch_submissions(self, form_id: str, limit: int = 50) -> List[Dict]:
        """Fetch submissions from Jotform"""
        print(f"Fetching up to {limit} submissions from form {form_id}...")
        
        all_subs = []
        offset = 0
        
        while len(all_subs) < limit:
            resp = requests.get(
                f"{self.base_url}/form/{form_id}/submissions",
                headers={"APIKEY": JOTFORM_API_KEY},
                params={"limit": 100, "offset": offset},
                timeout=30
            )
            
            if resp.status_code != 200:
                print(f"Error: {resp.status_code}")
                break
                
            subs = resp.json().get("content", [])
            if not subs:
                break
                
            all_subs.extend(subs)
            offset += len(subs)
            
            if len(subs) < 100:
                break
        
        return all_subs[:limit]
    
    def analyze_submission(self, submission: Dict) -> Dict:
        """Analyze a single submission for QC"""
        answers = submission.get("answers", {})
        
        # Extract fields
        def get(qid, default=None):
            return answers.get(qid, {}).get("answer", default)
        
        def parse_money(val):
            if not val:
                return None
            try:
                return float(str(val).replace(",", "").replace("$", ""))
            except:
                return None
        
        # Get address components
        prop_addr = get("57", {})
        if isinstance(prop_addr, dict):
            street = prop_addr.get("addr_line1", "")
            city = prop_addr.get("city", "")
            state = prop_addr.get("state", "")
            zip_code = prop_addr.get("postal", "")
        else:
            street = city = state = zip_code = ""
        
        # Financial data
        as_is = parse_money(get("7"))
        rehab = parse_money(get("8"))
        arv = parse_money(get("10"))
        purchase = parse_money(get("55"))
        
        # Calculate LTV and other metrics
        ltv = (rehab / arv * 100) if arv and rehab else None
        
        # QC Checks
        qc_issues = []
        
        if not as_is:
            qc_issues.append("Missing As-Is Value")
        if not rehab:
            qc_issues.append("Missing Rehab Amount")
        if not arv:
            qc_issues.append("Missing ARV")
        if not purchase:
            qc_issues.append("Missing Purchase Price")
        if not street:
            qc_issues.append("Missing Property Address")
        if not get("39"):
            qc_issues.append("Missing Borrower Name")
        if not get("41"):
            qc_issues.append("Missing Borrower Email")
        if not get("29"):
            qc_issues.append("Missing Entity Name")
        
        # Validate financial logic
        if arv and as_is and arv < as_is:
            qc_issues.append("ARV less than As-Is Value")
        if arv and rehab and (rehab / arv) > 0.8:
            qc_issues.append("High rehab ratio (>80% of ARV)")
        
        return {
            "submission_id": submission.get("id"),
            "date": submission.get("created_at", "")[:10],
            "borrower_name": f"{get('39', {}).get('first', '')} {get('39', {}).get('last', '')}".strip() if isinstance(get('39'), dict) else get('39', ''),
            "borrower_email": get("41", ""),
            "entity": get("29", ""),
            "property_address": f"{street}, {city}, {state} {zip_code}".strip(", "),
            "property_type": get("11", ""),
            "as_is_value": as_is,
            "rehab_amount": rehab,
            "arv": arv,
            "purchase_price": purchase,
            "ltv_ratio": round(ltv, 1) if ltv else None,
            "experience": get("13", ""),
            "under_contract": get("71", ""),
            "closing_date": get("12", ""),
            "qc_issues": "; ".join(qc_issues) if qc_issues else "None",
            "qc_status": "PASS" if not qc_issues else "NEEDS_REVIEW",
        }
    
    def run_qc(self, form_id: str, limit: int = 50) -> List[Dict]:
        """Run QC analysis on all submissions"""
        submissions = self.fetch_submissions(form_id, limit)
        print(f"Analyzing {len(submissions)} submissions...")
        
        results = []
        for i, sub in enumerate(submissions, 1):
            if i % 10 == 0:
                print(f"  Processed {i}/{len(submissions)}...")
            result = self.analyze_submission(sub)
            results.append(result)
        
        self.results = results
        return results
    
    def generate_report(self, filename: str = None):
        """Generate CSV report"""
        if not filename:
            filename = f"qc_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not self.results:
            print("No results to export")
            return
        
        # Write CSV
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        
        # Print summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r['qc_status'] == 'PASS')
        needs_review = total - passed
        
        print("\n" + "="*60)
        print("QC ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total submissions analyzed: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"⚠️  Needs Review: {needs_review} ({needs_review/total*100:.1f}%)")
        print(f"\n📄 Report saved to: {filename}")
        
        # Show common issues
        all_issues = []
        for r in self.results:
            if r['qc_issues'] != "None":
                all_issues.extend(r['qc_issues'].split("; "))
        
        if all_issues:
            from collections import Counter
            issue_counts = Counter(all_issues)
            print("\n📊 Common Issues:")
            for issue, count in issue_counts.most_common(5):
                print(f"  - {issue}: {count} occurrences")

def main():
    analyzer = QCAnalyzer()
    
    # Form IDs
    forms = {
        "1": ("242686259921063", "Loan Application (205 subs)"),
        "2": ("242686120690053", "DSCR Questionnaire (20 subs)"),
        "3": ("242685475165062", "Fix & Flip Funding (10 subs)"),
    }
    
    print("Available Forms:")
    for k, (_, name) in forms.items():
        print(f"  {k}. {name}")
    
    choice = input("\nSelect form (1-3): ").strip()
    
    if choice not in forms:
        print("Invalid choice")
        return
    
    form_id, form_name = forms[choice]
    limit = input("How many submissions to analyze? (default 20): ").strip()
    limit = int(limit) if limit.isdigit() else 20
    
    print(f"\n{'='*60}")
    print(f"QC Analysis: {form_name}")
    print('='*60)
    
    analyzer.run_qc(form_id, limit)
    analyzer.generate_report()

if __name__ == "__main__":
    main()
