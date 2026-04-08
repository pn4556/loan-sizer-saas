"""
Email Forward Processing System
Handles forwarded applicant emails, extracts data from body + attachments,
runs sizer, and sends results back automatically.
"""

import re
import os
import json
import base64
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

import httpx
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from processor_custom import SizerProcessor, LoanApplication
from pdf_parser import PDFLoanParser


@dataclass
class ForwardedEmail:
    """Represents a forwarded email from a loan officer"""
    forwarder_email: str
    forwarder_name: str
    original_sender_email: Optional[str]
    original_sender_name: Optional[str]
    original_subject: str
    original_body: str
    attachments: List[Dict]  # List of {filename, content_type, content}
    received_at: datetime
    client_id: Optional[int] = None


@dataclass
class ProcessingResult:
    """Result of processing a forwarded email"""
    success: bool
    application_data: Optional[Dict]
    sizer_result: Optional[Dict]
    generated_email: Optional[str]
    excel_file_path: Optional[str]
    error_message: Optional[str]
    processing_time_seconds: float


class EmailForwardProcessor:
    """Main processor for forwarded loan application emails"""
    
    # Common email forwarding patterns
    FORWARD_PATTERNS = [
        # Gmail format
        r'---------- Forwarded message ----------\s*\nFrom:\s*([^<\n]+)(?:<([^>]+)>)?\s*\nDate:\s*([^\n]+)\s*\nSubject:\s*([^\n]+)\s*\nTo:\s*([^\n]+)\s*\n\n(.*)',
        # Outlook format
        r'From:\s*([^<\n]+)(?:<([^>]+)>)?\s*\nSent:\s*([^\n]+)\s*\nTo:\s*([^\n]+)\s*\nSubject:\s*([^\n]+)\s*\n\n(.*)',
        # Apple Mail format
        r'Begin forwarded message:\s*\n\nFrom:\s*([^<\n]+)(?:<([^>]+)>)?\s*\nSubject:\s*([^\n]+)\s*\nDate:\s*([^\n]+)\s*\n\n(.*)',
        # Simple format
        r'--- Original Message ---\s*\nFrom:\s*([^<\n]+)(?:<([^>]+)>)?\s*\nSubject:\s*([^\n]+)\s*\n\n(.*)',
    ]
    
    def __init__(self, daily_rate: float = 8.50, template_path: str = None):
        self.daily_rate = daily_rate
        self.pdf_parser = PDFLoanParser()
        self.template_path = template_path
        self.sizer_processor = None
        
    def _get_sizer_processor(self, template_path: str = None):
        """Lazy load sizer processor with template"""
        if self.sizer_processor is None:
            path = template_path or self.template_path
            if path and Path(path).exists():
                self.sizer_processor = SizerProcessor(path)
        return self.sizer_processor
        
    def parse_forwarded_email(self, 
                             raw_email_content: str,
                             forwarder_email: str,
                             forwarder_name: str,
                             attachments: List[Dict] = None) -> ForwardedEmail:
        """
        Parse a forwarded email to extract original content
        Handles various email client forwarding formats
        """
        original_body = raw_email_content
        original_sender = None
        original_sender_name = None
        original_subject = ""
        
        # Try each pattern to extract forwarded content
        for pattern in self.FORWARD_PATTERNS:
            match = re.search(pattern, raw_email_content, re.DOTALL | re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 5:
                    # Extract based on pattern match
                    if 'Forwarded message' in raw_email_content:
                        # Gmail format
                        original_sender_name = groups[0].strip() if groups[0] else None
                        original_sender = groups[1].strip() if groups[1] else None
                        original_subject = groups[3].strip() if len(groups) > 3 else ""
                        original_body = groups[-1].strip()
                    elif 'Sent:' in raw_email_content:
                        # Outlook format
                        original_sender_name = groups[0].strip() if groups[0] else None
                        original_sender = groups[1].strip() if groups[1] else None
                        original_subject = groups[4].strip() if len(groups) > 4 else ""
                        original_body = groups[-1].strip()
                    else:
                        # Generic format
                        original_sender_name = groups[0].strip() if groups[0] else None
                        original_sender = groups[1].strip() if len(groups) > 1 else None
                        original_subject = groups[2].strip() if len(groups) > 2 else ""
                        original_body = groups[-1].strip()
                break
        
        # Clean up the body - remove signature blocks
        original_body = self._clean_email_body(original_body)
        
        # Extract applicant email from original body if not found in headers
        if not original_sender:
            original_sender = self._extract_email_from_text(original_body)
        
        return ForwardedEmail(
            forwarder_email=forwarder_email,
            forwarder_name=forwarder_name,
            original_sender_email=original_sender,
            original_sender_name=original_sender_name,
            original_subject=original_subject,
            original_body=original_body,
            attachments=attachments or [],
            received_at=datetime.now()
        )
    
    def _clean_email_body(self, body: str) -> str:
        """Remove signatures, disclaimers, and common email clutter"""
        # Remove common signature markers
        sig_patterns = [
            r'--\s*\n.*',  # Standard signature delimiter
            r'Best regards[\s\S]*',
            r'Regards[\s\S]*',
            r'Sincerely[\s\S]*',
            r'Thank you[\s\S]*',
            r'Cheers[\s\S]*',
            r'Disclaimer:[\s\S]*',
            r'CONFIDENTIALITY NOTICE[\s\S]*',
            r'\n\n\n+',  # Multiple newlines
        ]
        
        cleaned = body
        for pattern in sig_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _extract_email_from_text(self, text: str) -> Optional[str]:
        """Extract email address from text body"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, text)
        return matches[-1] if matches else None
    
    def extract_from_attachments(self, forwarded_email: ForwardedEmail) -> Optional[Dict]:
        """
        Extract loan application data from PDF attachments
        Returns extracted data or None if no valid attachment
        """
        for attachment in forwarded_email.attachments:
            content_type = attachment.get('content_type', '').lower()
            filename = attachment.get('filename', '').lower()
            
            # Process PDF files
            if 'pdf' in content_type or filename.endswith('.pdf'):
                try:
                    pdf_content = attachment.get('content')
                    if isinstance(pdf_content, str):
                        # Base64 encoded
                        pdf_content = base64.b64decode(pdf_content)
                    
                    # Save temporarily for parsing
                    temp_path = f"/tmp/{hashlib.md5(filename.encode()).hexdigest()}.pdf"
                    with open(temp_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    # Parse PDF
                    pdf_data = self.pdf_parser.parse_pdf(temp_path)
                    
                    # Clean up
                    os.remove(temp_path)
                    
                    return pdf_data
                    
                except Exception as e:
                    print(f"Error parsing PDF {filename}: {e}")
                    continue
            
            # Process Excel files (if it's a pre-filled sizer)
            if any(ext in filename for ext in ['.xlsx', '.xls', '.xlsm']):
                # Could extract existing data from Excel
                pass
        
        return None
    
    def process_forwarded_email(self, forwarded_email: ForwardedEmail) -> ProcessingResult:
        """
        Main processing pipeline:
        1. Extract from email body
        2. Extract from attachments (if any)
        3. Merge data sources
        4. Run sizer
        5. Generate response
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Extract from email body using AI/regex
            body_data = self._extract_from_email_body(forwarded_email.original_body)
            
            # Step 2: Extract from attachments
            attachment_data = self.extract_from_attachments(forwarded_email)
            
            # Step 3: Merge data (attachments take precedence over body)
            merged_data = self._merge_data_sources(body_data, attachment_data)
            
            if not merged_data:
                return ProcessingResult(
                    success=False,
                    application_data=None,
                    sizer_result=None,
                    generated_email=None,
                    excel_file_path=None,
                    error_message="Could not extract loan application data from email or attachments",
                    processing_time_seconds=time.time() - start_time
                )
            
            # Step 4: Create loan application object
            application = self._create_application(merged_data)
            
            # Step 5: Run sizer
            sizer = self._get_sizer_processor()
            if sizer is None:
                return ProcessingResult(
                    success=False,
                    application_data=merged_data,
                    sizer_result=None,
                    generated_email=None,
                    excel_file_path=None,
                    error_message="No Excel template configured. Please upload a template first.",
                    processing_time_seconds=time.time() - start_time
                )
            sizer_result = sizer.process_application(application, self.daily_rate)
            
            # Step 6: Generate filled Excel
            excel_path = self._generate_excel_output(application, sizer_result)
            
            # Step 7: Generate response email
            response_email = self._generate_response_email(
                forwarded_email=forwarded_email,
                application=application,
                sizer_result=sizer_result
            )
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                application_data=merged_data,
                sizer_result=sizer_result,
                generated_email=response_email,
                excel_file_path=excel_path,
                error_message=None,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(error_detail)  # Log for debugging
            return ProcessingResult(
                success=False,
                application_data=None,
                sizer_result=None,
                generated_email=None,
                excel_file_path=None,
                error_message=str(e),
                processing_time_seconds=time.time() - start_time
            )
    
    def _extract_from_email_body(self, body: str) -> Optional[Dict]:
        """Extract loan data from email body text"""
        # Use the same extraction logic from processor_custom
        try:
            from processor_custom import AIExtractor
            extractor = AIExtractor()
            return extractor.extract_application_data(body)
        except:
            # Fallback to regex extraction
            return self._regex_extract(body)
    
    def _regex_extract(self, text: str) -> Dict:
        """Fallback regex extraction"""
        extracted = {}
        
        # Property details
        patterns = {
            'units': r'(\d+)\s*(?:unit|door|plex)',
            'address': r'(?:at|located at|address[:\s]+)\s*([^,\n]+(?:,[^,\n]+)*)',
            'city': r'([^,]+),\s*(?:[A-Z]{2}|\w+)',
            'state': r'([A-Z]{2})',
            'zip': r'\b(\d{5}(?:-\d{4})?)\b',
            'estimated_value': r'(?:estimated value|value|worth)[:\s]*\$?([\d,]+)',
            'purchase_price': r'(?:purchase price|price)[:\s]*\$?([\d,]+)',
            'loan_amount': r'(?:loan amount|requested|financing)[:\s]*\$?([\d,]+)',
            'credit_score_1': r'(?:credit scores?|fico)[:\s]*(\d{3})',
            'credit_score_2': r'(?:credit scores?|fico)[:\s]*\d{3}[\s,]+(\d{3})',
            'credit_score_3': r'(?:credit scores?|fico)[:\s]*\d{3}[\s,]+\d{3}[\s,]+(\d{3})',
            'note_type': r'(\d+)\s*YR\s*(?:Fixed|Arm)',
            'points': r'(?:points?|fee)[:\s]*(\d+(?:\.\d+)?)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                if field.startswith('credit_score'):
                    extracted[field] = int(value)
                elif field in ['units']:
                    extracted[field] = int(value)
                elif field in ['points']:
                    extracted[field] = float(value)
                elif field in ['estimated_value', 'purchase_price', 'loan_amount']:
                    extracted[field] = float(value)
                else:
                    extracted[field] = value
        
        return extracted
    
    def _merge_data_sources(self, body_data: Optional[Dict], attachment_data: Optional[Dict]) -> Optional[Dict]:
        """Merge data from body and attachments, with attachments taking precedence"""
        if not body_data and not attachment_data:
            return None
        
        merged = {}
        if body_data:
            merged.update(body_data)
        if attachment_data:
            merged.update(attachment_data)  # Overwrite with attachment data
        
        return merged
    
    def _create_application(self, data: Dict) -> LoanApplication:
        """Create LoanApplication from extracted data"""
        return LoanApplication(
            units=data.get('units', 0),
            unit_size=data.get('unit_size', ''),
            address=data.get('address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            zip_code=data.get('zip_code', ''),
            estimated_value=data.get('estimated_value', 0),
            purchase_price=data.get('purchase_price', 0),
            loan_amount=data.get('loan_amount', 0),
            note_type=data.get('note_type', '30 YR Fixed'),
            points_to_lender=data.get('points_to_lender', data.get('points', 0)),
            credit_score_1=data.get('credit_score_1', 0),
            credit_score_2=data.get('credit_score_2', 0),
            credit_score_3=data.get('credit_score_3', 0),
            property_type=data.get('property_type', 'Multifamily'),
            asset_class=data.get('asset_class', 'C'),
            occupancy=data.get('occupancy', 1.0),
            rent_stabilized=data.get('rent_stabilized', 'No')
        )
    
    def _generate_excel_output(self, application: LoanApplication, sizer_result: Dict) -> str:
        """Generate filled Excel template with results"""
        # The sizer_result already contains the output file path from process_application
        if isinstance(sizer_result, dict):
            return sizer_result.get('output_file', '')
        # If sizer_result is a ProcessingResult object
        elif hasattr(sizer_result, 'output_file'):
            return sizer_result.output_file
        return ''
    
    def _generate_response_email(self, 
                                forwarded_email: ForwardedEmail,
                                application: LoanApplication,
                                sizer_result: Dict) -> str:
        """Generate HTML email response with highlighted results and detailed feedback"""
        
        overall_decision = sizer_result.get('overall_decision', 'PENDING')
        decision_color = '#10b981' if overall_decision == 'APPROVE' else '#ef4444'
        decision_bg = '#d1fae5' if overall_decision == 'APPROVE' else '#fee2e2'
        decision_icon = '✓' if overall_decision == 'APPROVE' else '✗'
        
        # Build programs table
        programs_html = ""
        for prog in sizer_result.get('programs', []):
            status_color = '#10b981' if prog['status'] == 'PASS' else '#ef4444'
            status_icon = '✓' if prog['status'] == 'PASS' else '✗'
            programs_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{prog['program_name']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; color: {status_color}; font-weight: bold;">
                    {status_icon} {prog['status']}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${prog.get('max_loan_amount', 0):,.0f}</td>
            </tr>
            """
        
        # Generate failure reasons if declined
        failure_reasons_html = ""
        if overall_decision == 'DECLINE':
            failure_reasons = self._extract_failure_reasons(sizer_result)
            if failure_reasons:
                reasons_list = "".join([f"<li style='margin-bottom: 8px;'>{reason}</li>" for reason in failure_reasons])
                failure_reasons_html = f"""
                <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <h3 style="margin-top: 0; color: #dc2626;">Why This Application Did Not Pass</h3>
                    <ul style="color: #7f1d1d; margin: 0; padding-left: 20px;">
                        {reasons_list}
                    </ul>
                    <p style="margin: 15px 0 0 0; color: #991b1b; font-size: 14px;">
                        <strong>Recommendation:</strong> Consider adjusting loan terms or exploring alternative programs.
                    </p>
                </div>
                """
        
        # Calculate LTV safely
        try:
            ltv = (application.loan_amount / application.estimated_value * 100) if application.estimated_value > 0 else 0
        except:
            ltv = 0
        
        email_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #374151; background: #f3f4f6; margin: 0; padding: 20px; }}
                .container {{ max-width: 650px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); padding: 30px; color: white; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; font-size: 14px; }}
                .content {{ padding: 30px; }}
                .decision-box {{ 
                    background: {decision_bg}; 
                    border: 3px solid {decision_color}; 
                    padding: 30px; 
                    border-radius: 12px; 
                    text-align: center;
                    margin: 0 0 25px 0;
                }}
                .decision-icon {{ 
                    font-size: 48px; 
                    color: {decision_color}; 
                    margin-bottom: 10px;
                }}
                .decision-text {{ 
                    color: {decision_color}; 
                    font-size: 32px; 
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }}
                .decision-subtext {{ 
                    color: #4b5563; 
                    font-size: 16px; 
                    margin-top: 10px;
                }}
                .details {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 25px 0; border: 1px solid #e5e7eb; }}
                .details h3 {{ margin-top: 0; color: #111827; font-size: 18px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }}
                .detail-row:last-child {{ border-bottom: none; }}
                .detail-label {{ font-weight: 600; color: #6b7280; }}
                .detail-value {{ color: #111827; font-weight: 500; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                th {{ background: #1e3a5f; color: white; padding: 12px; text-align: left; font-weight: 600; }}
                td {{ padding: 12px 8px; }}
                tr:nth-child(even) {{ background: #f9fafb; }}
                .footer {{ background: #f3f4f6; padding: 20px 30px; text-align: center; color: #6b7280; font-size: 13px; border-top: 1px solid #e5e7eb; }}
                .attachment-note {{ background: #ecfdf5; border: 2px dashed #10b981; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; color: #065f46; }}
                .pass {{ color: #10b981; }}
                .fail {{ color: #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏠 Loan Application Complete</h1>
                    <p>ComplAiCore Automated Analysis</p>
                </div>
                
                <div class="content">
                    <div class="decision-box">
                        <div class="decision-icon">{decision_icon}</div>
                        <div class="decision-text">{overall_decision}</div>
                        <div class="decision-subtext">
                            {sizer_result.get('decision_reason', 'Application has been analyzed')}
                        </div>
                    </div>
                    
                    {failure_reasons_html}
                    
                    <div class="details">
                        <h3>📋 Property Details</h3>
                        <div class="detail-row">
                            <span class="detail-label">Address</span>
                            <span class="detail-value">{application.address}, {application.city}, {application.state} {application.zip_code}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Units</span>
                            <span class="detail-value">{application.units}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Loan Amount</span>
                            <span class="detail-value">${application.loan_amount:,.0f}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Estimated Value</span>
                            <span class="detail-value">${application.estimated_value:,.0f}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">LTV Ratio</span>
                            <span class="detail-value">{ltv:.1f}%</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Credit Score (Middle)</span>
                            <span class="detail-value">{application.credit_score_middle}</span>
                        </div>
                    </div>
                    
                    <h3 style="color: #1e3a5f; margin-top: 30px;">📊 Program Results</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Program</th>
                                <th>Status</th>
                                <th style="text-align: right;">Max Loan Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {programs_html}
                        </tbody>
                    </table>
                    
                    <div class="attachment-note">
                        <strong>📎 Complete Analysis Attached</strong><br>
                        Download the Excel file below for full underwriting details
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>ComplAiCore Loan Sizer AI</strong></p>
                    <p>This analysis was generated automatically on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                    <p>Processing time: {sizer_result.get('processing_time', 'N/A')} seconds</p>
                    <p style="margin-top: 15px; font-size: 11px; color: #9ca3af;">
                        This is an automated analysis. Please verify all figures before proceeding.<br>
                        © 2026 ComplAiCore. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return email_html
    
    def _extract_failure_reasons(self, sizer_result: Dict) -> List[str]:
        """Extract specific reasons why the application failed"""
        reasons = []
        
        programs = sizer_result.get('programs', [])
        
        for prog in programs:
            if prog['status'] == 'FAIL':
                # Extract specific failure reasons from each program
                fails = prog.get('fails', [])
                for fail in fails:
                    if isinstance(fail, dict):
                        rule = fail.get('rule', 'Unknown rule')
                        actual = fail.get('actual', 'N/A')
                        required = fail.get('required', 'N/A')
                        reasons.append(f"{prog['program_name']}: {rule} (Got: {actual}, Required: {required})")
                    elif isinstance(fail, str):
                        reasons.append(f"{prog['program_name']}: {fail}")
        
        # Check for common issues if no specific reasons found
        if not reasons:
            credit_score = sizer_result.get('credit_score_middle', 0)
            if credit_score < 620:
                reasons.append(f"Credit score ({credit_score}) below minimum threshold (620)")
            
            ltv = sizer_result.get('ltv', 0)
            if ltv > 80:
                reasons.append(f"LTV ratio ({ltv:.1f}%) exceeds maximum (80%)")
            
            dscr = sizer_result.get('dscr', 0)
            if dscr < 1.0:
                reasons.append(f"DSCR ({dscr:.2f}) below minimum requirement (1.0)")
        
        return reasons if reasons else ["Application does not meet program requirements"]
    
    def create_email_with_attachment(self,
                                    to_email: str,
                                    to_name: str,
                                    subject: str,
                                    html_body: str,
                                    attachment_path: str,
                                    attachment_filename: str) -> Dict:
        """Create email message with Excel attachment"""
        
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = 'ComplAiCore Loan Sizer <pn@complaicore.com>'
        msg['To'] = f"{to_name} <{to_email}>"
        
        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach Excel file
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                excel_data = f.read()
            
            excel_attachment = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            excel_attachment.set_payload(excel_data)
            encoders.encode_base64(excel_attachment)
            excel_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment_filename}"'
            )
            msg.attach(excel_attachment)
        
        return {
            'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode(),
            'to': to_email,
            'subject': subject
        }


# Reuse LoanApplication from processor_custom