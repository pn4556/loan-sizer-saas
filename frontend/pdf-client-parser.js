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
    
    console.log('=== PARSING PDF TEXT ===');
    console.log('Text length:', text.length);
    console.log('First 2000 chars:', text.substring(0, 2000));
    
    // Split into lines and clean up
    const lines = text.split(/\n/).map(l => l.trim()).filter(l => l.length > 0);
    
    // STRATEGY 1: Two-column PDF format detection
    // Some PDFs have labels in one column and values in another
    // Format: "Purchase Price:" then later "219000", "As-Is Value:" then "219000", etc.
    
    // Find the section after "Closing Agent Email:" where values start appearing
    let valuesStartIndex = -1;
    const labelSectionEndMarkers = [
        'Closing Agent Email:',
        'Closing Agent Phone:',
        'Subject Property Address:'
    ];
    
    for (let i = 0; i < lines.length; i++) {
        // Look for the end of the labels section
        if (labelSectionEndMarkers.some(marker => lines[i].includes(marker))) {
            // Values typically start 1-3 lines after the last label
            valuesStartIndex = i + 1;
        }
    }
    
    // STRATEGY 2: Look for the sequence pattern
    // Find a "Yes" line followed by property type, then numerical values
    let yesIndex = -1;
    for (let i = 0; i < lines.length; i++) {
        if (lines[i] === 'Yes' || lines[i] === 'No') {
            yesIndex = i;
            console.log('Found Yes/No at index', i, ':', lines[i]);
            // Check if next line is a property type
            if (i + 1 < lines.length && 
                (lines[i+1].includes('Single') || lines[i+1].includes('Multi') || 
                 lines[i+1].includes('Home') || lines[i+1].includes('Property'))) {
                console.log('Found property type at index', i+1, ':', lines[i+1]);
                valuesStartIndex = i;
                break;
            }
        }
    }
    
    // STRATEGY 3: Collect all standalone numbers that appear to be dollar amounts
    // Look for a cluster of 4-6 numbers that look like loan values
    const potentialValues = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Match standalone numbers (5-6 digits typical for property values)
        // Exclude: years (4 digits starting with 19 or 20), phone numbers, zip codes
        const numMatch = line.match(/^(\d{5,6})$/);
        if (numMatch) {
            const num = parseInt(numMatch[1]);
            // Filter out years (1900-2030), keep property values
            if (!(num >= 1900 && num <= 2030)) {
                potentialValues.push({ value: num, index: i, context: lines.slice(Math.max(0, i-2), Math.min(lines.length, i+3)) });
            }
        }
    }
    
    console.log('Potential loan values found:', potentialValues);
    
    // If we found a cluster of 4+ consecutive property-value numbers, use them
    if (potentialValues.length >= 4) {
        // Find the first cluster of 4 consecutive numbers
        for (let i = 0; i <= potentialValues.length - 4; i++) {
            const cluster = potentialValues.slice(i, i + 4);
            const indices = cluster.map(c => c.index);
            // Check if they're within 10 lines of each other (consecutive in PDF)
            const spread = Math.max(...indices) - Math.min(...indices);
            
            if (spread <= 10) {
                console.log('Found valid cluster of 4 values at indices:', indices);
                // Assign in order: Purchase Price, As-Is Value, Rehab Budget, ARV
                result.purchase_price = cluster[0].value;
                result.as_is_value = cluster[1].value;
                result.rehab_budget = cluster[2].value;
                result.arv = cluster[3].value;
                
                console.log('✓ Set purchase_price:', result.purchase_price);
                console.log('✓ Set as_is_value:', result.as_is_value);
                console.log('✓ Set rehab_budget:', result.rehab_budget);
                console.log('✓ Set arv:', result.arv);
                break;
            }
        }
    }
    
    // STRATEGY 4: Fallback - Look for inline pattern if column-based failed
    if (!result.purchase_price) {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            // Look for line containing the specific loan value pattern
            // Pattern: Yes/No followed by property type, then 4-5 digit numbers
            if (line.match(/Yes\s+\w+.*\d{5,}.*\d{5,}.*\d{4,}/)) {
                console.log('Found inline values line at index', i, ':', line);
                const allNumbers = line.match(/(\d[\d,]+)/g);
                if (allNumbers && allNumbers.length >= 4) {
                    const propertyNumbers = allNumbers
                        .map(n => parseFloat(n.replace(/,/g, '')))
                        .filter(n => n > 10000);
                    
                    if (propertyNumbers.length >= 4) {
                        result.purchase_price = propertyNumbers[0];
                        result.as_is_value = propertyNumbers[1];
                        result.rehab_budget = propertyNumbers[2];
                        result.arv = propertyNumbers[3];
                        
                        console.log('✓ Set purchase_price (inline):', result.purchase_price);
                        console.log('✓ Set as_is_value (inline):', result.as_is_value);
                        console.log('✓ Set rehab_budget (inline):', result.rehab_budget);
                        console.log('✓ Set arv (inline):', result.arv);
                    }
                }
                break;
            }
        }
    }
    
    // STRATEGY 5: Extract text fields (entity name, borrower name, property address)
    // These appear in different sections of the PDF
    
    // Find the second label section (Entity Name:, First Name:, etc.)
    let secondLabelSectionStart = -1;
    for (let i = 0; i < lines.length; i++) {
        if (lines[i] === 'Entity Name:' && i > 20) {
            secondLabelSectionStart = i;
            console.log('Found second label section at line', i);
            break;
        }
    }
    
    // PHASE 1: Extract property address from early values (after numerical values)
    const earlyTextValues = [];
    if (potentialValues.length >= 4) {
        const lastNumIndex = potentialValues[Math.min(3, potentialValues.length - 1)].index;
        const earlyValuesEnd = secondLabelSectionStart > 0 ? secondLabelSectionStart : lastNumIndex + 20;
        
        for (let i = lastNumIndex + 1; i < lines.length && i < earlyValuesEnd; i++) {
            const line = lines[i];
            // Skip known non-value lines
            const skipPatterns = [
                'Yes', 'No', 'Single-Family Home', 'Multi-Family Home',
                'US Citizen', 'Married', 'Unmarried', 'Permanent Resident Alien',
                'Limited Liability Company', 'FL', 'PA', 'Ca', 'Tx', 'Ny', 'Fl',
                'Guarantor Personal Information', 'Entity Information',
                'City:', 'State', 'Zip Code:', 'First Name:', 'Last Name:',
                'Phone Number:', 'Email Address:', 'Residency Status:',
                'Marital Status:', 'SSN/ITIN:', 'Date of Birth:', 'Present Address:',
                'Entity Name:', 'Entity Type:', 'EIN Number:', 'State of Incorporation:',
                'Entity Present Address:'
            ];
            
            if (skipPatterns.includes(line) || line.endsWith(':')) continue;
            if (/^\d+$/.test(line)) continue;
            if (line.length < 2) continue;
            if (/^\(\d{3}\)/.test(line)) continue; // Phone
            if (/^\d{2}\/\d{2}\/\d{4}$/.test(line)) continue; // Date
            if (line.includes('@')) continue; // Email
            if (line.length > 40 && !/LLC|Inc|Corp/i.test(line)) continue; // Skip long instructional text
            if (/Please|processing|conﬁrm/i.test(line)) continue; // Skip instructional text
            
            earlyTextValues.push({ value: line, index: i });
        }
    }
    
    console.log('Early text values (for address):', earlyTextValues);
    
    // Extract Property Address from early values
    if (!result.property_address) {
        for (const item of earlyTextValues) {
            const val = item.value;
            // Pattern: Street number followed by street name and type
            if (/^\d+\s+[A-Za-z\s]+(Rd|St|Ave|Blvd|Dr|Ln|Way|Ct|Pl|Ter)/i.test(val)) {
                result.property_address = val;
                console.log('✓ Set property_address:', val);
                break;
            }
        }
    }
    
    // PHASE 2: Extract entity and borrower from later values (after second label section)
    if (secondLabelSectionStart > 0) {
        const laterTextValues = [];
        
        // Start after the second label section ends (around Present Address:)
        let secondLabelSectionEnd = secondLabelSectionStart;
        for (let i = secondLabelSectionStart; i < lines.length && i < secondLabelSectionStart + 30; i++) {
            if (lines[i] === 'Present Address:' || lines[i] === 'Zip Code:') {
                secondLabelSectionEnd = i + 1;
            }
        }
        
        for (let i = secondLabelSectionEnd; i < lines.length && i < secondLabelSectionEnd + 30; i++) {
            const line = lines[i];
            
            // Skip known non-value lines
            const skipPatterns = [
                'Yes', 'No', 'Single-Family Home', 'Multi-Family Home',
                'US Citizen', 'Married', 'Unmarried', 'Permanent Resident Alien',
                'Limited Liability Company', 'FL', 'PA', 'Ca', 'Tx', 'Ny', 'Fl', 'Bl',
                'Guarantor Personal Information', 'Entity Information',
                'City:', 'State', 'Zip Code:', 'First Name:', 'Last Name:',
                'Phone Number:', 'Email Address:', 'Residency Status:',
                'Marital Status:', 'SSN/ITIN:', 'Date of Birth:', 'Present Address:',
                'Entity Name:', 'Entity Type:', 'EIN Number:', 'State of Incorporation:',
                'Entity Present Address:'
            ];
            
            if (skipPatterns.includes(line) || line.endsWith(':')) continue;
            if (/^\d+$/.test(line)) continue;
            if (line.length < 2) continue;
            if (/^\(\d{3}\)/.test(line)) continue; // Phone
            if (/^\d{2}\/\d{2}\/\d{4}$/.test(line)) continue; // Date
            if (line.includes('@')) continue; // Email
            if (line.length > 40 && !/LLC|Inc|Corp/i.test(line)) continue; // Skip instructional text
            if (/Please|processing|conﬁrm/i.test(line)) continue; // Skip instructional text
            
            laterTextValues.push({ value: line, index: i });
        }
        
        console.log('Later text values (for entity/borrower):', laterTextValues);
        
        // Extract Entity Name (contains LLC, Inc, Corp, etc.)
        if (!result.entity_name) {
            for (const item of laterTextValues) {
                const val = item.value;
                if (/LLC|Inc\.?|Corp\.?|Company|Partnership/i.test(val)) {
                    result.entity_name = val;
                    console.log('✓ Set entity_name:', val);
                    break;
                }
            }
        }
        
        // Extract Borrower Name (First and Last name on consecutive lines)
        if (!result.borrower_name) {
            for (let i = 0; i < laterTextValues.length - 1; i++) {
                const first = laterTextValues[i].value;
                const second = laterTextValues[i + 1].value;
                
                // Pattern: Capitalized first name followed by capitalized last name
                if (/^[A-Z][a-z]+$/.test(first) && /^[A-Z][a-z]+$/.test(second)) {
                    // Make sure they're consecutive in the original lines
                    if (laterTextValues[i + 1].index - laterTextValues[i].index <= 2) {
                        result.borrower_name = first + ' ' + second;
                        console.log('✓ Set borrower_name:', result.borrower_name);
                        break;
                    }
                }
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
