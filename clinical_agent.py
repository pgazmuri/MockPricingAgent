"""
Specialized Clinical Agent

Handles drug interactions, clinical criteria, therapeutic alternatives, and medical guidance.
Can hand off to other agents when needed (e.g., pricing, benefits, pharmacy).
"""

import json
import time
from typing import Dict, Any, Optional
from agent_coordinator import BaseAgent, AgentType, AgentResponse, HandoffRequest
from openai import OpenAI


class ClinicalAgent(BaseAgent):
    """Specialized agent for clinical and medical guidance"""
    
    def __init__(self, client: OpenAI):
        super().__init__(client, AgentType.CLINICAL)
        self.create_assistant()
    
    def create_assistant(self):
        """Create the clinical specialist assistant"""
        instructions = """
You are a specialized clinical pharmacist expert for a healthcare system.
Your expertise is in drug interactions, therapeutic alternatives, clinical criteria, and medication safety.

CAPABILITIES:
- Drug interaction checking
- Therapeutic alternative recommendations
- Clinical criteria evaluation
- Medication safety alerts
- Allergy checking
- Contraindication analysis
- Dosing guidance
- Age-appropriate alternatives

IMPORTANT: You provide clinical information but always remind users to consult their healthcare provider for medical decisions.

MEMBER INFO: For demos, use member ID "DEMO123456" with DOB "1985-03-15"

HANDOFF SCENARIOS:
- If user needs authentication/login → hand off to AUTHENTICATION agent
- If user asks about drug costs/pricing → hand off to PRICING agent  
- If user needs prescription management → hand off to PHARMACY agent
- If user needs plan coverage details → hand off to BENEFITS agent

WORKFLOW:
1. Assess clinical request for drug interactions, alternatives, etc.
2. Provide evidence-based clinical information
3. Always recommend consulting healthcare provider
4. Hand off for non-clinical needs (pricing, coverage, refills)

Use the 'request_handoff' function when user needs services outside your expertise.
Always prioritize patient safety and evidence-based recommendations.
"""
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_drug_interactions",
                    "description": "Check for drug-drug interactions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_list": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of drugs to check for interactions"
                            },
                            "member_id": {"type": "string", "description": "Member ID (optional)"}
                        },
                        "required": ["drug_list"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_therapeutic_alternatives",
                    "description": "Find therapeutic alternatives for a drug",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name to find alternatives for"},
                            "indication": {"type": "string", "description": "Medical condition/indication"},
                            "contraindications": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Known allergies or contraindications"
                            }
                        },
                        "required": ["drug_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_clinical_criteria",
                    "description": "Check clinical criteria for drug approval",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name"},
                            "indication": {"type": "string", "description": "Medical indication"},
                            "member_id": {"type": "string", "description": "Member ID"},
                            "age": {"type": "integer", "description": "Patient age (optional)"}
                        },
                        "required": ["drug_name", "indication", "member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_allergies",
                    "description": "Check for drug allergies and cross-sensitivities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "drug_name": {"type": "string", "description": "Drug to check"}
                        },
                        "required": ["member_id", "drug_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_dosing_guidance",
                    "description": "Get dosing recommendations based on patient factors",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name"},
                            "indication": {"type": "string", "description": "Medical indication"},
                            "age": {"type": "integer", "description": "Patient age"},
                            "weight": {"type": "number", "description": "Patient weight in kg (optional)"},
                            "renal_function": {"type": "string", "description": "Renal function status (optional)"}
                        },
                        "required": ["drug_name", "indication", "age"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "safety_alert_check",
                    "description": "Check for FDA safety alerts and warnings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name"},
                            "alert_type": {
                                "type": "string", 
                                "enum": ["boxed_warning", "safety_communication", "recall"],
                                "description": "Type of safety alert (optional)"
                            }
                        },
                        "required": ["drug_name"]
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
                                "enum": ["authentication", "pricing", "pharmacy", "benefits"],
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
            name="Clinical Pharmacist Specialist",
            instructions=instructions,
            model="gpt-4o-mini",
            tools=tools
        )
        
        self.thread = self.client.beta.threads.create()
    def process_message(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process message and return response with potential handoff"""
        print(f"⚕️ Clinical Agent processing: {message}")
        
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
                    print(f"🔧 Clinical Agent calling: {function_name} with {function_args}")
                    
                    if function_name == "request_handoff":
                        # Handle handoff request
                        agent_type_str = function_args["agent_type"]
                        reason = function_args["reason"]
                        context_summary = function_args["context_summary"]
                        handoff_request = HandoffRequest(
                            from_agent=AgentType.CLINICAL,
                            to_agent=AgentType(agent_type_str),
                            context={"summary": context_summary},
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
                agent_type=AgentType.CLINICAL,
                message=response_text,
                handoff_request=handoff_request,
                completed=False  # Clinical agent typically stays active for follow-ups
            )
            
        except Exception as e:
            print(f"❌ Error in Clinical Agent: {e}")
            return AgentResponse(
                agent_type=AgentType.CLINICAL,
                message=f"I'm sorry, I encountered an error processing your request: {str(e)}",
                handoff_request=None,
                completed=False
            )
        finally:
            # Clear current run
            self.current_run = None
    
    def _handle_function_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle function calls with mock clinical data"""
        try:
            if function_name == "check_drug_interactions":
                drug_list = function_args.get("drug_list", [])
                
                print(f"⚠️ Checking interactions for drugs: {', '.join(drug_list)}")
                
                # Mock interaction checking
                if len(drug_list) >= 2:
                    mock_result = {
                        "drugs_checked": drug_list,
                        "interactions_found": [
                            {
                                "drug_a": drug_list[0],
                                "drug_b": drug_list[1] if len(drug_list) > 1 else drug_list[0],
                                "severity": "Moderate",
                                "mechanism": "Both medications can lower blood pressure",
                                "clinical_effect": "Increased risk of hypotension",
                                "recommendation": "Monitor blood pressure closely. Consider dose adjustment.",
                                "documentation": "Well-documented"
                            }
                        ],
                        "total_interactions": 1
                    }
                else:
                    mock_result = {
                        "drugs_checked": drug_list,
                        "interactions_found": [],
                        "total_interactions": 0,
                        "message": "No interactions found with single drug"
                    }
                
                print(f"⚠️ Found {mock_result['total_interactions']} interaction(s)")
                return json.dumps(mock_result)
                
            elif function_name == "find_therapeutic_alternatives":
                drug_name = function_args.get("drug_name", "")
                indication = function_args.get("indication", "")
                contraindications = function_args.get("contraindications", [])
                
                print(f"🔄 Finding alternatives for {drug_name}")
                
                mock_result = {
                    "original_drug": drug_name,
                    "indication": indication,
                    "alternatives": [
                        {
                            "drug_name": "Lisinopril",
                            "drug_class": "ACE Inhibitor",
                            "mechanism": "ACE inhibition",
                            "efficacy": "Similar efficacy for hypertension",
                            "safety_profile": "Generally well tolerated",
                            "cost_category": "Generic - Low cost"
                        },
                        {
                            "drug_name": "Losartan",
                            "drug_class": "ARB",
                            "mechanism": "Angiotensin receptor blocking",
                            "efficacy": "Equivalent efficacy",
                            "safety_profile": "Lower cough incidence than ACE inhibitors",
                            "cost_category": "Generic - Low cost"
                        }
                    ],
                    "contraindications_considered": contraindications
                }
                
                print(f"🔄 Found {len(mock_result['alternatives'])} alternative(s)")
                return json.dumps(mock_result)
                
            elif function_name == "check_clinical_criteria":
                drug_name = function_args.get("drug_name", "")
                indication = function_args.get("indication", "")
                member_id = function_args.get("member_id", "")
                
                print(f"📋 Checking clinical criteria for {drug_name}")
                
                mock_result = {
                    "drug_name": drug_name,
                    "indication": indication,
                    "member_id": member_id,
                    "criteria_met": True,
                    "clinical_requirements": [
                        {
                            "requirement": "Appropriate diagnosis",
                            "status": "Met",
                            "evidence": "ICD-10 code I10 - Essential hypertension"
                        },
                        {
                            "requirement": "First-line therapy trial",
                            "status": "Met",
                            "evidence": "Previous ACE inhibitor trial documented"
                        },
                        {
                            "requirement": "Age appropriateness",
                            "status": "Met",
                            "evidence": "Patient age 39 - within approved range"
                        }
                    ],
                    "approval_recommendation": "Approve - All clinical criteria met"
                }
                
                print(f"✅ Clinical criteria: {mock_result['approval_recommendation']}")
                return json.dumps(mock_result)
                
            elif function_name == "check_allergies":
                member_id = function_args.get("member_id", "")
                drug_name = function_args.get("drug_name", "")
                
                print(f"🚨 Checking allergies for {drug_name}")
                
                mock_result = {
                    "member_id": member_id,
                    "drug_checked": drug_name,
                    "allergy_found": False,
                    "member_allergies": [
                        {
                            "allergen": "Penicillin",
                            "reaction": "Rash",
                            "severity": "Mild",
                            "date_reported": "2020-03-15"
                        }
                    ],
                    "cross_sensitivity_check": {
                        "potential_cross_reactions": [],
                        "safe_to_use": True
                    }
                }
                
                status = "Safe" if mock_result["safe_to_use"] else "Caution"
                print(f"🚨 Allergy check: {status}")
                return json.dumps(mock_result)
                
            elif function_name == "get_dosing_guidance":
                drug_name = function_args.get("drug_name", "")
                indication = function_args.get("indication", "")
                age = function_args.get("age", 0)
                
                print(f"💊 Getting dosing guidance for {drug_name}")
                
                mock_result = {
                    "drug_name": drug_name,
                    "indication": indication,
                    "patient_age": age,
                    "recommended_dosing": {
                        "starting_dose": "5mg once daily",
                        "maximum_dose": "40mg once daily",
                        "titration_schedule": "Increase by 5-10mg every 2-4 weeks as tolerated",
                        "special_considerations": [
                            "Take with or without food",
                            "Monitor blood pressure and kidney function",
                            "Reduce dose in elderly patients"
                        ]
                    },
                    "age_specific_notes": "Adult dosing appropriate for age 39",
                    "monitoring_parameters": [
                        "Blood pressure",
                        "Serum creatinine",
                        "Serum potassium"
                    ]
                }
                
                print(f"💊 Dosing: {mock_result['recommended_dosing']['starting_dose']}")
                return json.dumps(mock_result)
                
            elif function_name == "safety_alert_check":
                drug_name = function_args.get("drug_name", "")
                alert_type = function_args.get("alert_type")
                
                print(f"⚠️ Checking safety alerts for {drug_name}")
                
                mock_result = {
                    "drug_name": drug_name,
                    "alert_type_checked": alert_type or "all",
                    "active_alerts": [
                        {
                            "alert_type": "safety_communication",
                            "date_issued": "2024-08-15",
                            "title": "Risk of angioedema with ACE inhibitors",
                            "summary": "Rare but serious risk of angioedema, particularly in first month of therapy",
                            "action_required": "Monitor patients for signs of angioedema, especially during initiation",
                            "severity": "Important"
                        }
                    ],
                    "recalls": [],
                    "boxed_warnings": []
                }
                
                print(f"⚠️ Found {len(mock_result['active_alerts'])} active alert(s)")
                return json.dumps(mock_result)
            
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
