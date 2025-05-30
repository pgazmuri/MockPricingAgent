import json
from typing import List, Dict, Any
from openai import OpenAI
from models import (
    Drug, Member, EligibilityResult, NDCSearchResult, 
    PlanBenefitStructure, MemberUtilization, FormularyResult,
    DrugCost, CouponResult, Coupon, PricingCalculation
)
import keys

class MockPBMServices:
    """Mock PBM services that use OpenAI API to generate realistic responses"""
    
    def __init__(self):
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
    def ndc_lookup(self, drug_name: str, dose: str = None, qty: int = None, dosage_form: str = None) -> NDCSearchResult:
        """Mock NDC lookup service that returns multiple matching drugs"""
        
        # Build search criteria for more specific results
        search_criteria = [f"Drug name: {drug_name}"]
        if dose:
            search_criteria.append(f"Dose/strength: {dose}")
        if dosage_form:
            search_criteria.append(f"Dosage form: {dosage_form}")
        if qty:
            search_criteria.append(f"Quantity needed: {qty}")
        
        search_description = ", ".join(search_criteria)
        
        prompt = f"""
        You are a pharmaceutical database API. Generate a realistic JSON response for an NDC lookup.
        Search criteria: {search_description}
        
        Return 3-5 realistic drugs that could match this search. Include both brand and generic options when appropriate.
        If specific dose or dosage form is provided, prioritize those in results.
        
        Each drug should have:
        - ndc: 11-digit NDC code (format: 12345-678-90)
        - name: Full drug name
        - strength: Dosage strength (e.g., "10 mg", "500 mg/5 mL")
        - dosage_form: Form (tablet, capsule, injection, cream, foam, liquid, etc.)
        - manufacturer: Pharmaceutical company
        - generic_name: Generic/active ingredient name
        - brand_name: Brand name (if applicable, null for generics)
        
        Make the results diverse and realistic. If searching for a specific drug like "metformin" or "lipitor",
        include multiple strengths and manufacturers.
        
        Do not just return a single drug unless it contains plausible details to identify an NDC.
        
        Response format:
        {{
            "drugs": [array of drug objects],
            "total_found": <total found>,
            "search_term": "{search_description}"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return NDCSearchResult(**result_json)
        except Exception as e:
            # Fallback with a simple example
            return NDCSearchResult(
                drugs=[
                    Drug(
                        ndc="12345-678-90",
                        name=f"{drug_name} {dose or '10 mg'} {dosage_form or 'tablet'} {qty or '30'} count",
                        strength="10 mg",
                        dosage_form="tablet",
                        manufacturer="Generic Pharma Co",
                        brand_name=None
                    )
                ],
                total_found=1,
                search_term=search_description
            )
    
    def check_eligibility(self, member_id: str, date_of_birth: str = None) -> EligibilityResult:
        """Mock eligibility check service"""
        prompt = f"""
        You are a PBM eligibility verification system. Generate a realistic response for member eligibility check.
        Member ID: {member_id}
        Date of Birth: {date_of_birth or "Not provided"}
        
        Generate realistic member information. The member should be eligible with active coverage.
        
        Response format:
        {{
            "is_eligible": true,
            "member_info": {{
                "member_id": "{member_id}",
                "first_name": "realistic_first_name",
                "last_name": "realistic_last_name", 
                "date_of_birth": "YYYY-MM-DD",
                "plan_id": "realistic_plan_id"
            }},
            "messages": ["Member is eligible and active"]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return EligibilityResult(**result_json)
        except Exception as e:
            return EligibilityResult(
                is_eligible=False,
                messages=[f"Error checking eligibility: {str(e)}"]
            )
    
    def get_plan_benefits(self, plan_id: str) -> PlanBenefitStructure:
        """Get detailed plan benefit structure"""
        prompt = f"""
        You are a PBM plan benefits service. Generate realistic plan benefit structure for plan ID: {plan_id}
        
        Generate a realistic pharmacy benefit plan with:
        - 4-tier formulary structure (Generic, Preferred Brand, Non-Preferred Brand, Specialty)
        - Realistic copays and coinsurance percentages
        - Annual deductible and out-of-pocket maximum
        - Current plan year (2025)
        
        Response format:
        {{
            "plan_id": "{plan_id}",
            "plan_name": "Realistic Plan Name",
            "plan_year": 2025,
            "deductible": 250.00,
            "out_of_pocket_max": 3000.00,
            "tier_1_copay": 10.00,
            "tier_1_coinsurance": null,
            "tier_2_copay": 30.00,
            "tier_2_coinsurance": null,
            "tier_3_copay": null,
            "tier_3_coinsurance": 0.40,
            "tier_4_copay": null,
            "tier_4_coinsurance": 0.25
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return PlanBenefitStructure(**result_json)
        except Exception as e:
            # Fallback
            return PlanBenefitStructure(
                plan_id=plan_id,
                plan_name="Standard Plan",
                plan_year=2025,
                deductible=250.0,
                out_of_pocket_max=3000.0,
                tier_1_copay=10.0,
                tier_2_copay=30.0,
                tier_3_coinsurance=0.40,
                tier_4_coinsurance=0.25
            )
    
    def get_member_utilization(self, member_id: str, plan_year: int = 2025) -> MemberUtilization:
        """Get member's current year utilization and spending"""
        prompt = f"""
        You are a PBM utilization tracking service. Generate realistic member utilization for:
        Member ID: {member_id}
        Plan Year: {plan_year}
        
        Generate realistic year-to-date spending and utilization. Make it varied - some members might be early in deductible, others may have met it.
        
        Response format:
        {{
            "member_id": "{member_id}",
            "plan_year": {plan_year},
            "deductible_met": 150.00,
            "out_of_pocket_met": 400.00,
            "total_paid_by_member": 400.00,
            "total_paid_by_plan": 1200.00,
            "prescription_count": 8
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return MemberUtilization(**result_json)
        except Exception as e:
            # Fallback
            return MemberUtilization(
                member_id=member_id,
                plan_year=plan_year,
                deductible_met=0.0,
                out_of_pocket_met=0.0,
                total_paid_by_member=0.0,
                total_paid_by_plan=0.0,
                prescription_count=0
            )
    
    def check_formulary(self, ndc: str, plan_id: str) -> FormularyResult:
        """Check if drug is on formulary and get tier information"""
        prompt = f"""
        You are a PBM formulary service. Check formulary status for:
        NDC: {ndc}
        Plan ID: {plan_id}
        
        Generate realistic formulary information including:
        - Coverage status (most drugs should be covered)
        - Tier placement (1=Generic, 2=Preferred Brand, 3=Non-Preferred Brand, 4=Specialty)
        - Any restrictions (prior auth, step therapy, quantity limits)
        - Alternative drugs if not covered
        
        Response format:
        {{
            "ndc": "{ndc}",
            "is_covered": true,
            "tier": 2,
            "prior_auth_required": false,
            "quantity_limits": null,
            "step_therapy_required": false,
            "formulary_alternatives": []
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return FormularyResult(**result_json)
        except Exception as e:
            # Fallback - assume covered, tier 2
            return FormularyResult(
                ndc=ndc,
                is_covered=True,
                tier=2,
                prior_auth_required=False,
                step_therapy_required=False,
                formulary_alternatives=[]
            )
    
    def get_drug_cost(self, ndc: str) -> DrugCost:
        """Get wholesale and negotiated drug costs"""
        prompt = f"""
        You are a PBM drug cost service. Provide realistic drug cost information for NDC: {ndc}
        
        Generate realistic pharmaceutical pricing including:
        - Wholesale/AWP price (what retail would charge)
        - Plan negotiated price (usually lower than wholesale)
        - Dispensing fee
        
        Make prices realistic for prescription drugs (typically $10-500 for most common drugs, higher for specialty).
        
        Response format:
        {{
            "ndc": "{ndc}",
            "wholesale_price": 125.50,
            "plan_negotiated_price": 89.25,
            "dispensing_fee": 2.50
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return DrugCost(**result_json)
        except Exception as e:
            # Fallback
            return DrugCost(
                ndc=ndc,
                wholesale_price=100.0,
                plan_negotiated_price=75.0,
                dispensing_fee=2.50
            )
    
    def check_coupons(self, ndc: str, member_id: str = None) -> CouponResult:
        """Check for available manufacturer coupons and discounts"""
        prompt = f"""
        You are a PBM coupon/discount service. Check for available discounts for:
        NDC: {ndc}
        Member ID: {member_id or "Not provided"}
        
        Generate realistic manufacturer coupons or discount programs. Not all drugs have coupons.
        Include variety like:
        - Manufacturer savings cards
        - Patient assistance programs
        - Pharmacy discount programs
        
        Response format:
        {{
            "ndc": "{ndc}",
            "available_coupons": [
                {{
                    "coupon_id": "MFG-001",
                    "name": "Manufacturer Savings Card",
                    "discount_type": "fixed",
                    "discount_value": 15.00,
                    "max_savings": 50.00,
                    "terms": "Save $15 per fill, max $50/month",
                    "eligible": true
                }}
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return CouponResult(**result_json)
        except Exception as e:
            # Fallback - no coupons
            return CouponResult(
                ndc=ndc,
                available_coupons=[]
            )
