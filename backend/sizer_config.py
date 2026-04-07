"""
Loan Sizer Configuration
Custom cell mappings for: Multi and Mixed-Use Term Sizer 3.18.2026
"""

# Cell mappings for the SIZER tab
# Based on analysis of: Multi and Mixed-Use Term Sizer 3.18.2026 1.xlsx

SIZER_CELL_MAPPINGS = {
    # Property Details
    'C5': 'property_type',        # Property Type (e.g., Multifamily)
    'C6': 'asset_class',          # Asset Class (e.g., C)
    'C7': 'square_footage',       # Square Footage
    'C8': 'units',                # Units
    'C9': 'unit_size',            # Unit Size (calculated: C7/C8)
    'C10': 'occupancy',           # Occupancy
    'C11': 'rent_stabilized',     # Rent Stabilized? (Yes/No)
    
    # Address
    'E5': 'address',              # Address
    'E6': 'city',                 # City
    'E7': 'state',                # State (e.g., KY)
    'E8': 'zip_code',             # Zip Code
    'E9': 'city_population',      # City Population (>=250K)
    
    # Financial - Property
    'G5': 'estimated_value',      # Estimated Value
    'G6': 'purchase_price',       # Purchase Price
    
    # Financial - Loan
    'J4': 'loan_amount',          # Loan Amount
    'I8': 'note_type',            # Note Type
    'I10': 'points_to_lender',    # Points to Lender
    'M7': 'credit_score',         # Credit / FICO (Middle score)
    'E48': 'interest_rate',       # Minimum Rate / Interest Rate
    
    # Calculated fields (read-only)
    'E40': 'final_dscr',          # Final DSCR
    'E45': 'ltv_ratio',           # Overwritten LTV
    'L5': 'recourse_status',      # Recourse Status
}

# Programs to evaluate (sheet names in workbook)
PROGRAM_SHEETS = [
    'INSURANCE PROGRAM',
    'SHORT TERM SALE',
    'DEEPHAVEN',
    'BLACKSTONE',
    'CHURCHILL',
    'VERUS',
    'CMBS TESTS'
]

# Pass/Fail check cells in SIZER tab
# These cells contain formulas that reference program sheets
PROGRAM_STATUS_CELLS = {
    'E10': 'state_status',        # =IFERROR('INSURANCE PROGRAM'!P6,"--")
    'E40': 'final_dscr_check',    # Final DSCR & Max Loan Amount Check
    # Additional program status cells can be mapped here
}

# Input validation rules
VALIDATION_RULES = {
    'units': {'min': 1, 'max': 1000, 'type': int},
    'estimated_value': {'min': 50000, 'max': 100000000, 'type': float},
    'purchase_price': {'min': 50000, 'max': 100000000, 'type': float},
    'loan_amount': {'min': 50000, 'max': 100000000, 'type': float},
    'credit_score': {'min': 300, 'max': 850, 'type': int},
    'points_to_lender': {'min': 0, 'max': 10, 'type': float},
    'interest_rate': {'min': 1.0, 'max': 20.0, 'type': float},
}

# Required fields for a complete application
REQUIRED_FIELDS = [
    'units',
    'address',
    'city',
    'state',
    'zip_code',
    'estimated_value',
    'purchase_price',
    'loan_amount',
    'note_type',
    'credit_score'
]

# State abbreviations (for validation)
US_STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR'
]
