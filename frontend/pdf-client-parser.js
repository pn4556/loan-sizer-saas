// Client-side PDF Parser for Loan Sizer
// Uses pdf.js to extract text directly in browser

// PDF.js loaded flag
let pdfJsLoaded = false;
let pdfJsLoading = false;

// Initialize PDF.js with better error handling
async function initPdfJs() {
    if (pdfJsLoaded) return true;
    if (pdfJsLoading) {
        // Wait for existing load attempt
        while (pdfJsLoading) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        return pdfJsLoaded;
    }
    
    pdfJsLoading = true;
    
    try {
        // Check if pdfjsLib is already loaded
        if (typeof pdfjsLib !== 'undefined') {
            console.log('PDF.js already loaded');
            pdfJsLoaded = true;
            pdfJsLoading = false;
            return true;
        }
        
        // Load PDF.js from CDN
        console.log('Loading PDF.js...');
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
            script.onload = resolve;
            script.onerror = () => reject(new Error('Failed to load PDF.js'));
            document.head.appendChild(script);
        });
        
        // Wait a bit for PDF.js to initialize
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Check if loaded
        if (typeof pdfjsLib === 'undefined') {
            throw new Error('PDF.js failed to initialize');
        }
        
        // Set worker
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        console.log('PDF.js loaded successfully');
        pdfJsLoaded = true;
        return true;
    } catch (error) {
        console.error('PDF.js initialization error:', error);
        pdfJsLoaded = false;
        throw error;
    } finally {
        pdfJsLoading = false;
    }
}

// Extract text from PDF file with error handling
async function extractTextFromPDF(file) {
    try {
        await initPdfJs();
        
        console.log('Reading PDF file:', file.name, 'Size:', file.size);
        const arrayBuffer = await file.arrayBuffer();
        
        console.log('Loading PDF document...');
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        console.log('PDF loaded, pages:', pdf.numPages);
        
        let fullText = '';
        
        for (let i = 1; i <= pdf.numPages; i++) {
            try {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                
                if (textContent && textContent.items && textContent.items.length > 0) {
                    const pageText = textContent.items
                        .filter(item => item.str && item.str.trim())
                        .map(item => item.str)
                        .join(' ');
                    fullText += pageText + '\n';
                }
                
                page.cleanup && page.cleanup();
            } catch (pageError) {
                console.warn('Error reading page', i, ':', pageError);
                // Continue with other pages
            }
        }
        
        console.log('Extracted text length:', fullText.length);
        
        if (fullText.length === 0) {
            throw new Error('PDF appears to be a scanned image. No text found.');
        }
        
        return fullText;
    } catch (error) {
        console.error('PDF extraction error:', error);
        throw error;
    }
}

// Parse loan application from extracted text
function parseLoanApplicationFromText(text) {
    if (!text || typeof text !== 'string') {
        throw new Error('No text to parse');
    }
    
    console.log('Parsing text, length:', text.length);
    
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
    
    const textLower = text.toLowerCase();
    
    // Borrower name patterns
    const borrowerPatterns = [
        /(?:borrower|applicant|client|customer)[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)/,
        /name[\s:]*([A-Z][a-z]+\s+[A-Z][a-z]+)/i
    ];
    for (const pattern of borrowerPatterns) {
        const match = text.match(pattern);
        if (match) {
            data.borrower_name = match[1].trim();
            break;
        }
    }
    
    // Property address
    const addressMatch = text.match(/(\d+\s+[^,\n]{10,60}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Place|Pl|Trail|Trl|Parkway|Pkwy)[^,]*)/i);
    if (addressMatch) data.property_address = addressMatch[1].trim();
    
    // City, State, ZIP
    const cityStateZip = text.match(/([^,\n]{3,30}),?\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)/);
    if (cityStateZip) {
        data.property_city = cityStateZip[1].trim();
        data.property_state = cityStateZip[2];
        data.property_zip = cityStateZip[3];
    }
    
    // Loan amount - look for dollar amounts
    const loanPatterns = [
        /(?:loan amount|requested|financing|loan)[\s:$]*([\d,]+(?:\.\d{2})?)/i,
        /\$?([\d,]{6,10})(?:\.\d{2})?/g
    ];
    for (const pattern of loanPatterns) {
        if (typeof pattern === 'string') continue;
        const match = text.match(pattern);
        if (match) {
            const amount = parseFloat(match[1].replace(/,/g, ''));
            if (amount >= 50000 && amount <= 50000000) {
                data.loan_amount = amount;
                break;
            }
        }
    }
    
    // Property value / purchase price
    const valuePatterns = [
        /(?:purchase price|property value|appraised|sales price)[\s:$]*([\d,]+(?:\.\d{2})?)/i,
        /value[\s:$]*([\d,]{6,10})/i
    ];
    for (const pattern of valuePatterns) {
        const match = text.match(pattern);
        if (match) {
            const amount = parseFloat(match[1].replace(/,/g, ''));
            if (amount >= 50000 && amount <= 50000000) {
                data.property_value = amount;
                break;
            }
        }
    }
    
    // Credit score
    const creditMatch = text.match(/(?:credit score|fico)[\s:]*(\d{3})/i);
    if (creditMatch) {
        const score = parseInt(creditMatch[1]);
        if (score >= 300 && score <= 850) {
            data.credit_score = score;
        }
    }
    
    // DSCR
    const dscrMatch = text.match(/(?:dscr|coverage ratio)[\s:]*(\d+\.?\d*)/i);
    if (dscrMatch) {
        const dscr = parseFloat(dscrMatch[1]);
        if (dscr >= 0.5 && dscr <= 5.0) {
            data.dscr = dscr;
        }
    }
    
    // NOI
    const noiMatch = text.match(/(?:noi|net operating income)[\s:$]*([\d,]+)/i);
    if (noiMatch) {
        data.noi = parseFloat(noiMatch[1].replace(/,/g, ''));
    }
    
    // Bedrooms
    const bedsMatch = text.match(/(\d+)\s*(?:bed|br)/i);
    if (bedsMatch) {
        const beds = parseInt(bedsMatch[1]);
        if (beds >= 0 && beds <= 20) data.beds = beds;
    }
    
    // Bathrooms
    const bathsMatch = text.match(/(\d+(?:\.5)?)\s*(?:bath|ba)/i);
    if (bathsMatch) {
        const baths = parseFloat(bathsMatch[1]);
        if (baths >= 0 && baths <= 20) data.baths = baths;
    }
    
    // Square footage
    const sqftMatch = text.match(/(\d{3,5})\s*(?:sq\.?\s*ft|sf|square feet)/i);
    if (sqftMatch) data.sqft = parseInt(sqftMatch[1]);
    
    // Year built
    const yearMatch = text.match(/(?:year built|built)[\s:]*(\d{4})/i);
    if (yearMatch) {
        const year = parseInt(yearMatch[1]);
        if (year >= 1800 && year <= 2026) data.year_built = year;
    }
    
    console.log('Parsed fields:', Object.entries(data).filter(([k,v]) => v).map(([k,v]) => k));
    
    return data;
}

// Main function to parse PDF file
async function parsePDFFile(file) {
    console.log('Starting PDF parse for:', file.name);
    
    try {
        if (!file || file.size === 0) {
            throw new Error('No file provided or file is empty');
        }
        
        if (file.size > 20 * 1024 * 1024) {
            throw new Error('PDF too large (max 20MB)');
        }
        
        // Extract text
        const text = await extractTextFromPDF(file);
        
        if (!text || text.length === 0) {
            throw new Error('Could not extract text from PDF');
        }
        
        // Parse data
        const data = parseLoanApplicationFromText(text);
        
        // Calculate confidence
        const filledFields = Object.values(data).filter(v => v !== '' && v !== null && v !== undefined).length;
        const totalFields = Object.keys(data).length;
        const confidence = Math.round((filledFields / totalFields) * 100);
        
        console.log('Parse complete. Confidence:', confidence + '%');
        
        return {
            success: true,
            data: data,
            confidence: confidence,
            raw_text_preview: text.substring(0, 500),
            method: 'client-side-pdf-js'
        };
    } catch (error) {
        console.error('PDF parse error:', error);
        return {
            success: false,
            error: error.message,
            data: {},
            confidence: 0
        };
    }
}

// Make functions globally available
window.parsePDFFile = parsePDFFile;
window.extractTextFromPDF = extractTextFromPDF;
window.parseLoanApplicationFromText = parseLoanApplicationFromText;

console.log('PDF Client Parser loaded');