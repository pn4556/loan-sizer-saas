// Client-side PDF Parser for Loan Sizer
// Uses pdf.js to extract text directly in browser

// Load PDF.js from CDN
const PDF_JS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
const PDF_JS_WORKER_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

let pdfJsLoaded = false;

// Initialize PDF.js
async function initPdfJs() {
    if (pdfJsLoaded) return;
    
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = PDF_JS_URL;
        script.onload = () => {
            pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_JS_WORKER_URL;
            pdfJsLoaded = true;
            resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Extract text from PDF file
async function extractTextFromPDF(file) {
    await initPdfJs();
    
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    
    let fullText = '';
    const numPages = pdf.numPages;
    
    for (let i = 1; i <= numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map(item => item.str).join(' ');
        fullText += pageText + '\n';
    }
    
    return fullText;
}

// Parse loan application from extracted text
function parseLoanApplicationFromText(text) {
    const data = {
        borrower_name: '',
        property_address: '',
        property_city: '',
        property_state: '',
        property_zip: '',
        loan_amount: '',
        property_value: '',
        credit_score: '',
        dscr: '',
        noi: '',
        property_type: '',
        beds: '',
        baths: '',
        sqft: '',
        year_built: '',
        rental_income: '',
        occupancy: '',
        property_taxes: '',
        insurance: '',
        hoa_fees: '',
        gross_income: '',
        expenses: ''
    };
    
    // Borrower name patterns
    const borrowerMatch = text.match(/(?:borrower|applicant|client|name)[\s:]*(\w+\s+\w+)/i);
    if (borrowerMatch) data.borrower_name = borrowerMatch[1];
    
    // Property address
    const addressMatch = text.match(/(\d+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Place|Pl|Trail|Trl|Parkway|Pkwy)[^,]*)/i);
    if (addressMatch) data.property_address = addressMatch[1].trim();
    
    // City, State, ZIP
    const cityStateZip = text.match(/([^,]+),?\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\s*(\d{5}(?:-\d{4})?)/i);
    if (cityStateZip) {
        data.property_city = cityStateZip[1].trim();
        data.property_state = cityStateZip[2];
        data.property_zip = cityStateZip[3];
    }
    
    // Loan amount
    const loanMatch = text.match(/(?:loan amount|requested amount|financing)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (loanMatch) {
        data.loan_amount = parseFloat(loanMatch[1].replace(/,/g, ''));
    }
    
    // Property value / purchase price
    const valueMatch = text.match(/(?:purchase price|property value|appraised value|sales price)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (valueMatch) {
        data.property_value = parseFloat(valueMatch[1].replace(/,/g, ''));
    }
    
    // Credit score
    const creditMatch = text.match(/(?:credit score|fico|credit)[\s:]*(\d{3})/i);
    if (creditMatch) {
        const score = parseInt(creditMatch[1]);
        if (score >= 300 && score <= 850) {
            data.credit_score = score;
        }
    }
    
    // DSCR (Debt Service Coverage Ratio)
    const dscrMatch = text.match(/(?:dscr|debt service coverage|coverage ratio)[\s:]*(\d+\.?\d*)/i);
    if (dscrMatch) {
        data.dscr = parseFloat(dscrMatch[1]);
    }
    
    // NOI (Net Operating Income)
    const noiMatch = text.match(/(?:noi|net operating income)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (noiMatch) {
        data.noi = parseFloat(noiMatch[1].replace(/,/g, ''));
    }
    
    // Property type
    const typeMatch = text.match(/(?:property type|type of property|building type)[\s:]*(\w+)/i);
    if (typeMatch) {
        data.property_type = typeMatch[1];
    }
    
    // Bedrooms
    const bedsMatch = text.match(/(\d+)\s*(?:bed|bedroom|br)/i);
    if (bedsMatch) data.beds = parseInt(bedsMatch[1]);
    
    // Bathrooms
    const bathsMatch = text.match(/(\d+(?:\.5)?)\s*(?:bath|bathroom|ba)/i);
    if (bathsMatch) data.baths = parseFloat(bathsMatch[1]);
    
    // Square footage
    const sqftMatch = text.match(/(\d{3,5})\s*(?:sq\.?\s*ft\.?|square feet|sf)/i);
    if (sqftMatch) data.sqft = parseInt(sqftMatch[1]);
    
    // Year built
    const yearMatch = text.match(/(?:year built|built|construction year)[\s:]*(\d{4})/i);
    if (yearMatch) {
        const year = parseInt(yearMatch[1]);
        if (year >= 1800 && year <= 2026) {
            data.year_built = year;
        }
    }
    
    // Rental income
    const rentMatch = text.match(/(?:rental income|monthly rent|gross rent)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (rentMatch) {
        data.rental_income = parseFloat(rentMatch[1].replace(/,/g, ''));
    }
    
    // Occupancy
    const occMatch = text.match(/(\d+)%?\s*(?:occupancy|occupied)/i);
    if (occMatch) data.occupancy = parseInt(occMatch[1]);
    
    // Property taxes
    const taxMatch = text.match(/(?:property tax|taxes|annual tax)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (taxMatch) {
        data.property_taxes = parseFloat(taxMatch[1].replace(/,/g, ''));
    }
    
    // Insurance
    const insMatch = text.match(/(?:insurance|hazard insurance)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (insMatch) {
        data.insurance = parseFloat(insMatch[1].replace(/,/g, ''));
    }
    
    // Gross income
    const grossMatch = text.match(/(?:gross income|gross revenue|total income)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (grossMatch) {
        data.gross_income = parseFloat(grossMatch[1].replace(/,/g, ''));
    }
    
    // Expenses
    const expMatch = text.match(/(?:expenses|operating expenses|total expenses)[\s:$]*([\d,]+(?:\.\d{2})?)/i);
    if (expMatch) {
        data.expenses = parseFloat(expMatch[1].replace(/,/g, ''));
    }
    
    return data;
}

// Main function to parse PDF file
async function parsePDFFile(file) {
    try {
        console.log('Parsing PDF:', file.name);
        const text = await extractTextFromPDF(file);
        console.log('Extracted text length:', text.length);
        
        const data = parseLoanApplicationFromText(text);
        console.log('Parsed data:', data);
        
        // Calculate confidence score
        const filledFields = Object.values(data).filter(v => v !== '' && v !== null && v !== undefined).length;
        const totalFields = Object.keys(data).length;
        const confidence = Math.round((filledFields / totalFields) * 100);
        
        return {
            success: true,
            data: data,
            confidence: confidence,
            raw_text: text.substring(0, 500) + '...',
            method: 'client-side-pdf-js'
        };
    } catch (error) {
        console.error('PDF parsing error:', error);
        return {
            success: false,
            error: error.message,
            data: {}
        };
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { parsePDFFile, extractTextFromPDF, parseLoanApplicationFromText };
}