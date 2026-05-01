
// ==================== UNIFIED BATCH PROCESSOR ====================
// Works client-side with optional backend fallback
// Supports 1-100 applications

class ClientBatchProcessor {
    constructor() {
        this.applications = [];
        this.isProcessing = false;
        this.processingInterval = null;
        this.results = [];
        this.onProgress = null;
        this.onComplete = null;
        this.onError = null;
    }

    // Generate demo applications (1-100)
    generateDemoApplications(count = 10, type = 'mixed') {
        const apps = [];
        const firstNames = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Lisa', 'William', 'Jennifer', 'James', 'Mary', 'Richard', 'Patricia', 'Thomas', 'Linda', 'Charles', 'Barbara', 'Daniel', 'Susan'];
        const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson'];
        const cities = ['Los Angeles', 'San Diego', 'San Francisco', 'Sacramento', 'Oakland', 'San Jose', 'Fresno', 'Bakersfield', 'Long Beach', 'Riverside', 'Santa Ana', 'Anaheim', 'Stockton', 'Irvine'];
        const streets = ['Main St', 'Elm St', 'Maple Ave', 'Oak Dr', 'Cedar Ln', 'Pine St', 'Washington Ave', 'Park Blvd', 'Lake St', 'Hill Rd', 'Canyon Dr', 'Sunset Blvd', 'Ocean Ave'];
        const loanTypes = type === 'rtl' ? ['RTL', 'Fix & Flip'] : 
                         type === 'dscr' ? ['DSCR 1-4 Unit', 'DSCR 4-9 Unit', 'DSCR Mixed Use'] :
                         type === 'bridge' ? ['Bridge'] :
                         ['DSCR 1-4 Unit', 'DSCR 4-9 Unit', 'RTL', 'Bridge', 'Fix & Flip', 'DSCR Mixed Use'];
        
        for (let i = 1; i <= count; i++) {
            const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
            const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
            const city = cities[Math.floor(Math.random() * cities.length)];
            const streetNum = Math.floor(Math.random() * 9000) + 1000;
            const street = streets[Math.floor(Math.random() * streets.length)];
            const loanType = loanTypes[Math.floor(Math.random() * loanTypes.length)];
            
            // Generate realistic loan amounts based on type
            let loanAmount, propertyValue, monthlyIncome;
            if (loanType.includes('DSCR')) {
                loanAmount = Math.floor(Math.random() * 1500000) + 300000;
                propertyValue = Math.floor(loanAmount * (1 + Math.random() * 0.5));
                monthlyIncome = Math.floor(loanAmount * 0.008);
            } else {
                loanAmount = Math.floor(Math.random() * 800000) + 150000;
                propertyValue = Math.floor(loanAmount * (1.2 + Math.random() * 0.8));
                monthlyIncome = Math.floor(Math.random() * 15000) + 8000;
            }
            
            const fico = Math.floor(Math.random() * 200) + 580;
            const monthlyDebts = Math.floor(monthlyIncome * (0.2 + Math.random() * 0.3));
            const dscr = loanType.includes('DSCR') ? (Math.random() * 1.5 + 0.8).toFixed(2) : null;
            const experience = Math.floor(Math.random() * 15);
            
            apps.push({
                id: `app_${Date.now()}_${i}`,
                applicantName: `${firstName} ${lastName}`,
                entityName: `${firstName} ${lastName} LLC`,
                loanType: loanType,
                loanAmount: loanAmount,
                propertyValue: propertyValue,
                propertyAddress: `${streetNum} ${street}`,
                city: city,
                state: 'CA',
                zipCode: String(Math.floor(Math.random() * 90000) + 10000),
                fico: fico,
                monthlyIncome: monthlyIncome,
                monthlyDebts: monthlyDebts,
                dscr: dscr,
                experience: experience,
                status: 'pending',
                result: null,
                details: null,
                createdAt: new Date().toISOString(),
                processedAt: null
            });
        }
        
        return apps;
    }

    // Process a single application client-side
    processApplication(app) {
        // Determine pass/fail/conditional based on criteria
        let result = 'PASS';
        let reasons = [];
        let maxLoanAmount = app.loanAmount;
        
        // FICO check
        if (app.fico < 620) {
            result = 'FAIL';
            reasons.push('Credit score below minimum (620)');
        } else if (app.fico < 660) {
            result = 'CONDITIONAL';
            reasons.push('Credit score below preferred threshold');
            maxLoanAmount = app.loanAmount * 0.8;
        }
        
        // LTV check
        const ltv = (app.loanAmount / app.propertyValue) * 100;
        if (ltv > 80) {
            if (result === 'PASS') result = 'CONDITIONAL';
            reasons.push(`High LTV (${ltv.toFixed(1)}%)`);
            maxLoanAmount = app.propertyValue * 0.8;
        }
        
        // DSCR check (for DSCR loans)
        if (app.loanType.includes('DSCR') && app.dscr) {
            if (parseFloat(app.dscr) < 1.0) {
                result = 'FAIL';
                reasons.push(`DSCR below 1.0 (${app.dscr})`);
            } else if (parseFloat(app.dscr) < 1.25) {
                if (result === 'PASS') result = 'CONDITIONAL';
                reasons.push(`Low DSCR (${app.dscr})`);
            }
        }
        
        // DTI check (for non-DSCR loans)
        if (!app.loanType.includes('DSCR')) {
            const dti = (app.monthlyDebts / app.monthlyIncome) * 100;
            if (dti > 50) {
                result = 'FAIL';
                reasons.push(`DTI too high (${dti.toFixed(1)}%)`);
            } else if (dti > 43) {
                if (result === 'PASS') result = 'CONDITIONAL';
                reasons.push(`Elevated DTI (${dti.toFixed(1)}%)`);
            }
        }
        
        // Generate lender recommendations based on loan type
        let recommendedLenders = [];
        if (app.loanType.includes('RTL') || app.loanType.includes('Fix')) {
            recommendedLenders = ['ICE Capital', 'IFC', 'Eastview Capital'];
        } else if (app.loanType.includes('DSCR')) {
            recommendedLenders = ['Lima One', 'Kiavi', 'Visio'];
        } else if (app.loanType.includes('Bridge')) {
            recommendedLenders = ['IFC', 'Eastview Capital'];
        }
        
        return {
            ...app,
            status: 'completed',
            result: result,
            ltv: ltv.toFixed(2),
            maxLoanAmount: Math.floor(maxLoanAmount),
            reasons: reasons,
            recommendedLenders: recommendedLenders,
            interestRate: this.calculateRate(app, result),
            monthlyPayment: this.calculatePayment(maxLoanAmount, app),
            processedAt: new Date().toISOString()
        };
    }
    
    calculateRate(app, result) {
        let baseRate = 7.5;
        
        // Adjust for FICO
        if (app.fico >= 740) baseRate -= 0.5;
        else if (app.fico >= 700) baseRate -= 0.25;
        else if (app.fico < 660) baseRate += 0.75;
        else if (app.fico < 620) baseRate += 1.5;
        
        // Adjust for result
        if (result === 'CONDITIONAL') baseRate += 0.5;
        
        // Adjust for loan type
        if (app.loanType.includes('Bridge')) baseRate += 0.75;
        if (app.loanType.includes('RTL')) baseRate += 1.0;
        
        return baseRate.toFixed(2);
    }
    
    calculatePayment(amount, app) {
        const rate = parseFloat(this.calculateRate(app, 'PASS')) / 100 / 12;
        const term = 360; // 30 years
        const payment = amount * (rate * Math.pow(1 + rate, term)) / (Math.pow(1 + rate, term) - 1);
        return Math.floor(payment);
    }

    // Process all applications with progress updates
    async processAll(applications) {
        this.applications = applications;
        this.results = [];
        this.isProcessing = true;
        
        const batchSize = 5; // Process 5 at a time for UI updates
        const total = applications.length;
        
        for (let i = 0; i < total; i += batchSize) {
            const batch = applications.slice(i, i + batchSize);
            
            // Process batch
            const processedBatch = batch.map(app => {
                app.status = 'processing';
                return this.processApplication(app);
            });
            
            this.results.push(...processedBatch);
            
            // Update progress
            const progress = {
                completed: this.results.length,
                total: total,
                percentage: Math.round((this.results.length / total) * 100),
                pass: this.results.filter(r => r.result === 'PASS').length,
                conditional: this.results.filter(r => r.result === 'CONDITIONAL').length,
                fail: this.results.filter(r => r.result === 'FAIL').length
            };
            
            if (this.onProgress) {
                this.onProgress(progress);
            }
            
            // Small delay for visual feedback
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        this.isProcessing = false;
        
        if (this.onComplete) {
            this.onComplete(this.results);
        }
        
        return this.results;
    }

    // Export results to CSV
    exportToCSV(results = this.results) {
        if (!results || results.length === 0) return null;
        
        const headers = [
            'Application ID', 'Date', 'Applicant Name', 'Entity', 'Loan Type',
            'Loan Amount', 'Property Value', 'Property Address', 'City', 'State',
            'FICO Score', 'Result', 'Max Loan Amount', 'LTV %', 'Interest Rate',
            'Monthly Payment', 'Recommended Lenders', 'Reasons'
        ];
        
        const rows = results.map(r => [
            r.id,
            new Date(r.processedAt || r.createdAt).toLocaleDateString(),
            r.applicantName,
            r.entityName,
            r.loanType,
            r.loanAmount,
            r.propertyValue,
            r.propertyAddress,
            r.city,
            r.state,
            r.fico,
            r.result,
            r.maxLoanAmount,
            r.ltv,
            r.interestRate + '%',
            r.monthlyPayment,
            (r.recommendedLenders || []).join('; '),
            (r.reasons || []).join('; ')
        ]);
        
        const csv = [headers.join(','), ...rows.map(r => r.map(cell => `"${cell}"`).join(','))].join('\n');
        return csv;
    }

    // Export results to PDF-like structured data
    exportToPDFData(results = this.results) {
        return {
            generatedAt: new Date().toISOString(),
            totalApplications: results.length,
            summary: {
                pass: results.filter(r => r.result === 'PASS').length,
                conditional: results.filter(r => r.result === 'CONDITIONAL').length,
                fail: results.filter(r => r.result === 'FAIL').length,
                totalAmount: results.reduce((sum, r) => sum + r.loanAmount, 0),
                approvedAmount: results.filter(r => r.result === 'PASS').reduce((sum, r) => sum + r.maxLoanAmount, 0)
            },
            applications: results
        };
    }
}

// Global batch processor instance
window.clientBatchProcessor = new ClientBatchProcessor();
