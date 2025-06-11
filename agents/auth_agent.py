"""
Specialized Authentication Agent

Handles member authentication, verification, and security-related tasks.
Can hand off to other agents once authentication is completed.
Now uses OpenAI Chat Completions API with streaming instead of Assistants API.
"""

import json
import time
from typing import Dict, Any, Optional, Iterator, List
from core.agent_coordinator import BaseAgent, AgentType
from openai import OpenAI
from core.shared_prompts import get_shared_context_awareness, get_shared_handoff_rules

class AuthenticationAgent(BaseAgent):
    """Specialized agent for member authentication and verification"""
    
    def __init__(self, client: OpenAI):
        super().__init__(client, AgentType.AUTHENTICATION)
        
        # Set agent-specific properties
        self.agent_name = "Authentication"
        self.agent_emoji = "🔐"
        
        # Initialize tools and system prompt
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
        
    def get_system_prompt(self) -> str:
        """Get the system prompt for the authentication agent"""
        base_prompt = """
You are a specialized authentication and security agent for a healthcare system.
Your expertise is in member verification, security validation, and authentication workflows.
Guide users through identity verification and multi-factor authentication clearly and securely.
Use the 'request_handoff' function only after successful authentication when user requests other services.
"""
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.AUTHENTICATION)
        clarification_rules = """
CLARIFICATION RULES:
- Answer follow-up questions about authentication steps directly (e.g., 'What is MFA?').
- Do not hand off clarifications within the authentication process.
- Only hand off after successful authentication to Pricing, Pharmacy, Benefits, or Clinical.
"""
        return base_prompt + context_awareness + handoff_rules + clarification_rules
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the authentication agent"""
        base_tools = [
            {
                "type": "function",
                "function": {
                    "name": "verify_member_identity",
                    "description": "Verify member identity with ID and date of birth",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "date_of_birth": {"type": "string", "description": "Date of birth YYYY-MM-DD"},
                            "additional_info": {"type": "string", "description": "Additional verification info (optional)"}
                        },
                        "required": ["member_id", "date_of_birth"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_mfa_code",
                    "description": "Send multi-factor authentication code",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string", "enum": ["sms", "email"], "description": "How to send code"},
                            "member_id": {"type": "string", "description": "Member ID"}
                        },
                        "required": ["method", "member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_mfa_code",
                    "description": "Verify MFA code entered by user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "6-digit verification code"},
                            "member_id": {"type": "string", "description": "Member ID"}
                        },
                        "required": ["code", "member_id"]
                    }
                }
            }
        ]
        
        # Add the handoff tool from base class
        handoff_tool = self.get_handoff_tool()
        if handoff_tool:
            base_tools.append(handoff_tool)
            
        return base_tools
    
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls with console output"""
        try:
            if function_name == "verify_member_identity":
                member_id = function_args["member_id"]
                dob = function_args["date_of_birth"]
                additional_info = function_args.get("additional_info", "")
                
                print(f"🔍 Verifying identity: Member {member_id}, DOB {dob}")
                
                # Demo authentication logic
                if member_id == "DEMO123456" and dob == "1985-03-15":
                    result = {
                        "verified": True,
                        "member_id": member_id,
                        "name": "Demo User",
                        "plan_id": "DEMO_PLAN_001",
                        "needs_mfa": False,  # Skip MFA for demo
                        "authenticated": True
                    }
                    print(f"✅ Identity verified for Demo User")
                else:
                    result = {
                        "verified": False,
                        "member_id": member_id,
                        "error": "Member ID and date of birth do not match our records",
                        "needs_mfa": False
                    }
                    print(f"❌ Identity verification failed")
                
                return json.dumps(result)
                
            elif function_name == "send_mfa_code":
                member_id = function_args["member_id"]
                method = function_args["method"]
                
                print(f"📱 Sending MFA code via {method} to member {member_id}")
                
                # Simulate sending code
                result = {
                    "code_sent": True,
                    "method": method,
                    "code": "123456",  # Demo code
                    "expires_in": 300  # 5 minutes
                }
                
                return json.dumps(result)
                
            elif function_name == "verify_mfa_code":
                code = function_args["code"]
                member_id = function_args["member_id"]
                
                print(f"🔑 Verifying MFA code: {code} for member {member_id}")
                
                # Demo verification - accept 123456
                if code == "123456":
                    result = {
                        "verified": True,
                        "authenticated": True,
                        "session_token": "demo_session_12345"
                    }
                    print(f"✅ MFA code verified")
                else:
                    result = {
                        "verified": False,
                        "error": "Invalid code"
                    }
                    print(f"❌ Invalid MFA code")
                
                return json.dumps(result)
                
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})