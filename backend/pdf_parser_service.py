"""
Production-Grade PDF Parsing Service for Loan Applications
Handles text PDFs, scanned images, and mixed content with OCR fallback
"""

import os
import re
import json
import uuid
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import tempfile
import hashlib

# PDF processing
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FieldExtraction:
    """Result of extracting a single field"""
    value: Any
    raw_text: str
    confidence: float
    pattern_used: str


@dataclass
class ParsedLoanApplication:
    """Complete parsed loan application"""
    job_id: str
    status: str
    filename: str
    pdf_type: str  # 'text', 'ocr', 'mixed'
    ocr_used: bool
    text_length: int
    fields: Dict[str, FieldExtraction]
    lender_detected: Optional[str]
    parsing_time_ms: int
    errors: List[str]
    raw_text_preview: str


# Lender-specific templates
LENDER_TEMPLATES = {
    "jotform": {
        "patterns": {
            "purchase_price": [
                r'Purchase Price[:\s]+\$?([\d,]+)',
                r'Purchase Price[:\s]*\n+\$?(\d[\d,]*)',
                r'Purchase Price.*?\n+.*?(\d{5,})',
                r'Purchase Price[:\s]*\n+Yes\s+\w+[\s\w]*\n+(\d{5,})',
            ],
            "as_is_value": [
                r'As-Is Property Value[:\s]+\$?([\d,]+)',
                r'As-Is Value[:\s]+\$?([\d,]+)',
                r'As-Is Property Value[:\s]*\n+\$?(\d[\d,]*)',
                r'Current Value[:\s]+\$?([\d,]+)',
                r'Yes\s+\w+[\s\w]*\n+(\d{5,})\n+(\d{5,})\n+(\d{4,})',
            ],
            "arv": [
                r'After Repair Property Value[:\s]+\$?([\d,]+)',
                r'ARV[:\s]+\$?([\d,]+)',
                r'After Repair Property Value[:\s]*\n+\$?(\d[\d,]*)',
                r'After Renovation Value[:\s]+\$?([\d,]+)',
            ],
            "rehab_budget": [
                r'Rehab Amount Requested[:\s]+\$?([\d,]+)',
                r'Rehab Budget[:\s]+\$?([\d,]+)',
                r'Rehab Amount Requested[:\s]*\n+\$?(\d[\d,]*)',
                r'Renovation Budget[:\s]+\$?([\d,]+)',
            ],
            "property_type": [
                r'Property Type[:\s]+([A-Za-z\-]+(?:\s+[A-Za-z]+)?)',
                r'Property Type[:\s]*\n+(Yes\s+)?([A-Za-z\-]+(?:\s+[A-Za-z]+)?)',
            ],
            "experience": [
                r'(\d+)\s+sold',
                r'(\d+)\s+deals',
                r'(\d+)\s+flips',
                r'Experience[:\s]+(\d+)',
                r'# of homes.*?\n+(\d+)\s+sold',
                r'flipped/exited.*?\n+(\d+)\s+sold',
            ],
            "property_address": [
                r'Subject Property Address[:\s]+(.+?)(?:\n|City:)',
                r'Property Address[:\s]+(.+?)(?:\n|City:)',
                r'Subject Property Address[:\s]*\n+([\w\s\d]+?)(?:\n|City:)',
            ],
            "city": [
                r'City[:\s]+([A-Za-z\s]+?)(?:\s+State|,)',
                r'City[:\s]*\n+([A-Za-z\s]+?)(?:\s+State|State|Zip)',
            ],
            "state": [
                r'State[:\s]+([A-Z]{2})',
                r'State[:\s]*\n+([A-Z]{2})',
            ],
            "zip_code": [
                r'Zip Code[:\s]+(\d{5}(?:-\d{4})?)',
                r'Zip[:\s]+(\d{5})',
                r'Zip Code[:\s]*\n+(\d{5})',
            ],
            "fico": [
                r'FICO[:\s]+(\d{3})',
                r'Credit Score[:\s]+(\d{3})',
            ],
        }
    },
    "bridge_capital": {
        "patterns": {
            "purchase_price": [
                r'Purchase Price[:\s$]+([\d,]+)',
            ],
            "loan_amount": [                r'Loan Amount[:\s$]+([\d,]+)',                r'Requested Loan[:\s$]+([\d,]+)',
            ],
        }
    },
    "generic": {
        "patterns": {
            "purchase_price": [
                r'Purchase\s+(?:Price|Amount)[:\s$]+([\d,]+)',
                r'Contract\s+Price[:\s$]+([\d,]+)',
                r'Sales\s+Price[:\s$]+([\d,]+)',
            ],
            "loan_amount": [
                r'Loan\s+(?:Amount|Amt)[:\s$]+([\d,]+)',
                r'Requested\s+(?:Loan|Amount)[:\s$]+([\d,]+)',
            ],
            "as_is_value": [
                r'As-?Is\s+(?:Value|Property\s+Value)[:\s$]+([\d,]+)',
                r'Current\s+Value[:\s$]+([\d,]+)',
                r'Present\s+Value[:\s$]+([\d,]+)',
            ],
            "arv": [
                r'ARV[:\s$]+([\d,]+)',
                r'After\s+Repair\s+(?:Value|Price)[:\s$]+([\d,]+)',
                r'After\s+Renovation\s+Value[:\s$]+([\d,]+)',
            ],
            "rehab_budget": [
                r'(?:Rehab|Renovation|Construction)\s+(?:Budget|Amount|Cost)[:\s$]+([\d,]+)',
            ],
            "property_type": [
                r'Property\s+Type[:\s]+(Single\s+Family|Multi[-\s]?Family|Condo|Townhouse|Commercial)',
                r'(Single\s+Family|Multi[-\s]?Family)\s+(?:Home|Property)',
            ],
            "fico": [
                r'FICO[:\s]+(\d{3})',
                r'Credit\s+Score[:\s]+(\d{3})',
                r'(?:Middle|Mid)\s+FICO[:\s]+(\d{3})',
            ],
            "experience": [
                r'(\d+)\s+(?:years?|yrs?)\s+experience',
                r'Experience[:\s]+(\d+)',
                r'(\d+)\s+deals?\s+(?:closed|completed)',
            ],
            "property_address": [
                r'(?:Subject\s+)?Property\s+Address[:\s]+(.+?)(?:\n|,)',
                r'Property\s+Location[:\s]+(.+?)(?:\n|,)',
            ],
            "city": [
                r'City[:\s]+([A-Za-z\s]+?)(?:,|\n|$)',
            ],
            "state": [
                r'State[:\s]+([A-Z]{2})',
                r',\s*([A-Z]{2})\s+\d{5}',
            ],
            "zip_code": [
                r'Zip(?:\s+Code)?[:\s]+(\d{5}(?:-\d{4})?)',
                r'([A-Z]{2})\s+(\d{5}(?:-\d{4})?)',
            ],
        }
    }
}


def normalize_text(text: str) -> str:
    """Normalize extracted text for better regex matching"""
    # Replace newlines with spaces
    text = text.replace('\n', ' ')
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Replace em-dashes and special dashes
    text = text.replace('—', '-').replace('–', '-')
    # Remove zero-width characters
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    # Normalize currency symbols
    text = text.replace('$', ' $ ')
    # Collapse spaces again
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def detect_pdf_type(doc: fitz.Document) -> str:
    """Detect if PDF is text-based, image-based, or mixed"""
    text_chars = 0
    image_pages = 0
    
    for page in doc:
        text = page.get_text()
        text_chars += len(text.strip())
        
        # Check for images
        images = page.get_images()
        if images:
            image_pages += 1
    
    avg_text_per_page = text_chars / len(doc) if len(doc) > 0 else 0
    
    if avg_text_per_page < 100:
        return 'image'
    elif image_pages > 0:
        return 'mixed'
    else:
        return 'text'


def needs_ocr(text: str) -> bool:
    """Determine if extracted text requires OCR processing"""
    if len(text.strip()) < 500:
        return True
    
    # Calculate alphabetic ratio
    alpha_count = sum(c.isalpha() for c in text)
    alpha_ratio = alpha_count / max(len(text), 1)
    
    if alpha_ratio < 0.3:
        return True
    
    # Check for excessive garbage characters
    garbage_chars = sum(1 for c in text if ord(c) > 127 and not c.isalnum())
    garbage_ratio = garbage_chars / max(len(text), 1)
    
    if garbage_ratio > 0.1:
        return True
    
    return False


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR results"""
    # Convert to numpy array
    img_array = np.array(image)
    
    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Adaptive thresholding
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Convert back to PIL Image
    return Image.fromarray(binary)


def extract_with_ocr(pdf_path: str) -> str:
    """Extract text from PDF using OCR"""
    logger.info(f"Running OCR on {pdf_path}")
    
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        
        ocr_text = ""
        for i, image in enumerate(images):
            logger.info(f"Processing page {i+1} with OCR")
            
            # Preprocess image
            processed = preprocess_image_for_ocr(image)
            
            # Run OCR
            page_text = pytesseract.image_to_string(
                processed,
                config='--psm 6'  # Assume single uniform block of text
            )
            
            ocr_text += page_text + "\n"
        
        return ocr_text
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def detect_lender(text: str) -> Optional[str]:
    """Detect which lender/form type based on text content"""
    text_lower = text.lower()
    
    lender_keywords = {
        "jotform": ["jotform", "bridge loan application", "loan details"],
        "bridge_capital": ["bridge capital", "bcp"],
        "eastview": ["eastview"],
        "loan_estimate": ["loan estimate", "closing disclosure"],
        "rocket_mortgage": ["rocket mortgage", "quicken loans"],
        "uwm": ["uwm", "united wholesale mortgage"],
    }
    
    for lender, keywords in lender_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return lender
    
    return None


def extract_field(text: str, field_name: str, patterns: List[str]) -> FieldExtraction:
    """Extract a single field using multiple regex patterns"""
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Get the first match
            match = matches[0]
            
            # Handle tuple matches (groups)
            if isinstance(match, tuple):
                match = match[0] if match[0] else match[1] if len(match) > 1 else match[0]
            
            # Clean the value
            clean_value = match.strip()
            
            # Remove currency formatting for numeric fields
            if field_name in ['purchase_price', 'loan_amount', 'as_is_value', 'arv', 'rehab_budget']:
                clean_value = clean_value.replace(',', '').replace('$', '')
                try:
                    clean_value = float(clean_value)
                except:
                    pass
            
            # Calculate confidence based on match quality
            confidence = 0.9  # High confidence for exact regex match
            # Check value length (handle both string and numeric values)
            value_str = str(clean_value)
            if len(value_str) < 2:
                confidence = 0.5
            
            return FieldExtraction(
                value=clean_value,
                raw_text=match,
                confidence=confidence,
                pattern_used=pattern
            )
    
    return FieldExtraction(
        value=None,
        raw_text="",
        confidence=0.0,
        pattern_used=""
    )


def parse_jotform_lines(text: str) -> Dict[str, FieldExtraction]:
    """
    Parse JotForm Bridge Loan Application with two-column layout.
    Handles the specific structure where labels are in left column and values in right column.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    fields = {}
    
    # Helper to create FieldExtraction
    def make_extraction(value, raw_text="", confidence=0.9):
        return FieldExtraction(
            value=value,
            raw_text=raw_text or str(value),
            confidence=confidence,
            pattern_used="jotform_line_parser"
        )
    
    # Find the 'Yes' marker which starts the values section in left column
    yes_idx = None
    for i, line in enumerate(lines):
        if line == 'Yes':
            yes_idx = i
            break
    
    if yes_idx:
        # Property type is the line after Yes
        if yes_idx + 1 < len(lines):
            fields['property_type'] = make_extraction(lines[yes_idx + 1])
        
        # Numeric values start at yes_idx + 2
        value_start = yes_idx + 2
        numeric_values = []
        for i in range(value_start, min(value_start + 10, len(lines))):
            clean = lines[i].replace(',', '').replace('$', '')
            if re.match(r'^\d+$', clean) and len(clean) >= 4:  # Only large numbers
                numeric_values.append(int(clean))
        
        # Map values to fields (in order: Purchase Price, As-Is Value, Rehab, ARV)
        if len(numeric_values) >= 4:
            fields['purchase_price'] = make_extraction(numeric_values[0])
            fields['as_is_value'] = make_extraction(numeric_values[1])
            fields['rehab_budget'] = make_extraction(numeric_values[2])
            fields['arv'] = make_extraction(numeric_values[3])
    
    # Extract experience from lines containing "sold"
    for line in lines:
        match = re.search(r'(\d+)\s+sold[/\s]+(\d+)\s+kept', line)
        if match:
            fields['experience'] = make_extraction(int(match.group(1)), line)
            break
        match = re.search(r'(\d+)\s+sold', line)
        if match:
            fields['experience'] = make_extraction(int(match.group(1)), line)
            break
    
    # Extract address, city, state, zip from the address section
    # The address values appear in the right column: street, city, state, zip
    for i, line in enumerate(lines):
        # Look for street address pattern (number followed by words)
        if re.match(r'^\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*$', line):
            # Check if next lines are city, state, zip
            if i + 3 < len(lines):
                possible_city = lines[i + 1]
                possible_state = lines[i + 2]
                possible_zip = lines[i + 3]
                
                # Validate city (letters only, reasonable length)
                is_city = re.match(r'^[A-Za-z\s]+$', possible_city) and 2 < len(possible_city) < 30
                # Validate state (2 uppercase letters)
                is_state = re.match(r'^[A-Z]{2}$', possible_state)
                # Validate zip (5 digits)
                is_zip = re.match(r'^\d{5}$', possible_zip)
                
                if is_city and is_state and is_zip:
                    fields['property_address'] = make_extraction(line, line)
                    fields['city'] = make_extraction(possible_city, possible_city)
                    fields['state'] = make_extraction(possible_state, possible_state)
                    fields['zip_code'] = make_extraction(possible_zip, possible_zip)
                    break
    
    return fields


def parse_loan_application(pdf_path: str, filename: str) -> ParsedLoanApplication:
    """Main parsing function - extracts all fields from loan PDF"""
    start_time = datetime.now()
    job_id = str(uuid.uuid4())
    errors = []
    
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Detect PDF type
        pdf_type = detect_pdf_type(doc)
        logger.info(f"PDF type detected: {pdf_type}")
        
        # Extract text using PyMuPDF
        text = ""
        for page in doc:
            text += page.get_text()
        
        text_length = len(text)
        logger.info(f"Extracted {text_length} characters from PDF")
        
        # Determine if OCR is needed
        ocr_used = False
        if pdf_type in ['image', 'mixed'] or needs_ocr(text):
            logger.info("PDF requires OCR processing")
            ocr_text = extract_with_ocr(pdf_path)
            if ocr_text:
                text = ocr_text
                ocr_used = True
                text_length = len(text)
                logger.info(f"OCR extracted {text_length} characters")
        
        # Normalize text
        normalized_text = normalize_text(text)
        
        # Detect lender
        lender = detect_lender(normalized_text)
        logger.info(f"Detected lender: {lender}")
        
        # Special handling for JotForm (two-column layout)
        if lender == "jotform":
            fields = parse_jotform_lines(text)
        else:
            # Select template
            if lender and lender in LENDER_TEMPLATES:
                template = LENDER_TEMPLATES[lender]
            else:
                template = LENDER_TEMPLATES["generic"]
            
            # Extract all fields using regex patterns
            fields = {}
            for field_name, patterns in template["patterns"].items():
                extraction = extract_field(normalized_text, field_name, patterns)
                fields[field_name] = extraction
                
                if extraction.value:
                    logger.info(f"Extracted {field_name}: {extraction.value} (confidence: {extraction.confidence:.2f})")
        
        # Calculate parsing time
        parsing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return ParsedLoanApplication(
            job_id=job_id,
            status="completed",
            filename=filename,
            pdf_type=pdf_type,
            ocr_used=ocr_used,
            text_length=text_length,
            fields=fields,
            lender_detected=lender,
            parsing_time_ms=parsing_time,
            errors=errors,
            raw_text_preview=normalized_text[:500]
        )
        
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        errors.append(str(e))
        
        return ParsedLoanApplication(
            job_id=job_id,
            status="failed",
            filename=filename,
            pdf_type="unknown",
            ocr_used=False,
            text_length=0,
            fields={},
            lender_detected=None,
            parsing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            errors=errors,
            raw_text_preview=""
        )


def convert_to_frontend_format(parsed: ParsedLoanApplication) -> Dict:
    """Convert parsed result to frontend-expected format"""
    result = {
        "job_id": parsed.job_id,
        "status": parsed.status,
        "filename": parsed.filename,
        "ocr_used": parsed.ocr_used,
        "lender_detected": parsed.lender_detected,
        "parsing_time_ms": parsed.parsing_time_ms,
        "errors": parsed.errors,
    }
    
    # Extract field values
    for field_name, extraction in parsed.fields.items():
        result[field_name] = extraction.value
        result[f"{field_name}_confidence"] = extraction.confidence
    
    return result


if __name__ == "__main__":
    # Test with the provided PDF
    test_pdf = "/Users/abs/.hermes/cache/documents/doc_6a10c645a84d_6537105639111405418-Loan-Application.pdf"
    
    if os.path.exists(test_pdf):
        result = parse_loan_application(test_pdf, "test_loan.pdf")
        
        print("\n" + "="*60)
        print("PARSED LOAN APPLICATION")
        print("="*60)
        print(f"Job ID: {result.job_id}")
        print(f"Status: {result.status}")
        print(f"PDF Type: {result.pdf_type}")
        print(f"OCR Used: {result.ocr_used}")
        print(f"Text Length: {result.text_length}")
        print(f"Lender Detected: {result.lender_detected}")
        print(f"Parsing Time: {result.parsing_time_ms}ms")
        
        print("\n--- Extracted Fields ---")
        for field_name, extraction in result.fields.items():
            if extraction.value:
                print(f"{field_name}: {extraction.value} (confidence: {extraction.confidence:.2f})")
        
        print("\n--- Frontend Format ---")
        frontend_data = convert_to_frontend_format(result)
        print(json.dumps(frontend_data, indent=2, default=str))
    else:
        print(f"Test PDF not found: {test_pdf}")