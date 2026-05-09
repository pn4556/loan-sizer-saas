"""
Universal File Parser for Loan Sizer
Handles PDF, CSV, Excel, TXT, and Images with OCR fallback
"""

import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import pytesseract
from PIL import Image
import io
import re
from typing import Dict, Any, Union, List
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of file parsing"""
    success: bool
    file_type: str
    text: str
    structured_data: Dict[str, Any]
    confidence: float
    error_message: str = None
    ocr_used: bool = False


class UniversalFileParser:
    """Handles all file types for loan application processing"""
    
    def __init__(self):
        self.supported_types = ['pdf', 'csv', 'excel', 'text', 'image']
        
    def detect_file_type(self, content: bytes, filename: str) -> str:
        """Detect file type from content and filename"""
        filename_lower = filename.lower()
        
        # Check by extension
        if filename_lower.endswith('.pdf'):
            return 'pdf'
        elif filename_lower.endswith('.csv'):
            return 'csv'
        elif filename_lower.endswith(('.xlsx', '.xls')):
            return 'excel'
        elif filename_lower.endswith(('.txt', '.text', '.md')):
            return 'text'
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif')):
            return 'image'
        
        # Check by content (magic numbers)
        if content[:4] == b'%PDF':
            return 'pdf'
        elif content[:2] == b'PK':
            return 'excel'
        
        return 'text'
    
    async def parse(self, content: bytes, filename: str) -> ParseResult:
        """Parse any supported file type"""
        try:
            file_type = self.detect_file_type(content, filename)
            logger.info(f"Parsing {file_type} file: {filename}")
            
            if file_type == 'pdf':
                return await self._parse_pdf(content)
            elif file_type == 'csv':
                return await self._parse_csv(content)
            elif file_type == 'excel':
                return await self._parse_excel(content)
            elif file_type == 'text':
                return await self._parse_text(content)
            elif file_type == 'image':
                return await self._parse_image(content)
            else:
                return ParseResult(
                    success=False,
                    file_type='unknown',
                    text='',
                    structured_data={},
                    confidence=0.0,
                    error_message=f'Unsupported file type: {file_type}'
                )
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return ParseResult(
                success=False,
                file_type='error',
                text='',
                structured_data={},
                confidence=0.0,
                error_message=str(e)
            )
    
    async def _parse_pdf(self, content: bytes) -> ParseResult:
        """Parse PDF with text extraction + OCR fallback"""
        text = ''
        ocr_used = False
        confidence = 0.0
        
        try:
            # Method 1: Native text extraction with PyMuPDF
            with fitz.open(stream=content, filetype="pdf") as doc:
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                text = '\n'.join(text_parts)
                
                # Check if we got meaningful text
                if len(text.strip()) > 100:
                    confidence = 0.85
                else:
                    # Low text confidence - try OCR
                    logger.info("Low text confidence, attempting OCR...")
                    text = await self._extract_pdf_with_ocr(content)
                    ocr_used = True
                    confidence = 0.75 if text else 0.0
            
            # Extract structured loan data
            structured = self._extract_loan_data(text)
            
            return ParseResult(
                success=True,
                file_type='pdf',
                text=text,
                structured_data=structured,
                confidence=confidence,
                ocr_used=ocr_used
            )
            
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            return ParseResult(
                success=False,
                file_type='pdf',
                text='',
                structured_data={},
                confidence=0.0,
                error_message=f'PDF parse error: {str(e)}'
            )
    
    async def _extract_pdf_with_ocr(self, content: bytes) -> str:
        """Extract text from scanned PDF using OCR"""
        try:
            text_parts = []
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    # Render at 2x for better OCR
                    mat = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    
                    # OCR
                    img = Image.open(io.BytesIO(img_data))
                    text = pytesseract.image_to_string(img)
                    text_parts.append(text)
            
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""
    
    async def _parse_csv(self, content: bytes) -> ParseResult:
        """Parse CSV files"""
        try:
            df = pd.read_csv(io.BytesIO(content))
            text = df.to_string()
            structured = self._extract_loan_data(text)
            # Also include raw data
            structured['csv_data'] = df.to_dict('records')
            
            return ParseResult(
                success=True,
                file_type='csv',
                text=text,
                structured_data=structured,
                confidence=0.95
            )
        except Exception as e:
            return ParseResult(
                success=False,
                file_type='csv',
                text='',
                structured_data={},
                confidence=0.0,
                error_message=f'CSV parse error: {str(e)}'
            )
    
    async def _parse_excel(self, content: bytes) -> ParseResult:
        """Parse Excel files"""
        try:
            excel_file = pd.ExcelFile(io.BytesIO(content))
            sheets_data = {}
            full_text = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheets_data[sheet_name] = df.to_dict('records')
                full_text.append(f"Sheet: {sheet_name}\n{df.to_string()}")
            
            text = '\n\n'.join(full_text)
            structured = self._extract_loan_data(text)
            structured['excel_sheets'] = sheets_data
            
            return ParseResult(
                success=True,
                file_type='excel',
                text=text,
                structured_data=structured,
                confidence=0.95
            )
        except Exception as e:
            return ParseResult(
                success=False,
                file_type='excel',
                text='',
                structured_data={},
                confidence=0.0,
                error_message=f'Excel parse error: {str(e)}'
            )
    
    async def _parse_text(self, content: bytes) -> ParseResult:
        """Parse plain text files"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                text = content.decode(encoding)
                structured = self._extract_loan_data(text)
                
                return ParseResult(
                    success=True,
                    file_type='text',
                    text=text,
                    structured_data=structured,
                    confidence=0.95
                )
            except UnicodeDecodeError:
                continue
        
        return ParseResult(
            success=False,
            file_type='text',
            text='',
            structured_data={},
            confidence=0.0,
            error_message='Unable to decode text file'
        )
    
    async def _parse_image(self, content: bytes) -> ParseResult:
        """Parse images using OCR"""
        try:
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img)
            structured = self._extract_loan_data(text)
            
            return ParseResult(
                success=True,
                file_type='image',
                text=text,
                structured_data=structured,
                confidence=0.8 if text else 0.0,
                ocr_used=True
            )
        except Exception as e:
            return ParseResult(
                success=False,
                file_type='image',
                text='',
                structured_data={},
                confidence=0.0,
                error_message=f'Image parse error: {str(e)}'
            )
    
    def _extract_loan_data(self, text: str) -> Dict[str, Any]:
        """Extract structured loan data from text using regex"""
        data = {
            'borrower_name': None,
            'loan_amount': None,
            'property_value': None,
            'purchase_price': None,
            'interest_rate': None,
            'loan_term': None,
            'property_address': None,
            'city': None,
            'state': None,
            'zip': None,
            'credit_score': None,
            'income': None,
            'property_type': None,
            'units': None,
            'ltv': None,
        }
        
        # Comprehensive regex patterns
        patterns = {
            'loan_amount': [
                r'(?:loan amount|requested loan|financing)[\s:]*\$?([\d,]+(?:\.\d{2})?)',
                r'loan[\s:]*\$?([\d,]+(?:\.\d{2})?)',
            ],
            'property_value': [
                r'(?:property value|estimated value|appraised value)[\s:]*\$?([\d,]+(?:\.\d{2})?)',
                r'value[\s:]*\$?([\d,]+(?:\.\d{2})?)',
            ],
            'purchase_price': [
                r'(?:purchase price|acquisition price)[\s:]*\$?([\d,]+(?:\.\d{2})?)',
            ],
            'interest_rate': [
                r'(?:rate|interest)[\s:]*(\d+\.?\d*)\s*%',
                r'(\d+\.?\d*)\s*percent',
            ],
            'loan_term': [
                r'(\d+)\s*(?:year|yr)[\s\-]*(?:fixed|mortgage)?',
                r'term[\s:]*(\d+)\s*years?',
            ],
            'credit_score': [
                r'(?:credit score|fico)[\s:]*(\d{3})',
                r'score[\s:]*(\d{3})',
            ],
            'property_address': [
                r'(?:property address|address)[\s:]*([^\n,]+(?:street|st|ave|road|dr)[^\n]*)',
            ],
            'city': [
                r'city[\s:]*([^\n,]+)',
            ],
            'state': [
                r'state[\s:]*([A-Z]{2})',
                r',\s*([A-Z]{2})\s*\d{5}',
            ],
            'zip': [
                r'(\d{5}(?:-\d{4})?)',
                r'zip[\s:]*(\d{5})',
            ],
            'units': [
                r'(\d+)\s*(?:unit|units)',
                r'units[\s:]*(\d+)',
            ],
            'property_type': [
                r'(single family|multifamily|commercial|mixed.use|condo|townhouse)',
            ],
            'borrower_name': [
                r'(?:borrower|applicant|name)[\s:]*([A-Za-z\s\.]+?)(?:\n|email|$)',
            ],
        }
        
        text_lower = text.lower()
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    value = matches[0]
                    if isinstance(value, str):
                        # Clean numeric values
                        if field in ['loan_amount', 'property_value', 'purchase_price']:
                            value = float(value.replace(',', '').replace('$', ''))
                        elif field in ['interest_rate', 'ltv']:
                            value = float(value)
                        elif field in ['credit_score', 'loan_term', 'units']:
                            value = int(float(value))
                    data[field] = value
                    break
        
        # Calculate LTV if possible
        if data['loan_amount'] and data['property_value']:
            try:
                data['ltv'] = (data['loan_amount'] / data['property_value']) * 100
            except:
                pass
        
        # Count extracted fields
        extracted_count = sum(1 for v in data.values() if v is not None)
        data['extraction_confidence'] = extracted_count / len(data)
        
        return data


# Singleton instance
_parser = None

def get_parser() -> UniversalFileParser:
    """Get or create parser instance"""
    global _parser
    if _parser is None:
        _parser = UniversalFileParser()
    return _parser
