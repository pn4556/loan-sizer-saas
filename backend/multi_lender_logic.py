
"""
Multi-Lender Pricing Module for Loan Sizer
Integrates 3 lender pricing scenarios:
1. Lender A: IFC (RTL Pricing Tool v4)
2. Lender B: ICE/Guides (Bridge Sizer)
3. Lender C: Eastview/EV (EV RTL Sizer)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

class LenderName(str, Enum):
    IFC = "IFC"
    ICE = "ICE"
    EASTVIEW = "Eastview"

class LoanProgram(str, Enum):
    BRIDGE = "Bridge"
    RENOVATION = "Renovation"
    FIX_FLIP = "Fix & Flip"
    LIGHT_REHAB = "Light Rehab"
    HEAVY_REHAB = "Heavy Rehab"

class FICOTier(str, Enum):
    TIER_740_PLUS = "740+"
    TIER_700_739 = "700-739"
    TIER_680_699 = "680-699"
    TIER_660_679 = "660-679"
    BELOW_660 = "<660"

class BorrowerGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"

@dataclass
class LenderPricing:
    name: LenderName
    program: LoanProgram
    base_rate: float
    points: float
    max_ltv: float
    max_ltc: float
    max_ltarv: Optional[float]
    min_fico: int
    adjustments: Dict[str, float]
    notes: str

@dataclass
class PricingResult:
    lender: LenderName
    program: str
    rate: float
    points: float
    max_loan_amount: float
    ltv: float
    ltc: float
    ltarv: Optional[float]
    monthly_payment: float
    total_cost: float
    approval_confidence: str

class MultiLenderPricingEngine:
    """
    Multi-lender pricing comparison engine for 1-4 unit properties
    """
    
    def __init__(self):
        self.lenders = self._init_lender_configs()
    
    def _init_lender_configs(self) -> Dict[LenderName, Dict]:
        """Initialize lender pricing configurations"""
        return {
            LenderName.IFC: {
                "name": "IFC",
                "programs": {
                    LoanProgram.BRIDGE: {
                        "ltv_ranges": [(0.55, 0.70), (0.7001, 0.75), (0.7501, 0.80)],
                        "fico_tiers": {
                            FICOTier.TIER_740_PLUS: [0.0750, 0.0775, 0.0800],
                            FICOTier.TIER_700_739: [0.0750, 0.0775, 0.0800],
                            FICOTier.TIER_680_699: [0.0750, 0.0775, None],
                            FICOTier.TIER_660_679: [None, None, None],
                        },
                        "max_ltv": 0.80,
                        "points": 0.015,
                        "min_fico": 680,
                    },
                    LoanProgram.RENOVATION: {
                        "ltv_ranges": [(0.65, 0.70), (0.7001, 0.75), (0.7501, 0.80), (0.8001, 0.85), (0.8501, 0.90)],
                        "fico_tiers": {
                            FICOTier.TIER_740_PLUS: [0.0775, 0.0775, 0.0775, 0.07875, 0.0800, 0.0825],
                            FICOTier.TIER_700_739: [0.0775, 0.0775, 0.07875, 0.0800, 0.08125, 0.08375],
                            FICOTier.TIER_680_699: [0.0800, 0.0800, 0.0800, 0.08125, 0.0825, 0.0850],
                            FICOTier.TIER_660_679: [0.0825, 0.0825, 0.0825, 0.08375, 0.0850, None],
                        },
                        "max_ltv": 0.90,
                        "max_ltarv": 0.75,
                        "points": 0.02,
                        "min_fico": 660,
                    }
                },
                "adjustments": {
                    "cash_out": 0.005,
                    "fico_below_700": 0.0025,
                    "high_ltv": 0.005,
                }
            },
            LenderName.ICE: {
                "name": "ICE/Guides",
                "programs": {
                    LoanProgram.LIGHT_REHAB: {
                        "base_rate": 0.0875,
                        "points": 0.005,
                        "max_ltv": 0.90,
                        "max_ltc": 0.90,
                        "max_ltarv": 0.75,
                        "min_fico": 680,
                    },
                    LoanProgram.BRIDGE: {
                        "base_rate": 0.0875,
                        "points": 0.0075,
                        "max_ltv": 0.85,
                        "max_ltc": 0.85,
                        "min_fico": 680,
                    },
                    LoanProgram.HEAVY_REHAB: {
                        "base_rate": 0.0900,
                        "points": 0.0075,
                        "max_ltv": 0.85,
                        "max_ltc": 0.85,
                        "max_ltarv": 0.70,
                        "min_fico": 700,
                    }
                },
                "adjustments": {
                    "midstream": 0.0025,
                    "cashout": 0.005,
                    "loan_size_1_5_2_5m": {"rate": 0.005, "points": 0.005},
                    "loan_size_over_2_5m": {"rate": 0.01, "points": 0.0075},
                    "multifamily_mixed_use": {"rate": 0.01, "points": 0.005},
                    "fico_below_700": 0.0025,
                    "ltv_under_75_exp_3_plus": -0.005,
                    "institutional_10_plus": -0.005,
                    "max_buydown": 0.0075,
                }
            },
            LenderName.EASTVIEW: {
                "name": "Eastview",
                "programs": {
                    LoanProgram.FIX_FLIP: {
                        "grades": {
                            BorrowerGrade.A_PLUS: {"max_ltv": 0.90, "max_ltc": 0.90, "max_ltarv": 0.75, "min_rate": 0.0925},
                            BorrowerGrade.A: {"max_ltv": 0.85, "max_ltc": 0.85, "max_ltarv": 0.70, "min_rate": 0.0950},
                            BorrowerGrade.B: {"max_ltv": 0.825, "max_ltc": 0.825, "max_ltarv": 0.65, "min_rate": 0.0975},
                            BorrowerGrade.C: {"max_ltv": 0.75, "max_ltc": 0.75, "max_ltarv": 0.60, "min_rate": 0.1025},
                        },
                        "points": 0.015,
                        "min_fico": 660,
                    },
                    LoanProgram.BRIDGE: {
                        "grades": {
                            BorrowerGrade.A_PLUS: {"max_ltv": 0.825, "max_ltc": 0.825, "min_rate": 0.0925},
                            BorrowerGrade.A: {"max_ltv": 0.80, "max_ltc": 0.80, "min_rate": 0.0950},
                            BorrowerGrade.B: {"max_ltv": 0.80, "max_ltc": 0.80, "min_rate": 0.0975},
                            BorrowerGrade.C: {"max_ltv": 0.75, "max_ltc": 0.75, "min_rate": 0.1025},
                        },
                        "points": 0.015,
                        "min_fico": 660,
                    }
                },
                "adjustments": {
                    "cash_out": 0.0025,
                    "refinance_no_cash_out": -0.0025,
                }
            }
        }
    
    def calculate_borrower_grade(self, fico: int, experience: int) -> BorrowerGrade:
        """Calculate borrower grade based on FICO and experience"""
        # Credit score points
        if fico >= 700:
            credit_points = 3
        elif fico >= 680:
            credit_points = 1
        else:
            credit_points = 0
        
        # Experience points
        if experience >= 10:
            exp_points = 7
        elif experience >= 3:
            exp_points = 5
        elif experience >= 0:
            exp_points = 1
        else:
            exp_points = 0
        
        total_score = credit_points + exp_points
        
        if total_score >= 7:
            return BorrowerGrade.A_PLUS
        elif total_score >= 5:
            return BorrowerGrade.A
        elif total_score >= 2:
            return BorrowerGrade.B
        else:
            return BorrowerGrade.C
    
    def get_fico_tier(self, fico: int) -> FICOTier:
        """Determine FICO tier"""
        if fico >= 740:
            return FICOTier.TIER_740_PLUS
        elif fico >= 700:
            return FICOTier.TIER_700_739
        elif fico >= 680:
            return FICOTier.TIER_680_699
        elif fico >= 660:
            return FICOTier.TIER_660_679
        else:
            return FICOTier.BELOW_660
    
    def calculate_ifc_pricing(self, as_is_value: float, arv: float, purchase_price: float,
                              rehab_budget: float, fico: int, program: LoanProgram,
                              loan_purpose: str = "purchase") -> Optional[PricingResult]:
        """Calculate IFC pricing"""
        config = self.lenders[LenderName.IFC]["programs"][program]
        fico_tier = self.get_fico_tier(fico)
        
        if fico < config["min_fico"]:
            return None
        
        # Determine LTV range
        ltv = 0.75  # Default
        rate_index = 1  # Default middle tier
        
        fico_rates = config["fico_tiers"].get(fico_tier)
        if not fico_rates or fico_rates[rate_index] is None:
            return None
        
        base_rate = fico_rates[rate_index]
        points = config["points"]
        
        # Calculate max loan
        max_ltv_loan = as_is_value * config["max_ltv"]
        max_ltc_loan = (purchase_price + rehab_budget) * config.get("max_ltc", config["max_ltv"])
        
        if program == LoanProgram.RENOVATION:
            max_ltarv_loan = arv * config["max_ltarv"]
            max_loan = min(max_ltv_loan, max_ltc_loan, max_ltarv_loan)
            ltarv = max_loan / arv if arv > 0 else 0
        else:
            max_loan = min(max_ltv_loan, max_ltc_loan)
            ltarv = None
        
        ltv = max_loan / as_is_value if as_is_value > 0 else 0
        ltc = max_loan / (purchase_price + rehab_budget) if (purchase_price + rehab_budget) > 0 else 0
        
        # Apply adjustments
        rate = base_rate
        if loan_purpose == "cash_out":
            rate += self.lenders[LenderName.IFC]["adjustments"]["cash_out"]
        
        monthly_payment = max_loan * rate / 12
        total_cost = max_loan * points + (monthly_payment * 12)
        
        return PricingResult(
            lender=LenderName.IFC,
            program=program.value,
            rate=rate,
            points=points,
            max_loan_amount=max_loan,
            ltv=ltv,
            ltc=ltc,
            ltarv=ltarv,
            monthly_payment=monthly_payment,
            total_cost=total_cost,
            approval_confidence="High" if fico >= 700 else "Medium"
        )
    
    def calculate_ice_pricing(self, as_is_value: float, arv: float, purchase_price: float,
                             rehab_budget: float, fico: int, program: LoanProgram,
                             experience: int = 5, loan_purpose: str = "purchase",
                             is_institutional: bool = False) -> Optional[PricingResult]:
        """Calculate ICE/Guides pricing"""
        if program not in self.lenders[LenderName.ICE]["programs"]:
            return None
        
        config = self.lenders[LenderName.ICE]["programs"][program]
        
        if fico < config["min_fico"]:
            return None
        
        rate = config["base_rate"]
        points = config["points"]
        
        # Apply adjustments
        adjustments = self.lenders[LenderName.ICE]["adjustments"]
        
        if loan_purpose == "cash_out":
            rate += adjustments["cashout"]
        
        if fico < 700:
            rate += adjustments["fico_below_700"]
        
        if is_institutional and experience >= 10:
            rate += adjustments["institutional_10_plus"]
        
        # Calculate max loan
        max_ltv_loan = as_is_value * config["max_ltv"]
        max_ltc_loan = (purchase_price + rehab_budget) * config["max_ltc"]
        
        max_loan = min(max_ltv_loan, max_ltc_loan)
        ltarv = None
        
        if "max_ltarv" in config:
            max_ltarv_loan = arv * config["max_ltarv"]
            max_loan = min(max_loan, max_ltarv_loan)
            ltarv = max_loan / arv if arv > 0 else 0
        
        ltv = max_loan / as_is_value if as_is_value > 0 else 0
        ltc = max_loan / (purchase_price + rehab_budget) if (purchase_price + rehab_budget) > 0 else 0
        
        monthly_payment = max_loan * rate / 12
        total_cost = max_loan * points + (monthly_payment * 12)
        
        return PricingResult(
            lender=LenderName.ICE,
            program=program.value,
            rate=rate,
            points=points,
            max_loan_amount=max_loan,
            ltv=ltv,
            ltc=ltc,
            ltarv=ltarv,
            monthly_payment=monthly_payment,
            total_cost=total_cost,
            approval_confidence="High" if experience >= 5 else "Medium"
        )
    
    def calculate_eastview_pricing(self, as_is_value: float, arv: float, purchase_price: float,
                                   rehab_budget: float, fico: int, program: LoanProgram,
                                   experience: int = 5, loan_purpose: str = "purchase") -> Optional[PricingResult]:
        """Calculate Eastview pricing"""
        if program not in self.lenders[LenderName.EASTVIEW]["programs"]:
            return None
        
        grade = self.calculate_borrower_grade(fico, experience)
        config = self.lenders[LenderName.EASTVIEW]["programs"][program]
        grade_config = config["grades"][grade]
        
        if fico < config["min_fico"]:
            return None
        
        rate = grade_config["min_rate"]
        points = config["points"]
        
        # Calculate max loan
        max_ltv_loan = as_is_value * grade_config["max_ltv"]
        max_ltc_loan = (purchase_price + rehab_budget) * grade_config["max_ltc"]
        
        max_loan = min(max_ltv_loan, max_ltc_loan)
        ltarv = None
        
        if "max_ltarv" in grade_config:
            max_ltarv_loan = arv * grade_config["max_ltarv"]
            max_loan = min(max_loan, max_ltarv_loan)
            ltarv = max_loan / arv if arv > 0 else 0
        
        ltv = max_loan / as_is_value if as_is_value > 0 else 0
        ltc = max_loan / (purchase_price + rehab_budget) if (purchase_price + rehab_budget) > 0 else 0
        
        # Adjustments
        if loan_purpose == "cash_out":
            rate += 0.0025
        elif loan_purpose == "refinance":
            rate -= 0.0025
        
        monthly_payment = max_loan * rate / 12
        total_cost = max_loan * points + (monthly_payment * 12)
        
        return PricingResult(
            lender=LenderName.EASTVIEW,
            program=f"{program.value} ({grade.value})",
            rate=rate,
            points=points,
            max_loan_amount=max_loan,
            ltv=ltv,
            ltc=ltc,
            ltarv=ltarv,
            monthly_payment=monthly_payment,
            total_cost=total_cost,
            approval_confidence="High" if grade in [BorrowerGrade.A_PLUS, BorrowerGrade.A] else "Medium"
        )
    
    def compare_all_lenders(self, as_is_value: float, arv: float, purchase_price: float,
                           rehab_budget: float, fico: int, experience: int = 5,
                           loan_purpose: str = "purchase") -> List[PricingResult]:
        """Get pricing from all 3 lenders for comparison"""
        results = []
        
        # IFC - Renovation (most comparable)
        ifc_result = self.calculate_ifc_pricing(
            as_is_value, arv, purchase_price, rehab_budget, fico,
            LoanProgram.RENOVATION, loan_purpose
        )
        if ifc_result:
            results.append(ifc_result)
        
        # ICE - Light Rehab
        ice_result = self.calculate_ice_pricing(
            as_is_value, arv, purchase_price, rehab_budget, fico,
            LoanProgram.LIGHT_REHAB, experience, loan_purpose
        )
        if ice_result:
            results.append(ice_result)
        
        # Eastview - Fix & Flip
        ev_result = self.calculate_eastview_pricing(
            as_is_value, arv, purchase_price, rehab_budget, fico,
            LoanProgram.FIX_FLIP, experience, loan_purpose
        )
        if ev_result:
            results.append(ev_result)
        
        # Sort by rate (lowest first)
        results.sort(key=lambda x: x.rate)
        
        return results
    
    def get_best_rate(self, results: List[PricingResult]) -> Optional[PricingResult]:
        """Get the best rate option from comparison"""
        if not results:
            return None
        return results[0]
    
    def get_best_overall(self, results: List[PricingResult]) -> Optional[PricingResult]:
        """Get best overall value considering rate, points, and max loan"""
        if not results:
            return None
        
        # Score each option (lower is better)
        def score_result(r: PricingResult) -> float:
            return r.rate + r.points + (1 / (r.max_loan_amount / 1000000 + 1))
        
        return min(results, key=score_result)


# Pydantic models for API
from pydantic import BaseModel

class MultiLenderRequest(BaseModel):
    as_is_value: float
    arv: float
    purchase_price: float
    rehab_budget: float
    fico: int
    experience: int = 5
    loan_purpose: str = "purchase"
    property_type: str = "SFR"

class MultiLenderResponse(BaseModel):
    results: List[dict]
    best_rate: dict
    best_overall: dict
    summary: str


def format_currency(amount: float) -> str:
    """Format as currency"""
    return f"${amount:,.2f}"

def format_percent(value: float) -> str:
    """Format as percentage"""
    return f"{value * 100:.2f}%"
