# Demo Application Batches

This folder contains demo loan application batches for testing the Multi-Application Processor.

## Batches

### batch_10_applications/
- 5 PASS applications (strong credit, good DSCR, low LTV)
- 3 CONDITIONAL applications (marginal credit/DSCR)
- 2 FAIL applications (low credit, high LTV)

### batch_22_applications/
- 12 PASS applications
- 6 CONDITIONAL applications  
- 4 FAIL applications

### batch_35_applications/
- 18 PASS applications
- 10 CONDITIONAL applications
- 7 FAIL applications

## File Format
Each .txt file contains loan application data in key:value format:
```
applicant_name: John Smith
entity_name: John Smith LLC
loan_type: DSCR 1-4 Unit
loan_amount: 750000
property_address: 1234 Main St
city: Los Angeles
state: CA
fico_score: 720
dscr_ratio: 1.45
ltv_ratio: 0.72
```

## Usage
1. Navigate to Multi-Application section
2. Click "Demo: X Apps" buttons to load
3. Or upload files from these folders
