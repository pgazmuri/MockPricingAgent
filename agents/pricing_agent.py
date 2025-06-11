"""
Specialized Pricing Agent

Handles drug pricing calculations, cost estimates, and insurance benefit calculations.
Can hand off to other agents when needed (e.g., authentication, pharmacy services).
Now uses OpenAI Chat Completions API with streaming instead of Assistants API.
"""

import json
import time
from typing import Dict, Any, Optional, Iterator, List
from core.agent_coordinator import BaseAgent, AgentType, HandoffRequest, CoordinationMode
from openai import OpenAI
from services.mock_services import MockPBMServices
from services.pricing_calculator import MathCalculator
from core.shared_prompts import get_shared_context_awareness, get_shared_handoff_rules

class PricingAgent(BaseAgent):
    """Specialized agent for drug pricing and cost calculations"""    
    def __init__(self, client: OpenAI, model: str = "gpt-4.1"):
        super().__init__(client, AgentType.PRICING, coordinator=None, model=model)
        self.pbm_services = MockPBMServices()
        self.math_calculator = MathCalculator()
        
        # Set agent-specific properties
        self.agent_name = "Pricing"
        self.agent_emoji = "💰"
          # Initialize tools and system prompt
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the pricing agent"""
        # Base pricing agent prompt
        base_prompt = """
You are a specialized drug pricing voice agent for a Pharmacy Benefits Manager (PBM).
Your expertise is in helping users find their medications and explaining drug costs, insurance benefits, and pricing estimates.
You make it easy for customers, often older Medicare patients, to find and understand drug costs, as well as explore alternatives.
Keep answers bite-sized and conversational. Do not overwhelm with long lists.
Always show your mathematical work clearly using the calculation functions.
Use the 'request_handoff' function only when the request is truly outside your expertise.
Don't call the ndc function if the user doesn't know their medication name. Help them figure it out first based on your knowledge.
Never ask for an NDC code directly; instead, ask for the drug name or other identifying information. Your conversation partner doesn't know anything about NDC codes.
You do not need to ask about insurance or member ID, as the pricing system will always have access to the member's insurance information once authenticated.
"""
        # Shared context awareness and handoff rules
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.PRICING, self.coordination_mode)
        
        # Pricing-specific clarification rules
        clarification_rules = """
CLARIFICATION RULES:
- After providing a specific dollar amount, you MUST answer follow-up questions about that amount directly.
- If the user asks "So I pay $X?" or "What's my out-of-pocket?", refer to your previous calculation.
- Only hand off plan structure or benefit policy questions without specific amounts to the Benefits agent.
- Always hand off to Pharmacy agent for prescription status or refill requests.
"""
        return base_prompt + context_awareness + handoff_rules + clarification_rules
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the pricing agent"""
        tools = [
            # Core PBM Functions
            {
                "type": "function",
                "function": {
                    "name": "ndcLookup",
                    "description": "Search for drugs by name to lookup and find specific drug products with NDCs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Drug name, NDC, or search term"},
                            "mode": {
                                "type": "string", 
                                "enum": ["exact", "search"],
                                "description": "Search mode: 'exact' for precise matches, 'search' for broader results",
                                "default": "search"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculateRxPrice",
                    "description": "Calculate prescription price with member cost and plan cost breakdown, taking into account member's insurance and other plan details. Requires an authenticated member ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ndc": {"type": "string", "description": "National Drug Code"},
                            "memberId": {"type": "string", "description": "Member ID"}
                        },
                        "required": ["ndc", "pharmacyNpi", "memberId", "fillDate"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "getFormularyAlternatives",
                    "description": "Get list of formulary alternative NDCs for a given drug",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "planId": {"type": "string", "description": "Plan identifier"},
                            "ndc": {"type": "string", "description": "NDC to find alternatives for"}
                        },
                        "required": ["planId", "ndc"]
                    }
                }
            },
            # Math/Calculator functions
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "subtract",
                    "description": "Subtract two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "multiply",
                    "description": "Multiply two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "divide",
                    "description": "Divide two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_percentage",
                    "description": "Calculate percentage of amount",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number"},
                            "percentage": {"type": "number"}
                        },
                        "required": ["amount", "percentage"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_minimum",
                    "description": "Apply minimum value",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "minimum": {"type": "number"}
                        },
                        "required": ["value", "minimum"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_maximum",
                    "description": "Apply maximum value",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "maximum": {"type": "number"}
                        },
                        "required": ["value", "maximum"]
                    }
                }
            }        ]
        
        # Add handoff function from base class
        tools.append(self.get_handoff_tool())
        return tools
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls with console output"""
        try:
            # Core PBM Functions
            if function_name == "ndcLookup":
                from core.models import SearchMode
                query = function_args["query"]
                mode = SearchMode(function_args.get("mode", "search"))
                
                result = self.pbm_services.ndc_lookup(query, mode)
                print(f"💊 NDC Lookup Results for '{query}' (mode: {mode}):")
                for i, drug in enumerate(result.result, 1):
                    print(f"   {i}. {drug.drug_name} - NDC: {drug.ndc}")
                    print(f"      Strength: {drug.strength}, Form: {drug.dosage_form}")
                    print(f"      Type: {drug.brand_generic}, Match: {drug.match:.2f}")
                
                return result.model_dump_json()
                
            elif function_name == "calculateRxPrice":
                ndc = function_args["ndc"]
                member_id = function_args["memberId"]
                
                result = self.pbm_services.calculate_rx_price(ndc, member_id)
                print(f"💰 Prescription Price Calculation:")
                print(f"   Plan Price: ${result.result.drug_cost}")
                print(f"   Member Cost: ${result.result.member_cost}")
                print(f"   Plan Paid: ${result.result.plan_paid}")
                print(f"   Pricing Basis: {result.result.pricing_basis}")
                print(f"   Context: {result.result.context}")
                
                return result.model_dump_json()
                
            elif function_name == "getFormularyAlternatives":
                plan_id = function_args["planId"]
                ndc = function_args["ndc"]
                
                result = self.pbm_services.get_formulary_alternatives(plan_id, ndc)
                print(f"🔄 Formulary Alternatives for NDC {ndc}:")
                if result.result:
                    for i, alt_ndc in enumerate(result.result, 1):
                        print(f"   {i}. NDC: {alt_ndc}")
                else:
                    print("   No alternatives found")
                
                return result.model_dump_json()
            
            # Math functions
            elif function_name == "add":
                result = self.math_calculator.add(**function_args)
                print(f"📊 Math: {function_args['a']} + {function_args['b']} = {result}")
                return json.dumps({"result": result})
                
            elif function_name == "subtract":
                result = self.math_calculator.subtract(**function_args)
                print(f"📊 Math: {function_args['a']} - {function_args['b']} = {result}")
                return json.dumps({"result": result})
                
            elif function_name == "multiply":
                result = self.math_calculator.multiply(**function_args)
                print(f"📊 Math: {function_args['a']} × {function_args['b']} = {result}")
                return json.dumps({"result": result})
                
            elif function_name == "divide":
                result = self.math_calculator.divide(**function_args)
                print(f"📊 Math: {function_args['a']} ÷ {function_args['b']} = {result}")
                return json.dumps({"result": result})
                
            elif function_name == "calculate_percentage":
                result = self.math_calculator.calculate_percentage(**function_args)
                print(f"📊 Math: {function_args['percentage']}% of {function_args['amount']} = {result}")
                return json.dumps({"result": result})
                
            elif function_name == "apply_minimum":
                result = self.math_calculator.apply_minimum(**function_args)
                print(f"📊 Math: max({function_args['value']}, {function_args['minimum']}) = {result}")
                return json.dumps({"result": result})
                
            elif function_name == "apply_maximum":
                result = self.math_calculator.apply_maximum(**function_args)
                print(f"📊 Math: min({function_args['value']}, {function_args['maximum']}) = {result}")
                return json.dumps({"result": result})
                
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
