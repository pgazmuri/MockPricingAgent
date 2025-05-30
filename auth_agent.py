"""
Authentication Agent

Handles member authentication, verification, and security-related tasks.
Can hand off to other agents once authentication is completed.
"""

import json
import time
from typing import Dict, Any, Optional
from agent_coordinator import BaseAgent, AgentType, AgentResponse, HandoffRequest
from openai import OpenAI

class AuthenticationAgent(BaseAgent):
    """Specialized agent for member authentication and verification"""
    
    def __init__(self, client: OpenAI):
        super().__init__(client, AgentType.AUTHENTICATION)
        self.create_assistant()
    
    def create_assistant(self):
        """Create the authentication specialist assistant"""
        instructions = """
You are a specialized authentication and security agent for a healthcare system.

CAPABILITIES:
- Member identity verification
- Multi-factor authentication simulation
- Security question validation
- Account lockout/unlock procedures
- Privacy and HIPAA compliance

AUTHENTICATION FLOW:
1. Collect member ID and date of birth
2. Verify identity through additional questions if needed
3. Simulate MFA (text/email codes)
4. Once authenticated, hand off to appropriate service agent

DEMO MODE: Accept member ID "DEMO123456" with DOB "1985-03-15" as valid.
For other members, simulate realistic authentication flows.

HANDOFF RULES:
- After successful authentication, ask user what they need help with
- Hand off to PRICING for cost questions
- Hand off to PHARMACY for prescription management  
- Hand off to BENEFITS for plan information
- Hand off to CLINICAL for medical questions

Be security-conscious but user-friendly. Explain each step clearly.
"""
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "verify_member_identity",
                    "description": "Verify member identity with ID and DOB",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "date_of_birth": {"type": "string", "description": "Date of birth YYYY-MM-DD"},
                            "additional_info": {"type": "string", "description": "Additional verification info"}
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
                            "member_id": {"type": "string"}
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
                            "code": {"type": "string", "description": "6-digit code"},
                            "member_id": {"type": "string"}
                        },
                        "required": ["code", "member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "request_handoff",
                    "description": "Hand off to another specialized agent after authentication",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_type": {
                                "type": "string", 
                                "enum": ["pricing", "pharmacy", "benefits", "clinical"],
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
            name="Authentication Specialist",
            instructions=instructions,
            model="gpt-4o-mini",
            tools=tools
        )
        
        self.thread = self.client.beta.threads.create()
    
    def process_message(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process authentication-related message"""
        print(f"🔐 Authentication Agent processing: {message}")
        
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
                    print(f"🔧 Auth Agent calling: {function_name} with {function_args}")
                    
                    if function_name == "request_handoff":
                        # Handle handoff request
                        agent_type_str = function_args["agent_type"]
                        reason = function_args["reason"]
                        context_summary = function_args["context_summary"]
                        
                        handoff_request = HandoffRequest(
                            from_agent=AgentType.AUTHENTICATION,
                            to_agent=AgentType(agent_type_str),
                            context={"summary": context_summary, "authenticated": True, "member_id": "DEMO123456"},
                            reason=reason,
                            user_message=message
                        )
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"status": "handoff_requested"})
                        })
                        
                    else:
                        # Handle authentication functions
                        output = self._handle_auth_function(function_name, function_args)
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
            
            # Authentication typically completes and hands off
            completed = handoff_request is not None
            
            return AgentResponse(
                agent_type=AgentType.AUTHENTICATION,
                message=response_text,
                handoff_request=handoff_request,
                completed=completed
            )
            
        except Exception as e:
            print(f"❌ Error in Authentication Agent: {e}")
            return AgentResponse(
                agent_type=AgentType.AUTHENTICATION,
                message=f"I'm sorry, I encountered an error processing your request: {str(e)}",
                handoff_request=None,
                completed=False
            )
        finally:
            # Clear current run
            self.current_run = None
    
    def _handle_auth_function(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle authentication function calls"""
        try:
            if function_name == "verify_member_identity":
                member_id = function_args["member_id"]
                dob = function_args["date_of_birth"]
                
                print(f"🔍 Verifying identity: Member {member_id}, DOB {dob}")
                
                # Demo authentication logic
                if member_id == "DEMO123456" and dob == "1985-03-15":
                    result = {
                        "verified": True,
                        "member_id": member_id,
                        "name": "Demo User",
                        "plan_id": "DEMO_PLAN_001",
                        "needs_mfa": False  # Skip MFA for demo
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
