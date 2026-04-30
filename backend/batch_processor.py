"""
Multi-Application Batch Processor for Loan Sizer
Handles processing multiple loan applications simultaneously
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import csv
import io


class LoanType(Enum):
    DSCR_1_4 = "DSCR 1-4 Unit"
    DSCR_4_9 = "DSCR 4-9 Unit"
    DSCR_MIXED = "DSCR Mixed Use"
    RTL = "Fix & Flip / RTL"
    BRIDGE = "Bridge"
    GROUND_UP = "Ground Up Construction"


class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class BatchLoanApplication:
    id: str
    applicant_name: str
    entity_name: str
    loan_type: LoanType
    loan_amount: float
    property_address: str
    property_city: str
    property_state: str
    fico_score: int
    dscr_ratio: Optional[float] = None
    ltv_ratio: Optional[float] = None
    noi: Optional[float] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    result: str = "Pending"
    result_details: Dict[str, Any] = None
    error_message: str = ""
    processed_at: Optional[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.result_details is None:
            self.result_details = {}


class ApplicationParser:
    """Parse various file formats (CSV, TXT, JSON) into loan applications"""
    
    @staticmethod
    def parse_csv(content: str) -> List[Dict[str, Any]]:
        """Parse CSV content into loan applications"""
        applications = []
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            applications.append(ApplicationParser._normalize_row(dict(row)))
        return applications
    
    @staticmethod
    def parse_txt(content: str) -> List[Dict[str, Any]]:
        """Parse text file with key:value pairs into loan applications"""
        applications = []
        # Split by blank lines to get individual applications
        apps_text = content.split('\n\n')
        
        for app_text in apps_text:
            if not app_text.strip():
                continue
            
            app_data = {}
            for line in app_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    app_data[key.strip().lower().replace(' ', '_')] = value.strip()
            
            if app_data:
                applications.append(ApplicationParser._normalize_row(app_data))
        
        return applications
    
    @staticmethod
    def parse_json(content: str) -> List[Dict[str, Any]]:
        """Parse JSON content into loan applications"""
        data = json.loads(content)
        if isinstance(data, list):
            return [ApplicationParser._normalize_row(item) for item in data]
        elif isinstance(data, dict):
            return [ApplicationParser._normalize_row(data)]
        return []
    
    @staticmethod
    def _normalize_row(row: Dict[str, str]) -> Dict[str, Any]:
        """Normalize field names from various formats"""
        field_mapping = {
            # Applicant name variations
            'applicant_name': ['applicant_name', 'applicant', 'borrower_name', 'borrower', 'name'],
            'entity_name': ['entity_name', 'entity', 'company', 'llc', 'business_name'],
            'loan_type': ['loan_type', 'type', 'loan_program', 'program'],
            'loan_amount': ['loan_amount', 'amount', 'loan', 'requested_amount', 'loan_request'],
            'property_address': ['property_address', 'address', 'street_address', 'property'],
            'city': ['city', 'property_city'],
            'state': ['state', 'property_state', 'st'],
            'fico_score': ['fico_score', 'fico', 'credit_score', 'score'],
            'dscr_ratio': ['dscr', 'dscr_ratio', 'debt_service_coverage_ratio'],
            'ltv_ratio': ['ltv', 'ltv_ratio', 'loan_to_value'],
            'noi': ['noi', 'net_operating_income', 'operating_income'],
        }
        
        normalized = {}
        for standard_field, variations in field_mapping.items():
            for variation in variations:
                if variation in row and row[variation]:
                    normalized[standard_field] = row[variation]
                    break
        
        return normalized


class BatchProcessor:
    """Process multiple loan applications in batch"""
    
    def __init__(self):
        self.processing_queue: List[BatchLoanApplication] = []
        self.completed_applications: List[BatchLoanApplication] = []
        self.is_processing = False
    
    def add_applications(self, file_contents: List[Dict[str, str]]) -> List[str]:
        """Add applications from uploaded files"""
        application_ids = []
        
        for file_info in file_contents:
            filename = file_info.get('filename', '')
            content = file_info.get('content', '')
            file_type = filename.split('.')[-1].lower() if '.' in filename else 'txt'
            
            try:
                # Parse based on file type
                if file_type == 'csv':
                    parsed = ApplicationParser.parse_csv(content)
                elif file_type == 'json':
                    parsed = ApplicationParser.parse_json(content)
                else:
                    parsed = ApplicationParser.parse_txt(content)
                
                # Create application objects
                for idx, app_data in enumerate(parsed):
                    app_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.processing_queue)}_{idx}"
                    
                    loan_app = BatchLoanApplication(
                        id=app_id,
                        applicant_name=app_data.get('applicant_name', 'Unknown'),
                        entity_name=app_data.get('entity_name', ''),
                        loan_type=self._parse_loan_type(app_data.get('loan_type', 'DSCR 1-4 Unit')),
                        loan_amount=self._parse_amount(app_data.get('loan_amount', '0')),
                        property_address=app_data.get('property_address', ''),
                        property_city=app_data.get('city', ''),
                        property_state=app_data.get('state', ''),
                        fico_score=self._parse_int(app_data.get('fico_score', '0')),
                        dscr_ratio=self._parse_float(app_data.get('dscr_ratio')),
                        ltv_ratio=self._parse_float(app_data.get('ltv_ratio')),
                        noi=self._parse_float(app_data.get('noi'))
                    )
                    
                    self.processing_queue.append(loan_app)
                    application_ids.append(app_id)
                    
            except Exception as e:
                print(f"Error parsing {filename}: {e}")
                continue
        
        return application_ids
    
    async def process_all(self, progress_callback=None):
        """Process all applications in the queue"""
        self.is_processing = True
        
        for app in self.processing_queue:
            if app.status != ProcessingStatus.PENDING:
                continue
            
            app.status = ProcessingStatus.PROCESSING
            
            if progress_callback:
                await progress_callback(app)
            
            try:
                # Simulate processing delay
                await asyncio.sleep(0.5)
                
                # Perform loan analysis
                result = self._analyze_loan(app)
                app.result = result['status']
                app.result_details = result['details']
                app.status = ProcessingStatus.COMPLETED
                app.processed_at = datetime.now().isoformat()
                
                self.completed_applications.append(app)
                
            except Exception as e:
                app.status = ProcessingStatus.ERROR
                app.error_message = str(e)
                app.result = "Error"
            
            if progress_callback:
                await progress_callback(app)
        
        self.is_processing = False
    
    def _analyze_loan(self, app: BatchLoanApplication) -> Dict[str, Any]:
        """Analyze a single loan application"""
        issues = []
        warnings = []
        
        # FICO check
        if app.fico_score < 620:
            issues.append(f"FICO score {app.fico_score} below minimum (620)")
        elif app.fico_score < 680:
            warnings.append("FICO score below preferred threshold (680)")
        
        # DSCR check for DSCR loans
        if app.loan_type in [LoanType.DSCR_1_4, LoanType.DSCR_4_9, LoanType.DSCR_MIXED]:
            if app.dscr_ratio is not None and app.dscr_ratio < 1.0:
                issues.append(f"DSCR {app.dscr_ratio:.2f} below 1.0 minimum")
            elif app.dscr_ratio is not None and app.dscr_ratio < 1.25:
                warnings.append(f"DSCR {app.dscr_ratio:.2f} below preferred 1.25")
        
        # LTV check
        if app.ltv_ratio is not None:
            max_ltv = 0.80
            if app.loan_type == LoanType.RTL:
                max_ltv = 0.90
            elif app.loan_type == LoanType.BRIDGE:
                max_ltv = 0.85
            
            if app.ltv_ratio > max_ltv:
                issues.append(f"LTV {app.ltv_ratio:.1%} exceeds maximum {max_ltv:.0%}")
        
        # Loan amount check
        max_loan = 3500000
        if app.loan_amount > max_loan:
            issues.append(f"Loan amount ${app.loan_amount:,.0f} exceeds maximum ${max_loan:,.0f}")
        
        # Determine result
        if issues:
            status = "FAIL"
        elif warnings:
            status = "CONDITIONAL"
        else:
            status = "PASS"
        
        return {
            'status': status,
            'details': {
                'issues': issues,
                'warnings': warnings,
                'fico_check': 'PASS' if app.fico_score >= 620 else 'FAIL',
                'dscr_check': 'PASS' if (app.dscr_ratio is None or app.dscr_ratio >= 1.0) else 'FAIL',
                'ltv_check': 'PASS' if (app.ltv_ratio is None or app.ltv_ratio <= 0.80) else 'FAIL',
                'recommendation': 'Approve' if status == 'PASS' else ('Review' if status == 'CONDITIONAL' else 'Decline')
            }
        }
    
    def get_all_applications(self) -> List[Dict]:
        """Get all applications (queue + completed)"""
        all_apps = self.processing_queue + self.completed_applications
        return [self._app_to_dict(app) for app in all_apps]
    
    def get_by_status(self, status: str) -> List[Dict]:
        """Get applications filtered by status"""
        all_apps = self.get_all_applications()
        if status == 'all':
            return all_apps
        return [app for app in all_apps if app['status'] == status]
    
    def get_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get applications filtered by date range"""
        all_apps = self.get_all_applications()
        filtered = []
        
        for app in all_apps:
            if app.get('processed_at'):
                app_date = datetime.fromisoformat(app['processed_at']).date()
                start = datetime.fromisoformat(start_date).date() if start_date else None
                end = datetime.fromisoformat(end_date).date() if end_date else None
                
                if start and app_date < start:
                    continue
                if end and app_date > end:
                    continue
                
                filtered.append(app)
        
        return filtered
    
    def export_to_dict(self, applications: List[Dict] = None) -> Dict[str, Any]:
        """Export applications for PDF generation"""
        if applications is None:
            applications = self.get_all_applications()
        
        summary = {
            'total': len(applications),
            'pass': len([a for a in applications if a['result'] == 'PASS']),
            'conditional': len([a for a in applications if a['result'] == 'CONDITIONAL']),
            'fail': len([a for a in applications if a['result'] == 'FAIL']),
            'pending': len([a for a in applications if a['result'] == 'Pending']),
            'total_amount': sum(a['loan_amount'] for a in applications),
            'pass_amount': sum(a['loan_amount'] for a in applications if a['result'] == 'PASS']),
            'date_range': {
                'from': min((a['processed_at'] for a in applications if a.get('processed_at')), default=None),
                'to': max((a['processed_at'] for a in applications if a.get('processed_at')), default=None)
            }
        }
        
        return {
            'export_date': datetime.now().isoformat(),
            'summary': summary,
            'applications': applications
        }
    
    def _app_to_dict(self, app: BatchLoanApplication) -> Dict:
        """Convert application to dictionary"""
        return {
            'id': app.id,
            'applicant_name': app.applicant_name,
            'entity_name': app.entity_name,
            'loan_type': app.loan_type.value,
            'loan_amount': app.loan_amount,
            'property_address': app.property_address,
            'property_city': app.property_city,
            'property_state': app.property_state,
            'fico_score': app.fico_score,
            'dscr_ratio': app.dscr_ratio,
            'ltv_ratio': app.ltv_ratio,
            'status': app.status.value,
            'result': app.result,
            'result_details': app.result_details,
            'error_message': app.error_message,
            'created_at': app.created_at,
            'processed_at': app.processed_at
        }
    
    def _parse_loan_type(self, value: str) -> LoanType:
        """Parse loan type string to enum"""
        value_lower = value.lower()
        
        if '1-4' in value_lower or '1 to 4' in value_lower:
            return LoanType.DSCR_1_4
        elif '4-9' in value_lower or '4 to 9' in value_lower:
            return LoanType.DSCR_4_9
        elif 'mixed' in value_lower:
            return LoanType.DSCR_MIXED
        elif 'rtl' in value_lower or 'fix' in value_lower or 'flip' in value_lower:
            return LoanType.RTL
        elif 'bridge' in value_lower:
            return LoanType.BRIDGE
        elif 'ground' in value_lower or 'construction' in value_lower:
            return LoanType.GROUND_UP
        else:
            return LoanType.DSCR_1_4
    
    def _parse_amount(self, value: str) -> float:
        """Parse amount string to float"""
        if not value:
            return 0.0
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,\s]', '', str(value))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _parse_int(self, value: str) -> int:
        """Parse integer string"""
        if not value:
            return 0
        try:
            return int(float(re.sub(r'[,\s]', '', str(value))))
        except ValueError:
            return 0
    
    def _parse_float(self, value: Optional[str]) -> Optional[float]:
        """Parse float string"""
        if not value:
            return None
        try:
            return float(re.sub(r'[%$,\s]', '', str(value)))
        except ValueError:
            return None


# Global batch processor instance
batch_processor = BatchProcessor()
