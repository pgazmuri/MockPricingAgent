"""
Specialized Pricing Agent

Handles drug pricing calculations, cost estimates, and insurance benefit calculations.
Can hand off to other agents when needed (e.g., authentication, pharmacy services).
"""

import json
import time
from typing import Dict, Any, Optional
from agent_coordinator import BaseAgent, AgentType, AgentResponse, HandoffRequest
from openai import OpenAI
from mock_services import MockPBMServices
from pricing_calculator import MathCalculator

class PricingAgent(BaseAgent):
    """Specialized agent for drug pricing and cost calculations"""
    
    def __init__(self, client: OpenAI):
        super().__init__(client, AgentType.PRICING)
        self.pbm_services = MockPBMServices()
        self.math_calculator = MathCalculator()
        self.create_assistant()
    
    def create_assistant(self):
        """Create the pricing specialist assistant"""
        instructions = """
You are a specialized drug pricing voice agent for a Pharmacy Benefits Manager (PBM).
Your expertise is in calculating drug costs, insurance benefits, and pricing estimates.
You make it easy for customers, often older medicare patients, to find and understand drug costs.
You answer as briefly as possible in small nuggets while providing clear explanations. You do not provide long bullet lists.
If asked about details like copays, and insurance benefits, you can explain.
Very Important: You are talking to a human over the phone. Do not overwhelm them with text or long bullet lists. keep answers bite sized. Your answers must be VERY CONCISE. You ask one question at a time, or ask "tell me about" questions if you are trying to whittle down options.
Don't call the ndc function if the user doesn't know their medication name. Help them figure it out first based on your knowledge.
Be conversational. Don't repeat the same words over and over, like when listing drug options. say 1, 2 or 3 milligrams instead of <drguname> 1 milligram, <drugname> 2 milligram, etc...

CAPABILITIES:
- Drug cost lookups and calculations
- Insurance benefit analysis  
- Step-by-step pricing math
- Copay/coinsurance calculations
- Deductible and out-of-pocket tracking
- Coupon and discount analysis

MEMBER INFO: For demos, use member ID "DEMO123456" with DOB "1985-03-15"

HANDOFF SCENARIOS:
- If user needs authentication/login → hand off to AUTHENTICATION agent
- If user asks about prescription status/refills → hand off to PHARMACY agent  
- If user needs plan coverage details → hand off to BENEFITS agent
- If user asks about drug interactions → hand off to CLINICAL agent

WORKFLOW:
1. Look up drugs using ndc_lookup
2. Check eligibility, benefits, utilization, formulary, costs, coupons
3. Use math functions for all calculations
4. Explain costs clearly to the user

Use the 'request_handoff' function when user needs services outside your expertise.
Always show your mathematical work clearly using the calculation functions.
"""
        
        # Define tools (same as before but add handoff capability)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ndc_lookup",
                    "description": "Search for drugs by name to find specific drug products",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name to search"},
                            "dose": {"type": "string", "description": "Dose/strength (optional)"},
                            "qty": {"type": "integer", "description": "Quantity (optional)"},
                            "dosage_form": {"type": "string", "description": "Form like tablet, capsule (optional)"}
                        },
                        "required": ["drug_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_eligibility",
                    "description": "Verify member eligibility",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string"},
                            "date_of_birth": {"type": "string", "description": "YYYY-MM-DD format"}
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_plan_benefits",
                    "description": "Get plan benefit structure",
                    "parameters": {
                        "type": "object",
                        "properties": {"plan_id": {"type": "string"}},
                        "required": ["plan_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_member_utilization",
                    "description": "Get member utilization data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string"},
                            "plan_year": {"type": "integer", "default": 2025}
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_formulary",
                    "description": "Check formulary coverage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ndc": {"type": "string"},
                            "plan_id": {"type": "string"}
                        },
                        "required": ["ndc", "plan_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_drug_cost",
                    "description": "Get drug cost information",
                    "parameters": {
                        "type": "object",
                        "properties": {"ndc": {"type": "string"}},
                        "required": ["ndc"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_coupons",
                    "description": "Check for available coupons",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ndc": {"type": "string"},
                            "member_id": {"type": "string"}
                        },
                        "required": ["ndc"]
                    }
                }
            },
            # Math functions
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
                                "enum": ["authentication", "pharmacy", "benefits", "clinical"],
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
        self.assistant = self.client.beta.assistants.create(
            name="Drug Pricing Specialist",
            instructions=instructions,
            model="gpt-4.1",
            tools=tools
        )
        
        self.thread = self.client.beta.threads.create()
        
    def process_message(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process message and return response with potential handoff"""
        print(f"💰 Pricing Agent processing: {message}")
        
        try:
            # Ensure thread is ready for new messages
            self._ensure_thread_ready()
            
            # Add user message to thread
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=f"{message}\n\nContext: {json.dumps(context or {})}"
            )
            
            # Run assistant
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id
            )
              # Track current run
            self.current_run = run
            
            handoff_request = None
            
            # Handle function calls
            run = self._wait_for_run_completion(run, self.thread.id)
            
            while run.status == 'requires_action':
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"🔧 Pricing Agent calling: {function_name} with {function_args}")
                    
                    if function_name == "request_handoff":
                        # Handle handoff request
                        agent_type_str = function_args["agent_type"]
                        reason = function_args["reason"]
                        context_summary = function_args["context_summary"]
                        
                        handoff_request = HandoffRequest(
                            from_agent=AgentType.PRICING,
                            to_agent=AgentType(agent_type_str),
                            context={"summary": context_summary, "original_context": context},
                            reason=reason,
                            user_message=message
                        )
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"status": "handoff_requested"})
                        })
                        
                    else:
                        # Handle regular function calls
                        output = self._handle_function_call(function_name, function_args)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })
                
                # Submit tool outputs
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                
                # Wait for completion again
                run = self._wait_for_run_completion(run, self.thread.id)
            
            # Get response
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread.id,
                order="desc",
                limit=1
            )
            
            response_text = messages.data[0].content[0].text.value
            
            return AgentResponse(
                agent_type=AgentType.PRICING,
                message=response_text,
                handoff_request=handoff_request,
                completed=False  # Pricing agent typically stays active for follow-ups
            )
            
        except Exception as e:
            print(f"❌ Error in Pricing Agent: {e}")
            return AgentResponse(
                agent_type=AgentType.PRICING,
                message=f"I'm sorry, I encountered an error processing your request: {str(e)}",
                handoff_request=None,
                completed=False
            )
        finally:
            # Clear current run
            self.current_run = None
    
    def _handle_function_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle function calls with console output"""
        try:
            if function_name == "ndc_lookup":
                result = self.pbm_services.ndc_lookup(**function_args)
                print(f"💊 NDC Lookup Results:")
                for i, drug in enumerate(result.drugs, 1):
                    print(f"   {i}. {drug.name} ({drug.strength}) - {drug.dosage_form}")
                    print(f"      NDC: {drug.ndc}, Manufacturer: {drug.manufacturer}")
                return result.model_dump_json()
                
            elif function_name == "check_eligibility":
                result = self.pbm_services.check_eligibility(**function_args)
                print(f"✅ Eligibility Check Result:")
                if result.is_eligible and result.member_info:
                    print(f"   Member: {result.member_info.first_name} {result.member_info.last_name}")
                    print(f"   Plan ID: {result.member_info.plan_id}")
                return result.model_dump_json()
                
            elif function_name == "get_plan_benefits":
                result = self.pbm_services.get_plan_benefits(**function_args)
                print(f"📋 Plan Benefits:")
                print(f"   Plan: {result.plan_name} ({result.plan_year})")
                print(f"   Deductible: ${result.deductible}")
                print(f"   Out-of-Pocket Max: ${result.out_of_pocket_max}")
                return result.model_dump_json()
                
            elif function_name == "get_member_utilization":
                result = self.pbm_services.get_member_utilization(**function_args)
                print(f"📊 Member Utilization:")
                print(f"   Deductible: ${result.deductible_met} spent")
                print(f"   Out-of-Pocket: ${result.out_of_pocket_met} spent")
                return result.model_dump_json()
                
            elif function_name == "check_formulary":
                result = self.pbm_services.check_formulary(**function_args)
                print(f"📖 Formulary Check:")
                status = "✅ Covered" if result.is_covered else "❌ Not covered"
                print(f"   Status: {status}")
                if result.is_covered:
                    print(f"   Tier: {result.tier}")
                return result.model_dump_json()
                
            elif function_name == "get_drug_cost":
                result = self.pbm_services.get_drug_cost(**function_args)
                print(f"💰 Drug Cost Information:")
                print(f"   Plan Price: ${result.plan_negotiated_price}")
                print(f"   Dispensing Fee: ${result.dispensing_fee}")
                return result.model_dump_json()
                
            elif function_name == "check_coupons":
                result = self.pbm_services.check_coupons(**function_args)
                print(f"🎟️ Available Coupons:")
                eligible_coupons = [c for c in result.available_coupons if c.eligible]
                print(f"   Found {len(eligible_coupons)} eligible coupons")
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
