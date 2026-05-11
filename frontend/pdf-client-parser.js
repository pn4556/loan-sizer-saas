/**
 * Client-side PDF Parser for Loan Sizer
 * Uses PDF.js to extract text and parse loan application data
 */

// Extract text from PDF using PDF.js
async function extractTextFromPDF(file) {
    try {
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        
        let fullText = '';
        
        // Extract text from all pages
        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const textContent = await page.getTextContent();
            const pageText = textContent.items.map(item => item.str).join(' ');
            fullText += pageText + '\n';
        }
        
        return fullText;
    } catch (error) {
        console.error('Error extracting PDF text:', error);
        throw new Error('Failed to read PDF file');
    }
}

// Parse loan application from extracted text
function parseLoanApplicationFromText(text) {
    const result = {};
    const lineMap = {};
    
    console.log('=== PARSING PDF TEXT ===');
    console.log('Text length:', text.length);
    console.log('First 2000 chars:', text.substring(0, 2000));
    
    // Split into lines and clean up
    const lines = text.split(/\n/).map(l => l.trim()).filter(l => l.length > 0);
    
    // Find the data section - look for the line with the actual loan values
    // The values appear in a specific pattern: 260000 269000 40000 405000
    let valuesLineIndex = -1;
    let valuesLine = '';
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Look for line containing the specific loan value pattern
        // Pattern: Yes/No followed by property type, then 4-5 digit numbers
        if (line.match(/Yes\s+\w+.*\d{5,}.*\d{5,}.*\d{4,}/)) {
            valuesLine = line;
            valuesLineIndex = i;
            console.log('Found values line at index', i, ':', line);
            break;
        }
    }
    
    // If we found the values line, extract all numbers from it
    if (valuesLine) {
        const allNumbers = valuesLine.match(/(\d[\d,]+)/g);
        console.log('All numbers found:', allNumbers);
        
        if (allNumbers && allNumbers.length >= 4) {
            // Filter for property-sized numbers (5+ digits, > 10000)
            const propertyNumbers = allNumbers
                .map(n => parseFloat(n.replace(/,/g, '')))
                .filter(n => n > 10000);
            
            console.log('Property-sized numbers:', propertyNumbers);
            
            // For JotForm bridge loan applications, the order is typically:
            // 0: Purchase Price (260000)
            // 1: As-Is Value (269000)
            // 2: Rehab Budget (40000)
            // 3: ARV (405000)
            
            if (propertyNumbers.length >= 4) {
                const purchasePrice = propertyNumbers[0];
                const asIsValue = propertyNumbers[1];
                const rehabBudget = propertyNumbers[2];
                const arv = propertyNumbers[3];
                
                result.purchase_price = purchasePrice;
                result.as_is_value = asIsValue;
                result.rehab_budget = rehabBudget;
                result.arv = arv;
                
                console.log('✓ Set purchase_price:', purchasePrice);
                console.log('✓ Set as_is_value:', asIsValue);
                console.log('✓ Set rehab_budget:', rehabBudget);
                console.log('✓ Set arv:', arv);
            }
        }
    }
    
    // Fallback: Use regex patterns if line-based parsing didn't find values
    const extractValue = (patterns, fieldName) => {
        if (result[fieldName]) return; // Already found
        for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                const val = match[1].replace(/[$,\s]/g, '').trim();
                const numVal = parseFloat(val);
                if (!isNaN(numVal) && numVal > 0) {
                    console.log(`✓ Extracted ${fieldName} (regex):`, numVal);
                    result[fieldName] = numVal;
                    return;
                }
            }
        }
    };
    
    // Only use regex fallbacks for fields not found via line parsing
    if (!result.purchase_price) {
        extractValue([
            /Purchase Price[:\s]+\$?([\d,]+)/i,
            /purchase.*?\$?([\d,]{5,})/i
        ], 'purchase_price');
    }
    
    if (!result.as_is_value) {
        extractValue([
            /As-Is (?:Property )?Value[:\s]+\$?([\d,]+)/i,
            /as.is.*?\$?([\d,]{5,})/i
        ], 'as_is_value');
    }
    
    if (!result.arv) {
        extractValue([
            /After Repair (?:Property )?Value[:\s]+\$?([\d,]+)/i,
            /ARV[:\s]+\$?([\d,]+)/i,
            /arv.*?\$?([\d,]{5,})/i
        ], 'arv');
    }
    
    if (!result.rehab_budget) {
        extractValue([
            /Rehab (?:Amount|Budget)[:\s]+\$?([\d,]+)/i,
            /Renovation Budget[:\s]+\$?([\d,]+)/i,
            /rehab.*?\$?([\d,]{3,})/i
        ], 'rehab_budget');
    }
    
    // FICO patterns
    if (!result.fico) {
        extractValue([
            /FICO[:\s]+(\d{3})/i,
            /Credit Score[:\s]+(\d{3})/i,
            /fico.*?\b(\d{3})\b/i
        ], 'fico');
    }
    
    // Experience patterns
    if (!result.experience) {
        extractValue([
            /Experience[:\s]+(\d+)/i,
            /(\d+)\s+(?:years|deals|flips|sold)/i,
            /(\d+)\s+sold/i
        ], 'experience');
    }
    
    // Property Type
    const propTypeMatch = text.match(/Property Type[:\s]+([A-Za-z\-]+(?:\s+[A-Za-z]+)?)/i);
    if (propTypeMatch) {
        result.property_type = propTypeMatch[1].trim();
    }
    
    // Loan Purpose
    if (text.match(/bridge/i)) {
        result.loan_purpose = 'bridge';
    } else if (text.match(/purchase/i)) {
        result.loan_purpose = 'purchase';
    } else if (text.match(/refinance/i)) {
        result.loan_purpose = 'refinance';
    }
    
    console.log('=== EXTRACTION RESULT ===', result);
    
    return result;
}

// Calculate confidence score based on fields found
function calculateConfidence(parsed) {
    const criticalFields = ['purchase_price', 'as_is_value'];
    const optionalFields = ['arv', 'rehab_budget', 'fico', 'experience'];
    
    let criticalFound = criticalFields.filter(f => parsed[f] && parsed[f] > 0).length;
    let optionalFound = optionalFields.filter(f => parsed[f] && (parsed[f] > 0 || typeof parsed[f] === 'string')).length;
    
    return Math.round((criticalFound / criticalFields.length) * 70 + (optionalFound / optionalFields.length) * 30);
}

// Main function to parse PDF file
async function parsePDFFile(file) {
    console.log('Starting PDF parse for:', file.name);
    
    try {
        // Extract text from PDF
        const text = await extractTextFromPDF(file);
        
        if (!text || text.length === 0) {
            return {
                success: false,
                error: 'Could not extract text from PDF',
                data: null
            };
        }
        
        // Parse loan application data
        const parsed = parseLoanApplicationFromText(text);
        const confidence = calculateConfidence(parsed);
        
        return {
            success: true,
            data: parsed,
            confidence: confidence,
            rawText: text.substring(0, 1000) // First 1000 chars for debugging
        };
        
    } catch (error) {
        console.error('PDF parsing error:', error);
        return {
            success: false,
            error: error.message || 'Failed to parse PDF',
            data: null
        };
    }
}

// Make functions globally available
window.parsePDFFile = parsePDFFile;
window.extractTextFromPDF = extractTextFromPDF;
window.parseLoanApplicationFromText = parseLoanApplicationFromText;

console.log('PDF Client Parser loaded');
