"""
Specialized Pharmacy Agent

Handles prescription management, refills, transfers, and pharmacy-related services.
Can hand off to other agents when needed (e.g., pricing, authentication, clinical).
"""

import json
import time
from typing import Dict, Any, Optional, List
from agent_coordinator import BaseAgent, AgentType, AgentResponse, HandoffRequest
from openai import OpenAI
from shared_prompts import get_shared_context_awareness, get_shared_handoff_rules


class PharmacyAgent(BaseAgent):
    """Specialized agent for pharmacy services and prescription management"""
    
    def __init__(self, client: OpenAI, model: str = "gpt-4.1"):
        super().__init__(client, AgentType.PHARMACY, model=model)
        
        # Set agent-specific properties
        self.agent_name = "Pharmacy"
        self.agent_emoji = "🏥"
          # Initialize agent configuration
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the pharmacy agent"""
        base_prompt = """
You are a specialized pharmacy services expert for a healthcare system.
Your expertise is in prescription management, refills, transfers, and pharmacy operations.
Provide clear and concise information on prescription status, refill scheduling, transfers, and pickup details.
Always ensure member verification before processing requests with specific information like refills, and always get confirmation to proceed.
You do not need to ask for member pharmacy ID or prescription ID, the system has this information once the member is authenticated.
Use the 'request_handoff' function only when your expertise domain is exceeded.
"""
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.PHARMACY)
        clarification_rules = """
CLARIFICATION RULES:
- After providing prescription status or refill details, answer follow-up questions directly.
- If the user asks 'When will my refill be ready?' or 'Can I pick up tomorrow?', answer from the context you have.
- Only hand off pricing queries to Pricing, coverage queries to Benefits, clinical queries to Clinical, and authentication to Authentication.
"""
        return base_prompt + context_awareness + handoff_rules + clarification_rules
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools for the pharmacy agent"""
        base_tools = [
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
                }            }
        ]
        
        # Add the handoff tool from base class
        handoff_tool = self.get_handoff_tool()
        if handoff_tool:
            base_tools.append(handoff_tool)
            
        return base_tools
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls with mock data"""
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
