"""
PDF Parser for Loan Applications
Extracts text and data from PDF loan application documents
"""

import re
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Try to import PDF libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available. PDF parsing will be limited.")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available. PDF parsing will be limited.")


@dataclass
class PDFExtractionResult:
    """Result of PDF extraction"""
    success: bool
    text: str
    fields: Dict[str, any]
    tables: List[List[List[str]]]
    confidence: float
    missing_fields: List[str]
    error_message: Optional[str] = None


class PDFLoanParser:
    """Parser for loan application PDFs"""
    
    def __init__(self):
        self.patterns = {
            'units': [
                r'(\d+)\s*(?:unit|units|doors?)',
                r'number\s+of\s+units?[:\s]+(\d+)',
                r'total\s+units?[:\s]+(\d+)',
            ],
            'address': [
                r'(?:property\s+)?address[:\s]+([^\n,]+(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|lane|ln)[^\n,]*)',
                r'location[:\s]+([^\n,]+(?:street|st|avenue|ave)[^\n,]*)',
            ],
            'city': [
                r'city[:\s]+([a-zA-Z\s]+?)(?:,|\n|$)',
                r'[^,]+,\s*([a-zA-Z\s]+?),\s*[A-Za-z]{2}\s*\d{5}',
            ],
            'state': [
                r',\s*([A-Z]{2})\s*\d{5}',
                r'state[:\s]+([A-Z]{2})',
            ],
            'zip': [
                r'\b(\d{5}(?:-\d{4})?)\b',
                r'zip[:\s]+(\d{5})',
            ],
            'estimated_value': [
                r'(?:est(?:imated)?\s+)?(?:value|appraised\s+value)[:\s]+\$?([\d,\.]+)',
                r'property\s+value[:\s]+\$?([\d,\.]+)',
            ],
            'purchase_price': [
                r'(?:purchase\s+price|purchase\s+amount|acquisition\s+price)[:\s]+\$?([\d,\.]+)',
            ],
            'loan_amount': [
                r'(?:loan\s+amount|requested\s+loan|financing\s+amount)[:\s]+\$?([\d,\.]+)',
            ],
            'note_type': [
                r'(30|15|20|10)\s*(?:year|yr)?\s*(?:fixed|arm|variable)',
                r'loan\s+type[:\s]+(30\s*year\s*fixed|15\s*year\s*fixed|ARM)',
            ],
            'points': [
                r'(?:points|origination)[:\s]+(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*(?:point|pts)',
            ],
            'credit_scores': [
                r'(?:credit\s+score|fico)[s:]?\s*(\d{3})[\s,]+(\d{3})[\s,]+(\d{3})',
                r'(?:experian|exp)[:\s]*(\d{3}).{0,50}(?:transunion|trans)[:\s]*(\d{3}).{0,50}(?:equifax|eq)[:\s]*(\d{3})',
            ],
            'applicant_name': [
                r'(?:borrower|applicant|name)[:\s]+([A-Za-z\s\.]+?)(?:\n|email|$)',
                r'submitted\s+by[:\s]+([A-Za-z\s\.]+)',
            ],
            'applicant_email': [
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            ],
            'property_type': [
                r'property\s+type[:\s]+(multifamily|commercial|mixed-use|retail|office|industrial)',
                r'(multifamily|mixed-use)\s+property',
            ],
        }
    
    def parse_pdf(self, pdf_bytes: bytes) -> PDFExtractionResult:
        """
        Parse a PDF file and extract loan application data
        
        Args:
            pdf_bytes: Raw PDF file bytes
            
        Returns:
            PDFExtractionResult with extracted data
        """
        try:
            # Extract text from PDF
            text, tables = self._extract_text_and_tables(pdf_bytes)
            
            if not text:
                return PDFExtractionResult(
                    success=False,
                    text="",
                    fields={},
                    tables=[],
                    confidence=0.0,
                    missing_fields=[],
                    error_message="Could not extract text from PDF"
                )
            
            # Extract fields using regex patterns
            fields = self._extract_fields(text)
            
            # Also try to extract from tables
            table_fields = self._extract_from_tables(tables)
            fields.update(table_fields)
            
            # Calculate confidence
            required_fields = ['units', 'address', 'city', 'state', 'zip', 
                             'estimated_value', 'loan_amount', 'credit_scores']
            found_fields = [f for f in required_fields if f in fields and fields[f]]
            confidence = len(found_fields) / len(required_fields)
            
            missing = [f for f in required_fields if f not in fields or not fields[f]]
            
            # Process credit scores
            if 'credit_scores' in fields:
                scores = fields['credit_scores']
                if isinstance(scores, tuple) and len(scores) == 3:
                    fields['credit_score_1'] = int(scores[0])
                    fields['credit_score_2'] = int(scores[1])
                    fields['credit_score_3'] = int(scores[2])
                    del fields['credit_scores']
            
            return PDFExtractionResult(
                success=True,
                text=text[:5000],  # Limit text length
                fields=fields,
                tables=tables,
                confidence=confidence,
                missing_fields=missing
            )
            
        except Exception as e:
            logger.error(f"PDF parsing error: {str(e)}")
            return PDFExtractionResult(
                success=False,
                text="",
                fields={},
                tables=[],
                confidence=0.0,
                missing_fields=[],
                error_message=str(e)
            )
    
    def _extract_text_and_tables(self, pdf_bytes: bytes) -> Tuple[str, List]:
        """Extract text and tables from PDF"""
        text = ""
        tables = []
        
        # Try pdfplumber first (better table extraction)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                        
                        # Extract tables
                        page_tables = page.extract_tables()
                        tables.extend(page_tables)
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Fallback to PyPDF2
        if not text and PYPDF2_AVAILABLE:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e:
                logger.warning(f"PyPDF2 extraction failed: {e}")
        
        return text, tables
    
    def _extract_fields(self, text: str) -> Dict[str, any]:
        """Extract fields using regex patterns"""
        fields = {}
        text_lower = text.lower()
        
        for field_name, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    value = match.group(1) if match.lastindex else match.group(0)
                    value = value.strip()
                    
                    # Clean and convert values
                    if field_name in ['units']:
                        try:
                            fields[field_name] = int(value.replace(',', ''))
                        except:
                            continue
                    elif field_name in ['estimated_value', 'purchase_price', 'loan_amount', 'points']:
                        try:
                            # Remove $ and commas
                            clean_val = value.replace('$', '').replace(',', '')
                            # Handle 'k' suffix (thousands)
                            if 'k' in clean_val.lower():
                                clean_val = float(clean_val.lower().replace('k', '')) * 1000
                            fields[field_name] = float(clean_val)
                        except:
                            continue
                    elif field_name == 'credit_scores':
                        if match.lastindex and match.lastindex >= 3:
                            fields[field_name] = (match.group(1), match.group(2), match.group(3))
                    elif field_name == 'note_type':
                        # Format note type
                        value = value.replace(' ', '').upper()
                        if '30' in value:
                            fields[field_name] = "30 YR Fixed"
                        elif '15' in value:
                            fields[field_name] = "15 YR Fixed"
                        else:
                            fields[field_name] = value
                    else:
                        fields[field_name] = value
                    
                    break  # Found match for this field
        
        return fields
    
    def _extract_from_tables(self, tables: List) -> Dict[str, any]:
        """Try to extract data from tables"""
        fields = {}
        
        for table in tables:
            if not table:
                continue
            
            for row in table:
                if not row or len(row) < 2:
                    continue
                
                # Check first column for field names
                key = str(row[0]).lower().strip() if row[0] else ""
                value = str(row[1]).strip() if row[1] else ""
                
                if 'unit' in key and value.isdigit():
                    fields['units'] = int(value)
                elif 'address' in key:
                    fields['address'] = value
                elif 'city' in key:
                    fields['city'] = value
                elif 'state' in key:
                    fields['state'] = value
                elif 'zip' in key:
                    fields['zip'] = value
                elif 'value' in key or 'price' in key:
                    try:
                        fields['estimated_value'] = float(value.replace('$', '').replace(',', ''))
                    except:
                        pass
                elif 'loan' in key and 'amount' in key:
                    try:
                        fields['loan_amount'] = float(value.replace('$', '').replace(',', ''))
                    except:
                        pass
        
        return fields


# Factory function
def get_pdf_parser() -> PDFLoanParser:
    """Get PDF parser instance"""
    return PDFLoanParser()


# Example usage
if __name__ == "__main__":
    # Test with sample PDF
    parser = PDFLoanParser()
    
    # You would read a real PDF file here
    # with open("sample.pdf", "rb") as f:
    #     result = parser.parse_pdf(f.read())
    #     print(result)
    
    print("PDF Parser ready. Use parse_pdf() method with PDF bytes.")
