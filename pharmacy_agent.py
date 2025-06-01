"""
Specialized Pharmacy Agent

Handles prescription management, refills, transfers, and pharmacy-related services.
Can hand off to other agents when needed (e.g., pricing, authentication, clinical).
"""

import json
import time
from typing import Dict, Any, Optional
from agent_coordinator import BaseAgent, AgentType, AgentResponse, HandoffRequest
from openai import OpenAI


class PharmacyAgent(BaseAgent):
    """Specialized agent for pharmacy services and prescription management"""
    
    def __init__(self, client: OpenAI):
        super().__init__(client, AgentType.PHARMACY)
        self.create_assistant()
    
    def create_assistant(self):
        """Create the pharmacy specialist assistant"""
        instructions = """
You are a specialized pharmacy services expert for a healthcare system.
Your expertise is in prescription management, refills, transfers, and pharmacy operations.

CAPABILITIES:
- Prescription status checking
- Refill management and scheduling  
- Prescription transfers between pharmacies
- Pickup notifications and reminders
- Pharmacy location services
- Prescription history
- Medication synchronization

MEMBER INFO: For demos, use member ID "DEMO123456" with DOB "1985-03-15"

HANDOFF SCENARIOS:
- If user needs authentication/login → hand off to AUTHENTICATION agent
- If user asks about drug costs/pricing → hand off to PRICING agent  
- If user needs plan coverage details → hand off to BENEFITS agent
- If user asks about drug interactions/alternatives → hand off to CLINICAL agent

WORKFLOW:
1. Check prescription status or refill needs
2. Verify member identity if needed
3. Process pharmacy requests (refills, transfers, etc.)
4. Provide clear status updates and next steps

Use the 'request_handoff' function when user needs services outside your expertise.
Always be helpful and provide accurate pharmacy information.
"""
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_prescription_status",
                    "description": "Check the status of prescriptions for a member",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "prescription_id": {"type": "string", "description": "Specific prescription ID (optional)"}
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "request_refill",
                    "description": "Request a prescription refill",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "prescription_id": {"type": "string", "description": "Prescription ID to refill"},
                            "pharmacy_id": {"type": "string", "description": "Preferred pharmacy ID (optional)"}
                        },
                        "required": ["member_id", "prescription_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "transfer_prescription",
                    "description": "Transfer prescription to a different pharmacy",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "prescription_id": {"type": "string", "description": "Prescription ID to transfer"},
                            "from_pharmacy_id": {"type": "string", "description": "Current pharmacy ID"},
                            "to_pharmacy_id": {"type": "string", "description": "Target pharmacy ID"}
                        },
                        "required": ["member_id", "prescription_id", "from_pharmacy_id", "to_pharmacy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_pharmacies",
                    "description": "Find pharmacies near a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "zip_code": {"type": "string", "description": "ZIP code to search near"},
                            "radius_miles": {"type": "number", "description": "Search radius in miles", "default": 10}
                        },
                        "required": ["zip_code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_pickup_notifications",
                    "description": "Get pickup notifications for a member",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"}
                        },
                        "required": ["member_id"]
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
                                "enum": ["authentication", "pricing", "benefits", "clinical"],
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
            name="Pharmacy Services Specialist",
            instructions=instructions,
            model="gpt-4.1-mini",
            tools=tools
        )
        self.thread = self.client.beta.threads.create()
    
    def process_message(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process message and return response with potential handoff"""
        print(f"🏥 Pharmacy Agent processing: {message}")
        
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
                    print(f"🔧 Pharmacy Agent calling: {function_name} with {function_args}")
                    
                    if function_name == "request_handoff":
                        # Handle handoff request
                        agent_type_str = function_args["agent_type"]
                        reason = function_args["reason"]
                        context_summary = function_args["context_summary"]
                        handoff_request = HandoffRequest(
                            from_agent=AgentType.PHARMACY,
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
                agent_type=AgentType.PHARMACY,
                message=response_text,
                handoff_request=handoff_request,
                completed=False  # Pharmacy agent typically stays active for follow-ups
            )
            
        except Exception as e:
            print(f"❌ Error in Pharmacy Agent: {e}")
            return AgentResponse(
                agent_type=AgentType.PHARMACY,
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
            if function_name == "check_prescription_status":
                member_id = function_args.get("member_id", "")
                prescription_id = function_args.get("prescription_id")
                
                print(f"🔍 Checking prescription status for member {member_id}")
                
                # Mock prescription data
                if prescription_id:
                    mock_result = {
                        "prescription_id": prescription_id,
                        "drug_name": "Lisinopril 10mg",
                        "status": "Ready for pickup",
                        "pharmacy": "CVS #1234 - Main St",
                        "filled_date": "2025-01-10",
                        "pickup_by": "2025-01-17",
                        "refills_remaining": 3
                    }
                else:
                    mock_result = {
                        "prescriptions": [
                            {
                                "prescription_id": "RX123456",
                                "drug_name": "Lisinopril 10mg",
                                "status": "Ready for pickup",
                                "pharmacy": "CVS #1234 - Main St",
                                "filled_date": "2025-01-10"
                            },
                            {
                                "prescription_id": "RX789012",
                                "drug_name": "Metformin 500mg",
                                "status": "Refill needed",
                                "pharmacy": "CVS #1234 - Main St",
                                "last_filled": "2024-12-15"
                            }
                        ]
                    }
                
                print(f"📋 Status Result: {mock_result}")
                return json.dumps(mock_result)
                
            elif function_name == "request_refill":
                member_id = function_args.get("member_id", "")
                prescription_id = function_args.get("prescription_id", "")
                pharmacy_id = function_args.get("pharmacy_id", "CVS #1234")
                
                print(f"🔄 Processing refill request for {prescription_id}")
                
                mock_result = {
                    "refill_id": "RF" + str(time.time())[-6:],
                    "prescription_id": prescription_id,
                    "status": "Processing",
                    "estimated_ready": "2025-01-12 3:00 PM",
                    "pharmacy": pharmacy_id,
                    "message": "Refill request submitted successfully. You'll receive a text when ready."
                }
                
                print(f"✅ Refill Result: {mock_result}")
                return json.dumps(mock_result)
                
            elif function_name == "transfer_prescription":
                prescription_id = function_args.get("prescription_id", "")
                from_pharmacy = function_args.get("from_pharmacy_id", "")
                to_pharmacy = function_args.get("to_pharmacy_id", "")
                
                print(f"🔄 Transferring {prescription_id} from {from_pharmacy} to {to_pharmacy}")
                
                mock_result = {
                    "transfer_id": "TR" + str(time.time())[-6:],
                    "prescription_id": prescription_id,
                    "from_pharmacy": from_pharmacy,
                    "to_pharmacy": to_pharmacy,
                    "status": "Transfer initiated",
                    "estimated_completion": "2-4 hours",
                    "message": "Transfer request sent. New pharmacy will contact you when ready."
                }
                
                print(f"📋 Transfer Result: {mock_result}")
                return json.dumps(mock_result)
                
            elif function_name == "find_pharmacies":
                zip_code = function_args.get("zip_code", "")
                radius = function_args.get("radius_miles", 10)
                
                print(f"🏥 Finding pharmacies near {zip_code} within {radius} miles")
                
                mock_result = {
                    "pharmacies": [
                        {
                            "pharmacy_id": "CVS #1234",
                            "name": "CVS Pharmacy",
                            "address": "123 Main St, City, ST 12345",
                            "phone": "(555) 123-4567",
                            "distance_miles": 0.8,
                            "hours": "Mon-Fri 9am-9pm, Sat-Sun 9am-6pm"
                        },
                        {
                            "pharmacy_id": "WAL #5678",
                            "name": "Walmart Pharmacy",
                            "address": "456 Oak Ave, City, ST 12345",
                            "phone": "(555) 987-6543",
                            "distance_miles": 1.2,
                            "hours": "Mon-Fri 9am-8pm, Sat-Sun 9am-6pm"
                        }
                    ]
                }
                
                print(f"📍 Pharmacy Results: Found {len(mock_result['pharmacies'])} pharmacies")
                return json.dumps(mock_result)
                
            elif function_name == "get_pickup_notifications":
                member_id = function_args.get("member_id", "")
                
                print(f"🔔 Getting pickup notifications for {member_id}")
                
                mock_result = {
                    "notifications": [
                        {
                            "prescription_id": "RX123456",
                            "drug_name": "Lisinopril 10mg",
                            "pharmacy": "CVS #1234 - Main St",
                            "ready_date": "2025-01-10",
                            "pickup_by": "2025-01-17",
                            "notification_sent": "2025-01-10 2:30 PM"
                        }
                    ],
                    "count": 1
                }
                
                print(f"🔔 Notifications: {mock_result['count']} ready for pickup")
                return json.dumps(mock_result)
            
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
