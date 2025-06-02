"""
Specialized Benefits Agent

Handles plan details, coverage rules, prior authorizations, and benefit questions.
Can hand off to other agents when needed (e.g., pricing, authentication, clinical).
Now uses OpenAI Chat Completions API with streaming instead of Assistants API.
"""

import json
import time
from typing import Dict, Any, Optional, Iterator, List
from agent_coordinator import BaseAgent, AgentType
from openai import OpenAI
from shared_prompts import get_shared_context_awareness, get_shared_handoff_rules


class BenefitsAgent(BaseAgent):
    """Specialized agent for plan benefits and coverage information"""
    
    def __init__(self, client: OpenAI, model: str = "gpt-4.1"):
        super().__init__(client, AgentType.BENEFITS, model=model)
        
        # Set agent-specific properties
        self.agent_name = "Benefits"
        self.agent_emoji = "📋"
        
        # Initialize tools and system prompt
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
    def get_system_prompt(self) -> str:
        """Get the system prompt for the benefits agent"""
        # Base benefits agent prompt
        base_prompt = """
You are a specialized benefits and coverage expert for a healthcare insurance system.
Your expertise is in plan details, coverage rules, prior authorizations, and benefit explanations.
Answer benefit questions clearly and concisely.
Use the 'request_handoff' function only when truly outside your expertise.
"""
        # Shared context awareness and handoff rules
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.BENEFITS)
        # Benefits-specific clarification rules
        clarification_rules = """
CLARIFICATION RULES:
- If receiving a handoff from Pricing agent about specific dollar amounts, answer directly using provided pricing context.
- Questions about "how much I pay", copay, deductible status, or out-of-pocket are your domain; do not hand off.
- Only hand off specific pricing calculations you cannot derive from given context.
"""
        return base_prompt + context_awareness + handoff_rules + clarification_rules
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the benefits agent"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_plan_details",
                    "description": "Get detailed plan information for a member",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "plan_id": {"type": "string", "description": "Specific plan ID (optional)"}
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_coverage",
                    "description": "Check coverage for a specific drug or service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "ndc": {"type": "string", "description": "Drug NDC (optional)"},
                            "service_code": {"type": "string", "description": "Service code (optional)"},
                            "drug_name": {"type": "string", "description": "Drug name (optional)"}
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_prior_auth",
                    "description": "Check prior authorization status and requirements",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "ndc": {"type": "string", "description": "Drug NDC"},
                            "pa_id": {"type": "string", "description": "Prior auth ID (optional)"}
                        },
                        "required": ["member_id", "ndc"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_formulary_details",
                    "description": "Get detailed formulary information including tiers and restrictions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "plan_id": {"type": "string", "description": "Plan ID"},
                            "drug_class": {"type": "string", "description": "Drug class (optional)"},
                            "ndc": {"type": "string", "description": "Specific drug NDC (optional)"}
                        },
                        "required": ["plan_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_utilization_summary",
                    "description": "Get member's benefit utilization summary",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "plan_year": {"type": "integer", "description": "Plan year", "default": 2025}
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_step_therapy",
                    "description": "Check step therapy requirements for a drug",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "ndc": {"type": "string", "description": "Drug NDC"},
                            "plan_id": {"type": "string", "description": "Plan ID"}
                        },
                        "required": ["member_id", "ndc", "plan_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "request_handoff",
                    "description": "Hand off to another specialized agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_type": {
                                "type": "string",
                                "enum": ["authentication", "pricing", "pharmacy", "clinical"],
                                "description": "Which agent to hand off to"
                            },
                            "reason": {"type": "string", "description": "Why handoff is needed"},
                            "context_summary": {"type": "string", "description": "Context for receiving agent"}
                        },
                        "required": ["agent_type", "reason", "context_summary"]
                    }
                }
            }
        ]
    
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls with mock data"""
        try:
            if function_name == "get_plan_details":
                member_id = function_args.get("member_id", "")
                plan_id = function_args.get("plan_id")
                
                print(f"📋 Getting plan details for member {member_id}")
                
                mock_result = {
                    "plan_id": plan_id or "HEALTH_PLUS_2025",
                    "plan_name": "HealthPlus Premier Plan",
                    "plan_type": "PDP",
                    "effective_date": "2025-01-01",
                    "formulary": "Comprehensive Formulary 2025",
                    "benefits": {
                        "deductible": {
                            "medical": 250.00,
                            "pharmacy": 100.00
                        },
                        "out_of_pocket_maximum": 3000.00,
                        "copays": {
                            "tier_1_generic": 10.00,
                            "tier_2_preferred_brand": 35.00,
                            "tier_3_non_preferred": 70.00,
                            "tier_4_specialty": 150.00
                        },
                        "coinsurance_after_deductible": "20%"
                    }
                }
                
                print(f"📋 Plan Details: {mock_result['plan_name']}")
                return json.dumps(mock_result)
                
            elif function_name == "check_coverage":
                member_id = function_args.get("member_id", "")
                ndc = function_args.get("ndc")
                drug_name = function_args.get("drug_name")
                
                print(f"🔍 Checking coverage for member {member_id}")
                
                mock_result = {
                    "member_id": member_id,
                    "drug": drug_name or "Sample Drug",
                    "ndc": ndc or "12345-678-90",
                    "coverage_status": "Covered",
                    "formulary_tier": "Tier 2 - Preferred Brand",
                    "copay": 35.00,
                    "prior_auth_required": False,
                    "step_therapy_required": False,
                    "quantity_limits": "30-day supply maximum"
                }
                
                print(f"✅ Coverage: {mock_result['coverage_status']} - {mock_result['formulary_tier']}")
                return json.dumps(mock_result)
                
            elif function_name == "check_prior_auth":
                member_id = function_args.get("member_id", "")
                ndc = function_args.get("ndc", "")
                pa_id = function_args.get("pa_id")
                
                print(f"📋 Checking prior authorization for {ndc}")
                
                mock_result = {
                    "member_id": member_id,
                    "ndc": ndc,
                    "pa_id": pa_id or "PA" + str(time.time())[-6:],
                    "status": "Approved",
                    "approval_date": "2025-01-05",
                    "expires": "2025-07-05",
                    "approved_quantity": "30 tablets per month",
                    "requirements_met": [
                        "Medical necessity documented",
                        "Prior medication trial completed",
                        "Prescriber authorization received"
                    ]
                }
                
                print(f"✅ Prior Auth: {mock_result['status']}")
                return json.dumps(mock_result)
                
            elif function_name == "get_formulary_details":
                plan_id = function_args.get("plan_id", "")
                drug_class = function_args.get("drug_class")
                ndc = function_args.get("ndc")
                
                print(f"📚 Getting formulary details for plan {plan_id}")
                
                mock_result = {
                    "plan_id": plan_id,
                    "formulary_name": "Comprehensive Formulary 2025",
                    "tiers": [
                        {
                            "tier": 1,
                            "name": "Generic",
                            "copay": 10.00,
                            "description": "Generic medications"
                        },
                        {
                            "tier": 2,
                            "name": "Preferred Brand",
                            "copay": 35.00,
                            "description": "Preferred brand medications"
                        },
                        {
                            "tier": 3,
                            "name": "Non-Preferred Brand",
                            "copay": 70.00,
                            "description": "Non-preferred brand medications"
                        },
                        {
                            "tier": 4,
                            "name": "Specialty",
                            "copay": 150.00,
                            "description": "Specialty medications"
                        }
                    ],
                    "restrictions": {
                        "prior_authorization": "Required for tier 3 and 4",
                        "step_therapy": "May apply to certain drug classes",
                        "quantity_limits": "Apply to select medications"
                    }
                }
                
                print(f"📚 Formulary: {len(mock_result['tiers'])} tiers available")
                return json.dumps(mock_result)
                
            elif function_name == "get_utilization_summary":
                member_id = function_args.get("member_id", "")
                plan_year = function_args.get("plan_year", 2025)
                
                print(f"📊 Getting utilization summary for {member_id}")
                
                mock_result = {
                    "member_id": member_id,
                    "plan_year": plan_year,
                    "deductible_status": {
                        "medical_deductible": {
                            "total": 250.00,
                            "used": 125.00,
                            "remaining": 125.00
                        },
                        "pharmacy_deductible": {
                            "total": 100.00,
                            "used": 75.00,
                            "remaining": 25.00
                        }
                    },
                    "out_of_pocket": {
                        "maximum": 3000.00,
                        "used": 640.00,
                        "remaining": 2360.00
                    },
                    "pharmacy_utilization": {
                        "prescriptions_filled": 8,
                        "total_cost": 1250.00,
                        "member_paid": 280.00,
                        "plan_paid": 970.00
                    }
                }
                
                print(f"📊 Utilization: ${mock_result['out_of_pocket']['used']:.2f} of ${mock_result['out_of_pocket']['maximum']:.2f} used")
                return json.dumps(mock_result)
                
            elif function_name == "check_step_therapy":
                member_id = function_args.get("member_id", "")
                ndc = function_args.get("ndc", "")
                plan_id = function_args.get("plan_id", "")
                
                print(f"🪜 Checking step therapy for {ndc}")
                
                mock_result = {
                    "member_id": member_id,
                    "ndc": ndc,
                    "plan_id": plan_id,
                    "step_therapy_required": True,
                    "current_step": 1,
                    "total_steps": 2,
                    "step_requirements": [
                        {
                            "step": 1,
                            "requirement": "Trial of generic ACE inhibitor",
                            "duration": "30 days minimum",
                            "status": "Completed",
                            "completion_date": "2024-12-15"
                        },
                        {
                            "step": 2,
                            "requirement": "Trial of preferred ARB",
                            "duration": "30 days minimum",
                            "status": "Current step - medication requested",
                            "eligible": True
                        }
                    ]
                }
                
                print(f"🪜 Step Therapy: Step {mock_result['current_step']} of {mock_result['total_steps']}")
                return json.dumps(mock_result)
            
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
