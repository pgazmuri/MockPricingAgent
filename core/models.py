from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

class SearchMode(str, Enum):
    """Search mode for NDC lookup"""
    EXACT = "exact"
    SEARCH = "search"

class NDCLookupResult(BaseModel):
    """Individual drug result from NDC lookup"""
    ndc: str
    drug_name: str
    strength: str
    dosage_form: str
    brand_generic: str  # "brand" or "generic"
    match: float  # Match confidence score 0.0-1.0

class NDCLookupResponse(BaseModel):
    """Response from ndcLookup function"""
    result: List[NDCLookupResult]
    context: str

class RxPriceResult(BaseModel):
    """Comprehensive result from calculateRxPrice function"""
    # Basic pricing
    member_cost: Decimal
    plan_paid: Decimal
    pricing_basis: str  # e.g., "AWP", "MAC", "negotiated_rate"
    
    # Detailed cost breakdown
    drug_cost: Optional[Decimal] = None
    dispensing_fee: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    
    # Member benefit details
    copay: Optional[Decimal] = None
    coinsurance: Optional[float] = None
    deductible_applied: Optional[Decimal] = None
    oop_applied: Optional[Decimal] = None
    
    # Plan information
    formulary_tier: Optional[str] = None
    formulary_status: Optional[str] = None  # "covered", "prior_auth", "step_therapy"
    
    # Utilization tracking
    days_supply: Optional[int] = None
    quantity: Optional[int] = None
    refills_remaining: Optional[int] = None
    
    # Coupons and discounts
    coupon_eligible: Optional[bool] = None
    coupon_discount: Optional[Decimal] = None
    manufacturer_rebate: Optional[Decimal] = None
    
    # Member eligibility details
    coverage_effective_date: Optional[str] = None
    coverage_termination_date: Optional[str] = None
    
    # Additional context
    notes: Optional[str] = None
    warnings: Optional[List[str]] = None

    context: Optional[str] = None  # Additional context for the calculation

class RxPriceResponse(BaseModel):
    """Response from calculateRxPrice function"""
    result: RxPriceResult


class FormularyAlternativesResponse(BaseModel):
    """Response from getFormularyAlternatives function"""
    result: List[str]  # List of alternative NDCs
    context: str

# Legacy models for backwards compatibility
class Drug(BaseModel):
    """Represents a drug with its NDC and details"""
    ndc: str
    name: str
    strength: str
    dosage_form: str
    manufacturer: str
    brand_name: Optional[str] = None

class Member(BaseModel):
    """Represents a member/patient"""
    member_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    plan_id: str

class PlanBenefitStructure(BaseModel):
    """Detailed plan benefit structure"""
    plan_id: str
    plan_name: str
    plan_year: int
    deductible: float
    out_of_pocket_max: float
    
    # Tier structure
    tier_1_copay: Optional[float] = None  # Generic
    tier_1_coinsurance: Optional[float] = None
    
    tier_2_copay: Optional[float] = None  # Preferred brand
    tier_2_coinsurance: Optional[float] = None
    
    tier_3_copay: Optional[float] = None  # Non-preferred brand
    tier_3_coinsurance: Optional[float] = None
    
    tier_4_copay: Optional[float] = None  # Specialty
    tier_4_coinsurance: Optional[float] = None

class MemberUtilization(BaseModel):
    """Member's current year utilization"""
    member_id: str
    plan_year: int
    deductible_met: float
    out_of_pocket_met: float
    total_paid_by_member: float
    total_paid_by_plan: float
    prescription_count: int

class FormularyResult(BaseModel):
    """Formulary coverage information"""
    ndc: str
    is_covered: bool
    tier: Optional[int] = None
    prior_auth_required: bool = False
    quantity_limits: Optional[Dict[str, Any]] = None
    step_therapy_required: bool = False
    formulary_alternatives: List[str] = []

class DrugCost(BaseModel):
    """Drug cost information"""
    ndc: str
    wholesale_price: float  # AWP or similar
    plan_negotiated_price: float  # What plan actually pays
    dispensing_fee: float
    
class Coupon(BaseModel):
    """Manufacturer or other discount coupon"""
    coupon_id: str
    name: str
    discount_type: str  # "fixed", "percentage", "copay_card"
    discount_value: float
    max_savings: Optional[float] = None
    terms: str
    eligible: bool = True

class CouponResult(BaseModel):
    """Available coupons for a drug"""
    ndc: str
    available_coupons: List[Coupon]

class PricingCalculation(BaseModel):
    """Detailed pricing calculation breakdown"""
    ndc: str
    drug_name: str
    quantity: int
    days_supply: int
    
    # Base costs
    wholesale_price: float
    plan_negotiated_price: float
    dispensing_fee: float
    
    # Plan details
    tier: int
    formulary_covered: bool
    
    # Member status
    deductible_remaining: float
    oop_max_remaining: float
    
    # Calculations
    drug_cost_before_benefits: float
    deductible_applies: float
    after_deductible_cost: float
    member_copay_coinsurance: float
    plan_pays: float
    member_pays_before_coupons: float
    
    # Coupons applied
    coupons_applied: List[Coupon]
    total_coupon_savings: float
    
    # Final amounts
    final_member_cost: float
    calculation_notes: List[str]

class EligibilityResult(BaseModel):
    """Represents eligibility check result"""
    is_eligible: bool
    member_info: Optional[Member] = None
    messages: List[str] = []

class NDCSearchResult(BaseModel):
    """Represents NDC search results"""
    drugs: List[Drug]
    total_found: int
    search_term: str
