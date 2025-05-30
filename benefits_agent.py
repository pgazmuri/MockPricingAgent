"""
Specialized Benefits Agent

Handles plan details, coverage rules, prior authorizations, and benefit questions.
Can hand off to other agents when needed (e.g., pricing, authentication, clinical).
"""

import json
import time
from typing import Dict, Any, Optional
from agent_coordinator import BaseAgent, AgentType, AgentResponse, HandoffRequest
from openai import OpenAI


class BenefitsAgent(BaseAgent):
    """Specialized agent for plan benefits and coverage information"""
    
    def __init__(self, client: OpenAI):
        super().__init__(client, AgentType.BENEFITS)
        self.create_assistant()
    
    def create_assistant(self):
        """Create the benefits specialist assistant"""
        instructions = """
You are a specialized benefits and coverage expert for a healthcare insurance system.
Your expertise is in plan details, coverage rules, prior authorizations, and benefit explanations.

CAPABILITIES:
- Plan benefit explanations
- Coverage determination
- Prior authorization status and requirements
- Formulary tier explanations
- Deductible and out-of-pocket tracking
- Plan comparisons
- Benefits utilization analysis
- Step therapy requirements

MEMBER INFO: For demos, use member ID "DEMO123456" with DOB "1985-03-15"

HANDOFF SCENARIOS:
- If user needs authentication/login → hand off to AUTHENTICATION agent
- If user asks about drug costs/pricing calculations → hand off to PRICING agent  
- If user needs prescription management → hand off to PHARMACY agent
- If user asks about drug interactions/alternatives → hand off to CLINICAL agent

WORKFLOW:
1. Identify the member's plan and benefits
2. Explain coverage rules and requirements
3. Guide through prior authorization if needed
4. Provide clear benefit explanations

Use the 'request_handoff' function when user needs services outside your expertise.
Always explain benefits clearly and help members understand their coverage.
"""
        
        tools = [
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
        self.assistant = self.client.beta.assistants.create(
            name="Benefits Coverage Specialist",
            instructions=instructions,
            model="gpt-4o-mini",
            tools=tools
        )
        
        self.thread = self.client.beta.threads.create()
    def process_message(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process message and return response with potential handoff"""
        print(f"📋 Benefits Agent processing: {message}")
        
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
                    print(f"🔧 Benefits Agent calling: {function_name} with {function_args}")
                    
                    if function_name == "request_handoff":
                        # Handle handoff request
                        agent_type_str = function_args["agent_type"]
                        reason = function_args["reason"]
                        context_summary = function_args["context_summary"]
                        
                        handoff_request = HandoffRequest(
                            from_agent=AgentType.BENEFITS,
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
                agent_type=AgentType.BENEFITS,
                message=response_text,
                handoff_request=handoff_request,
                completed=False  # Benefits agent typically stays active for follow-ups
            )
            
        except Exception as e:
            print(f"❌ Error in Benefits Agent: {e}")
            return AgentResponse(
                agent_type=AgentType.BENEFITS,
                message=f"I'm sorry, I encountered an error processing your request: {str(e)}",
                handoff_request=None,
                completed=False
            )
        finally:
            # Clear current run
            self.current_run = None
    
    def _handle_function_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle function calls with mock data"""
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
