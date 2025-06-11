import json
import random
from typing import List, Dict, Any
from decimal import Decimal
from openai import OpenAI
from core.models import (
    NDCLookupResponse, NDCLookupResult, SearchMode,
    RxPriceResponse, RxPriceResult, FormularyAlternativesResponse,
    # Legacy models for backwards compatibility
    Drug, Member, EligibilityResult, NDCSearchResult, 
    PlanBenefitStructure, MemberUtilization, FormularyResult,
    DrugCost, CouponResult, Coupon, PricingCalculation
)
import config.keys as keys

class MockPBMServices:
    """Simplified mock PBM services with only the three core functions"""
    
    def __init__(self):
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
    
    def ndc_lookup(self, query: str, mode: SearchMode = SearchMode.SEARCH) -> NDCLookupResponse:
        """
        Mock NDC lookup service
        Args:
            query: Search string (drug name, NDC, etc.)
            mode: "exact" for exact matches, "search" for fuzzy matching
        """
        
        prompt = f"""
        You are a pharmaceutical database API. Generate a realistic JSON response for an NDC lookup.
        Query: "{query}"
        Search mode: {mode}
        
        Return 3-6 realistic drugs that could match this query. For "exact" mode, prioritize exact matches.
        For "search" mode, include related drugs and alternatives.
        
        Each drug should have:
        - ndc: 11-digit NDC code (format: 12345-678-90)
        - drug_name: Full drug name including strength
        - strength: Dosage strength (e.g., "10 mg", "500 mg/5 mL")
        - dosage_form: Form (tablet, capsule, injection, cream, etc.)
        - brand_generic: Either "brand" or "generic"
        - match: Float between 0.0-1.0 indicating match confidence
        
        Make results realistic. Include both brand and generic when appropriate.
        
        Return only the JSON array of drugs, no other text:
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            drugs_data = json.loads(response_text)
            
            # Convert to our model
            results = []
            for drug_data in drugs_data:
                result = NDCLookupResult(
                    ndc=drug_data.get('ndc', ''),
                    drug_name=drug_data.get('drug_name', ''),
                    strength=drug_data.get('strength', ''),
                    dosage_form=drug_data.get('dosage_form', ''),
                    brand_generic=drug_data.get('brand_generic', 'generic'),
                    match=drug_data.get('match', 0.8)
                )
                results.append(result)
            
            context = f"NDC lookup performed for '{query}' using {mode} mode. Found {len(results)} results."
            
            return NDCLookupResponse(result=results, context=context)
            
        except Exception as e:
            # Fallback with realistic mock data
            return self._fallback_ndc_lookup(query, mode)
    
    def _fallback_ndc_lookup(self, query: str, mode: SearchMode) -> NDCLookupResponse:
        """Fallback NDC lookup with realistic mock data"""
        
        # Mock data based on common queries
        mock_results = {
            "metformin": [
                NDCLookupResult(ndc="00093-7267-01", drug_name="Metformin HCl 500 mg", strength="500 mg", 
                               dosage_form="tablet", brand_generic="generic", match=0.95),
                NDCLookupResult(ndc="00093-7268-01", drug_name="Metformin HCl 850 mg", strength="850 mg", 
                               dosage_form="tablet", brand_generic="generic", match=0.90),
                NDCLookupResult(ndc="00003-0284-11", drug_name="Glucophage 500 mg", strength="500 mg", 
                               dosage_form="tablet", brand_generic="brand", match=0.85)
            ],
            "lipitor": [
                NDCLookupResult(ndc="00071-0155-23", drug_name="Lipitor 20 mg", strength="20 mg", 
                               dosage_form="tablet", brand_generic="brand", match=0.98),
                NDCLookupResult(ndc="00093-7270-01", drug_name="Atorvastatin 20 mg", strength="20 mg", 
                               dosage_form="tablet", brand_generic="generic", match=0.85)
            ],
            "advair": [
                NDCLookupResult(ndc="00173-0715-20", drug_name="Advair Diskus 250/50", strength="250/50 mcg", 
                               dosage_form="inhalation powder", brand_generic="brand", match=0.95)
            ]
        }
        
        # Find best match
        query_lower = query.lower()
        results = []
        
        for drug_name, drug_results in mock_results.items():
            if drug_name in query_lower or query_lower in drug_name:
                results.extend(drug_results)
        
        # If no matches, provide generic examples
        if not results:
            results = [
                NDCLookupResult(ndc="12345-678-90", drug_name=f"Generic Drug A", strength="10 mg", 
                               dosage_form="tablet", brand_generic="generic", match=0.6),
                NDCLookupResult(ndc="12345-678-91", drug_name=f"Brand Drug B", strength="20 mg", 
                               dosage_form="capsule", brand_generic="brand", match=0.5)        ]
        
        context = f"Fallback NDC lookup for '{query}' using {mode} mode. Found {len(results)} results."
        return NDCLookupResponse(result=results, context=context)
    
    def calculate_rx_price(self, ndc: str, member_id: str) -> RxPriceResponse:
        """
        Mock prescription price calculation using OpenAI to generate comprehensive response
        Args:
            ndc: National Drug Code
            pharmacy_npi: Pharmacy NPI number
            member_id: Member ID
            fill_date: Fill date (YYYY-MM-DD format)
        """
        
        # Create a comprehensive prompt for OpenAI to generate realistic pricing details
        prompt = f"""
        You are a PBM (Pharmacy Benefit Manager) pricing system. Generate a comprehensive, realistic prescription pricing response for the following request:

        NDC: {ndc}
        Member ID: {member_id}

        Generate a detailed JSON response that includes:
        1. Basic pricing (member_cost, plan_paid, pricing_basis)
        2. Detailed cost breakdown (drug_cost, dispensing_fee, total_cost)
        3. Member benefit details (copay, coinsurance, deductible_applied, oop_applied)
        4. Plan information (formulary_tier, formulary_status)
        5. Utilization details (days_supply, quantity, refills_remaining)
        6. Coupon/discount information (coupon_eligible, coupon_discount, manufacturer_rebate)
        7. Member eligibility (coverage_effective_date, coverage_termination_date)
        8. Additional context (Detailed explanation of how this pricing was calculated, including member plan benefits, formulary status, cost breakdown methodology, any applied discounts or rebates, and specific calculation steps used to arrive at the final member cost and plan paid amounts.)       
        Use realistic pharmaceutical pricing:
        - Generic drugs: $5-50 member cost
        - Brand drugs: $25-200 member cost
        - Specialty drugs: $100-500+ member cost
        - Include realistic dispensing fees ($1-3)
        - Use common formulary tiers (Tier 1-4)
        - Include realistic days supply (30, 60, 90 days)
        - Consider member benefits and plan structures

        Return ONLY a valid JSON object with the following structure (include a detailed context field):
        {{
            "member_cost": 25.00,
            "plan_paid": 75.00,
            "pricing_basis": "AWP-15%",
            "drug_cost": 95.00,
            "dispensing_fee": 2.50,
            "total_cost": 100.00,
            "copay": 25.00,
            "coinsurance": null,
            "deductible_applied": 0.00,
            "oop_applied": 25.00,
            "formulary_tier": "Tier 2",
            "formulary_status": "covered",
            "days_supply": 30,
            "quantity": 30,
            "refills_remaining": 5,
            "coupon_eligible": true,
            "coupon_discount": 10.00,
            "manufacturer_rebate": 5.00,
            "coverage_effective_date": "2024-01-01",
            "coverage_termination_date": "2024-12-31",
            "notes": "Standard formulary coverage with copay",
            "warnings": ["Check for drug interactions", "Requires prior authorization for quantities over 30 days"],
            "context": "Plan Price: $100. Drug is Tier 2 with a copay of $30. However, member has a $500 deductible, of which $200 has been met, so no copay or coinsurance applies. The dispensing fee is $2.50. The total cost includes a coupon discount of $10 applied to the member cost. $100 minus $10 coupon discount plus $2.50 dispensing fee equals $92.50 paid by the member."
        }}
        """
        
        try:
            # Use OpenAI to generate comprehensive pricing response
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a PBM pricing system API. Generate realistic pharmaceutical pricing data in JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            # Parse the OpenAI response
            openai_response = response.choices[0].message.content.strip()
              # Clean up the response (remove any markdown formatting)
            if openai_response.startswith("```json"):
                openai_response = openai_response[7:]
            if openai_response.endswith("```"):
                openai_response = openai_response[:-3]
            
            pricing_data = json.loads(openai_response)
            
            # Convert to our model format
            result = RxPriceResult(
                member_cost=Decimal(str(pricing_data.get("member_cost", 25.00))),
                plan_paid=Decimal(str(pricing_data.get("plan_paid", 75.00))),
                pricing_basis=pricing_data.get("pricing_basis", "AWP-15%"),
                drug_cost=Decimal(str(pricing_data.get("drug_cost", 95.00))) if pricing_data.get("drug_cost") else None,
                dispensing_fee=Decimal(str(pricing_data.get("dispensing_fee", 2.50))) if pricing_data.get("dispensing_fee") else None,
                total_cost=Decimal(str(pricing_data.get("total_cost", 100.00))) if pricing_data.get("total_cost") else None,
                copay=Decimal(str(pricing_data.get("copay", 25.00))) if pricing_data.get("copay") else None,
                coinsurance=pricing_data.get("coinsurance"),
                deductible_applied=Decimal(str(pricing_data.get("deductible_applied", 0.00))) if pricing_data.get("deductible_applied") is not None else None,
                oop_applied=Decimal(str(pricing_data.get("oop_applied", 25.00))) if pricing_data.get("oop_applied") is not None else None,
                formulary_tier=pricing_data.get("formulary_tier"),
                formulary_status=pricing_data.get("formulary_status"),
                days_supply=pricing_data.get("days_supply"),
                quantity=pricing_data.get("quantity"),
                refills_remaining=pricing_data.get("refills_remaining"),
                coupon_eligible=pricing_data.get("coupon_eligible"),
                coupon_discount=Decimal(str(pricing_data.get("coupon_discount", 0.00))) if pricing_data.get("coupon_discount") else None,
                manufacturer_rebate=Decimal(str(pricing_data.get("manufacturer_rebate", 0.00))) if pricing_data.get("manufacturer_rebate") else None,
                coverage_effective_date=pricing_data.get("coverage_effective_date"),
                coverage_termination_date=pricing_data.get("coverage_termination_date"),
                notes=pricing_data.get("notes"),
                warnings=pricing_data.get("warnings", []),
                context = pricing_data.get("context", f"Comprehensive price calculated for NDC {ndc} at pharmacy for member {member_id}. Generated using AI-powered pricing engine with full benefit analysis.")
            )
            
            print("=== OpenAI Pricing Response ===")
            print(openai_response)  # Debug: print the raw OpenAI response
            print("=== End OpenAI Pricing Response ===")
            # Use the context generated by OpenAI, which includes detailed calculation explanation
            
        except Exception as e:
            # Fallback to basic pricing if OpenAI fails
            print(f"OpenAI pricing generation failed: {e}. Using fallback pricing.")
            
            # Simulate pricing logic with realistic variations
            base_drug_cost = random.uniform(15.0, 500.0)
            dispensing_fee = random.uniform(1.50, 3.00)
            total_cost = base_drug_cost + dispensing_fee
            
            # Simulate member plan benefits
            if "DEMO" in member_id.upper():
                coinsurance = 0.20
                copay = min(10.0, base_drug_cost * 0.1)
            else:
                coinsurance = random.choice([0.10, 0.20, 0.25, 0.30])
                copay = random.uniform(5.0, 50.0)
            
            member_cost = min(copay, base_drug_cost * coinsurance)
            plan_paid = total_cost - member_cost
            
            # Ensure reasonable minimums
            member_cost = max(member_cost, 1.0)
            plan_paid = max(plan_paid, 0.0)
            
            result = RxPriceResult(
                member_cost=Decimal(str(round(member_cost, 2))),
                plan_paid=Decimal(str(round(plan_paid, 2))),
                pricing_basis=random.choice(["AWP-15%", "MAC", "negotiated_rate", "WAC+2%"]),
                drug_cost=Decimal(str(round(base_drug_cost, 2))),
                dispensing_fee=Decimal(str(round(dispensing_fee, 2))),
                total_cost=Decimal(str(round(total_cost, 2))),
                copay=Decimal(str(round(copay, 2))),
                coinsurance=coinsurance,
                formulary_tier=random.choice(["Tier 1", "Tier 2", "Tier 3", "Tier 4"]),
                formulary_status="covered",
                days_supply=random.choice([30, 60, 90]),
                quantity=random.randint(30, 90),
                refills_remaining=random.randint(0, 5),
                coupon_eligible=random.choice([True, False]),
                notes="Fallback pricing calculation",
                warnings=["Generated using fallback pricing system"],
                context = f"Fallback price calculated for NDC {ndc} at pharmacy {pharmacy_npi} for member {member_id} on {fill_date}."
            )
            
        
        return RxPriceResponse(result=result)
    
    def get_formulary_alternatives(self, plan_id: str, ndc: str) -> FormularyAlternativesResponse:
        """
        Mock formulary alternatives lookup
        Args:
            plan_id: Plan identifier
            ndc: NDC to find alternatives for
        """
        
        # Mock alternative NDCs based on common therapeutic classes
        alternative_map = {
            "00093-7267-01": ["00093-7268-01", "00003-0284-11", "60505-0234-01"],  # Metformin alternatives
            "00071-0155-23": ["00093-7270-01", "16729-0123-01", "43063-0456-12"],  # Statin alternatives
            "00173-0715-20": ["00078-0123-45", "54868-0789-01"]  # Inhaler alternatives
        }
        
        # Get alternatives or generate some
        alternatives = alternative_map.get(ndc, [])
        
        if not alternatives:
            # Generate some mock alternatives
            base_ndc_parts = ndc.split('-')
            if len(base_ndc_parts) == 3:
                base_prefix = base_ndc_parts[0]
                alternatives = [
                    f"{base_prefix}-{random.randint(1000,9999):04d}-{random.randint(10,99):02d}" 
                    for _ in range(random.randint(1, 4))
                ]
        context = f"Formulary alternatives found for NDC {ndc} under plan {plan_id}. Found {len(alternatives)} alternatives."
        
        return FormularyAlternativesResponse(result=alternatives, context=context)
