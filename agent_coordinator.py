"""
Multi-Agent Coordinator

This module manages multiple specialized agents and handles conversation handoffs
between them based on user intent and conversation context.
"""

import json
import time
from typing import List, Dict, Any, Optional
from enum import Enum
from openai import OpenAI
from dataclasses import dataclass
import keys

class AgentType(Enum):
    """Types of specialized agents"""
    COORDINATOR = "coordinator"
    PRICING = "pricing"
    AUTHENTICATION = "authentication"
    PHARMACY = "pharmacy"
    BENEFITS = "benefits"
    CLINICAL = "clinical"

@dataclass
class HandoffRequest:
    """Request to hand off conversation to another agent"""
    from_agent: AgentType
    to_agent: AgentType
    context: Dict[str, Any]
    reason: str
    user_message: str

@dataclass
class AgentResponse:
    """Response from an agent"""
    agent_type: AgentType
    message: str
    handoff_request: Optional[HandoffRequest] = None
    function_calls: List[Dict[str, Any]] = None
    completed: bool = False

class BaseAgent:
    """Base class for all specialized agents"""
    
    def __init__(self, client: OpenAI, agent_type: AgentType):
        self.client = client
        self.agent_type = agent_type
        self.assistant = None
        self.thread = None
        self.current_run = None
        
    def create_assistant(self) -> None:
        """Create the OpenAI assistant - to be implemented by subclasses"""
        raise NotImplementedError
    
    def process_message(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process a message and return response with potential handoff"""
        raise NotImplementedError
    
    def _wait_for_run_completion(self, run, thread_id: str):
        """Wait for a run to complete and handle any errors"""
        max_retries = 30  # 30 * 0.2s = 6 seconds max wait
        retries = 0
        
        while run.status in ['queued', 'in_progress', 'requires_action'] and retries < max_retries:
            time.sleep(0.2)
            retries += 1
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            except Exception as e:
                print(f"❌ Error retrieving run status: {e}")
                break
        
        if run.status in ['failed', 'cancelled', 'expired']:
            print(f"❌ Run failed with status: {run.status}")
            if hasattr(run, 'last_error') and run.last_error:
                print(f"❌ Error details: {run.last_error}")
        
        return run
    
    def _ensure_thread_ready(self):
        """Ensure the thread is ready for new messages"""
        if self.current_run:
            try:
                # Check if there's an active run
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=self.current_run.id
                )
                
                if run_status.status in ['queued', 'in_progress', 'requires_action']:
                    print(f"⏳ Waiting for previous run to complete...")
                    self._wait_for_run_completion(run_status, self.thread.id)
                
            except Exception as e:
                print(f"⚠️ Error checking run status: {e}")
            finally:
                self.current_run = None

class MultiAgentCoordinator:
    """Coordinates multiple agents and manages handoffs"""
    def __init__(self):
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.conversation_context = {}
        self.current_agent = AgentType.COORDINATOR
        self.conversation_history = []
        
        # Initialize coordinator assistant
        self.coordinator_assistant = None
        self.coordinator_thread = None
        self.coordinator_current_run = None  # Track coordinator's current run
        self._create_coordinator()
        
    def _create_coordinator(self):
        """Create the main coordinator assistant"""
        instructions = """
You are a smart coordinator for a healthcare/pharmacy system with multiple specialized agents.

Your job is to:
1. Understand user intent and determine which specialized agent should handle the request
2. Collect any missing information needed for handoffs
3. Provide smooth transitions between agents
4. Maintain conversation context

AVAILABLE AGENTS:
- PRICING: Drug cost calculations, insurance benefits, pricing estimates
- AUTHENTICATION: Member verification, login, security checks  
- PHARMACY: Prescription status, refills, transfers, pickup notifications
- BENEFITS: Plan details, coverage rules, prior authorizations
- CLINICAL: Drug interactions, alternatives, clinical criteria

HANDOFF RULES:
- Start with AUTHENTICATION if user needs member-specific services
- Use PRICING for cost/pricing questions
- Use PHARMACY for prescription management
- Use BENEFITS for plan/coverage questions
- Use CLINICAL for medical/drug interaction questions

Always be friendly and explain transitions: "Let me connect you with our pricing specialist..."

You have access to a special function 'request_handoff' to transfer conversations.
"""
        self.coordinator_assistant = self.client.beta.assistants.create(
            name="Healthcare Coordinator",
            instructions=instructions,
            model="gpt-4.1-mini",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "request_handoff",
                        "description": "Hand off conversation to a specialized agent",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "agent_type": {
                                    "type": "string",
                                    "enum": ["pricing", "authentication", "pharmacy", "benefits", "clinical"],
                                    "description": "Which agent to hand off to"
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "Why this handoff is needed"
                                },
                                "context_summary": {
                                    "type": "string",
                                    "description": "Summary of conversation context for the receiving agent"
                                }
                            },
                            "required": ["agent_type", "reason", "context_summary"]
                        }
                    }
                }
            ]
        )
        
        self.coordinator_thread = self.client.beta.threads.create()
    def _ensure_coordinator_thread_ready(self):
        """Ensure the coordinator thread is ready for new messages"""
        if self.coordinator_current_run:
            try:
                # Check if there's an active run
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.coordinator_thread.id,
                    run_id=self.coordinator_current_run.id
                )
                
                if run_status.status in ['queued', 'in_progress', 'requires_action']:
                    print(f"⏳ Waiting for previous coordinator run to complete...")
                    # Use the same wait pattern as BaseAgent
                    self._wait_for_coordinator_run_completion(run_status, self.coordinator_thread.id)
                
            except Exception as e:
                print(f"⚠️ Error checking coordinator run status: {e}")
            finally:
                self.coordinator_current_run = None
    
    def _wait_for_coordinator_run_completion(self, run, thread_id: str):
        """Wait for a coordinator run to complete and handle any errors"""
        max_retries = 30  # 30 * 0.2s = 6 seconds max wait
        retries = 0
        
        while run.status in ['queued', 'in_progress', 'requires_action'] and retries < max_retries:
            time.sleep(0.2)
            retries += 1
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            except Exception as e:
                print(f"❌ Error retrieving coordinator run status: {e}")
                break
        
        # CHECK FOR TIMEOUT
        if retries >= max_retries and run.status in ['queued', 'in_progress', 'requires_action']:
            print(f"⏰ TIMEOUT: Coordinator run {run.id} did not complete in {max_retries * 0.2}s")
            print(f"📊 Final status: {run.status}")
            # Optionally cancel the run
            try:
                self.client.beta.threads.runs.cancel(
                    thread_id=thread_id,
                    run_id=run.id
                )
                print(f"🛑 Cancelled timed-out run {run.id}")
            except Exception as e:
                print(f"⚠️ Could not cancel run: {e}")
        
        if run.status in ['failed', 'cancelled', 'expired']:
            print(f"❌ Coordinator run failed with status: {run.status}")
            if hasattr(run, 'last_error') and run.last_error:
                print(f"❌ Error details: {run.last_error}")
        
        return run
    
    def register_agent(self, agent: BaseAgent):
        """Register a specialized agent"""
        self.agents[agent.agent_type] = agent
        print(f"🤖 Registered {agent.agent_type.value} agent")    
    def process_message(self, user_message: str) -> str:
        """Process user message and coordinate between agents"""
        print(f"\n👤 User: {user_message}")
        print(f"🎛️ Current agent: {self.current_agent.value}")
        
        # Comprehensive diagnostic information
        # print(f"🔍 === SYSTEM STATE DIAGNOSTICS ===")
        # print(f"🏠 Coordinator thread ID: {self.coordinator_thread.id if self.coordinator_thread else 'None'}")
        # print(f"🎛️ Coordinator run: {self.coordinator_current_run.id if self.coordinator_current_run else 'None'}")
        
        # Check coordinator thread for active runs
        if self.coordinator_thread:
            try:
                active_runs = self.client.beta.threads.runs.list(
                    thread_id=self.coordinator_thread.id,
                    limit=5
                )
                print(f"📋 Coordinator active runs:")
                for run in active_runs.data:
                    print(f"   - Run {run.id}: {run.status}")
            except Exception as e:
                print(f"❌ Error checking coordinator runs: {e}")
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user", 
            "content": user_message,
            "timestamp": time.time()
        })
        
        # Include conversation history in context
        self.conversation_context["conversation_history"] = self.conversation_history.copy()
        
        # If we're currently with a specialized agent, try them first
        if self.current_agent != AgentType.COORDINATOR and self.current_agent in self.agents:
            current_agent = self.agents[self.current_agent]
            # print(f"🔍 Checking if {self.current_agent.value} agent can handle message...")
            print(f"📍 Current agent: {current_agent.agent_type}")
            # print(f"🧵 Agent thread ID: {current_agent.thread.id if current_agent.thread else 'None'}")
            # print(f"🏃 Agent run: {current_agent.current_run.id if current_agent.current_run else 'None'}")
            
           
            print(f"🎯 Continuing conversation with {self.current_agent.value} agent...")
                
            # Check for active runs before processing
            if hasattr(current_agent, 'current_run') and current_agent.current_run:
                print(f"⚠️ FOUND ACTIVE RUN in {self.current_agent.value} agent - this could cause the error!")
                try:
                    run_status = current_agent.client.beta.threads.runs.retrieve(
                        thread_id=current_agent.thread.id,
                        run_id=current_agent.current_run.id
                    )
                    print(f"📊 Run status: {run_status.status}")
                    
                    # If the run is still active, wait for it to complete
                    if run_status.status in ['queued', 'in_progress', 'requires_action']:
                        print(f"⏳ WAITING for active run to complete before processing new message...")
                        # Call the agent's _ensure_thread_ready method to wait for completion
                        current_agent._ensure_thread_ready()
                        print(f"✅ Previous run completed, now processing new message")
                    
                except Exception as e:
                    print(f"❌ Error checking run status: {e}")
			
            response = current_agent.process_message(user_message, self.conversation_context)
            return self._handle_agent_response(response)
          # Otherwise, use coordinator to determine routing
        print(f"🎛️ Using coordinator to route message...")
        return self._coordinate_request(user_message)
    
    def _coordinate_request(self, user_message: str) -> str:
        """Use coordinator to determine which agent should handle the request"""
        print(f"🎛️ Coordinator analyzing request...")
        # print(f"🔍 === COORDINATOR DIAGNOSTICS ===")
        # print(f"🏠 Thread ID: {self.coordinator_thread.id}")
        # print(f"🎛️ Current run: {self.coordinator_current_run.id if self.coordinator_current_run else 'None'}")
        
        try:
            # Ensure coordinator thread is ready for new messages
            print(f"⏳ Ensuring coordinator thread is ready...")
            self._ensure_coordinator_thread_ready()
            print(f"✅ Coordinator thread ready")
            
            # Create a summary of conversation history for the coordinator
            history_summary = self._create_history_summary()
            
            # Add user message to coordinator thread
            print(f"📝 Adding message to coordinator thread...")
            self.client.beta.threads.messages.create(
                thread_id=self.coordinator_thread.id,
                role="user",
                content=f"User request: {user_message}\n\nCurrent context: {json.dumps(self.conversation_context)}\n\nConversation history:\n{history_summary}"
            )
            print(f"✅ Message added to coordinator thread")
            
            # Run coordinator
            print(f"🚀 Creating coordinator run...")
            run = self.client.beta.threads.runs.create(
                thread_id=self.coordinator_thread.id,
                assistant_id=self.coordinator_assistant.id
            )
            print(f"✅ Coordinator run created: {run.id}")
            
            # Track current run
            self.coordinator_current_run = run
            
            # Wait for completion with proper thread management
            max_retries = 30  # 30 * 0.2s = 6 seconds max wait
            retries = 0
            
            while run.status in ['queued', 'in_progress', 'requires_action'] and retries < max_retries:
                time.sleep(0.2)
                retries += 1
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.coordinator_thread.id,
                    run_id=run.id
                )
                
                if run.status == 'requires_action':
                    return self._handle_coordinator_actions(run, user_message)
            
            # Check for errors
            if run.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Coordinator run failed: {run.status}")
                return "I'm sorry, I'm having trouble processing your request right now. Please try again."
              # Get coordinator response if no handoff
            messages = self.client.beta.threads.messages.list(
                thread_id=self.coordinator_thread.id,
                order="desc",
                limit=1
            )
            
            response_text = messages.data[0].content[0].text.value
            print(f"🎛️ Coordinator: {response_text}")
            return response_text
            
        except Exception as e:
            print(f"❌ Error in coordinator: {e}")
            return "I'm sorry, I encountered an error while processing your request. Please try again."
        finally:
            # Clear coordinator run tracking
            self.coordinator_current_run = None
    def _handle_coordinator_actions(self, run, user_message: str) -> str:
        """Handle coordinator function calls (handoffs)"""
        print(f"🔄 === HANDOFF PROCESSING ===")
        # print(f"🎛️ Coordinator run: {run.id}")
        # print(f"🏠 Coordinator thread: {self.coordinator_thread.id}")
        
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "request_handoff":
                agent_type_str = function_args["agent_type"]
                reason = function_args["reason"]
                context_summary = function_args["context_summary"]
                
                print(f"🔄 Handoff requested: {agent_type_str} - {reason}")
                print(f"📋 Context summary: {context_summary}")
                
                # Update context with handoff info and ensure history is included
                self.conversation_context["handoff_reason"] = reason
                self.conversation_context["context_summary"] = context_summary
                self.conversation_context["conversation_history"] = self.conversation_history.copy()
                self.conversation_context["previous_agent"] = self.current_agent.value
                
                # Perform handoff
                target_agent_type = AgentType(agent_type_str)
                if target_agent_type in self.agents:
                    print(f"🎯 Transferring to {agent_type_str} agent...")
                    self.current_agent = target_agent_type
                    target_agent = self.agents[target_agent_type]
                    
                    # Add current agent type to conversation context for tracking (not the object itself)
                    self.conversation_context["current_agent_type"] = agent_type_str
                    
                    # Check target agent thread state before processing
                    print(f"🔍 === TARGET AGENT DIAGNOSTICS ===")
                    print(f"🎯 Agent: {target_agent.agent_type}")
                    print(f"🧵 Thread ID: {target_agent.thread.id if target_agent.thread else 'None'}")
                    print(f"🏃 Current run: {target_agent.current_run.id if target_agent.current_run else 'None'}")
                    
                    if target_agent.thread:
                        try:
                            active_runs = self.client.beta.threads.runs.list(
                                thread_id=target_agent.thread.id,
                                limit=5
                            )
                            print(f"📋 Target agent active runs:")
                            for run_info in active_runs.data:
                                print(f"   - Run {run_info.id}: {run_info.status}")
                        except Exception as e:
                            print(f"❌ Error checking target agent runs: {e}")
                    
                    # Process message with target agent
                    print(f"🚀 Processing message with {agent_type_str} agent...")
                    response = target_agent.process_message(user_message, self.conversation_context)
                    result = self._handle_agent_response(response)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps({"status": "handoff_completed", "response": result})
                    })
                    
                    return result
                else:
                    error_msg = f"Agent {agent_type_str} not available"
                    print(f"❌ {error_msg}")
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps({"error": error_msg})
                    })
          # Submit tool outputs and continue
        try:
            run = self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.coordinator_thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            
            # Wait for final response - include requires_action in case of multiple function calls
            max_retries = 30
            retries = 0
            while run.status in ['queued', 'in_progress', 'requires_action'] and retries < max_retries:
                time.sleep(0.2)
                retries += 1
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.coordinator_thread.id,
                    run_id=run.id
                )
                
                # Handle additional function calls if needed
                if run.status == 'requires_action':
                    print("⚠️ Coordinator needs additional actions - this shouldn't happen in normal handoffs")
                    break
            
            # Check for completion errors
            if run.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Coordinator action run failed: {run.status}")
                return "I'm sorry, there was an issue completing the handoff. Please try again."
            
            if retries >= max_retries:
                print("❌ Coordinator action run timed out")
                return "I'm sorry, the request took too long to process. Please try again."
            
            # Get final response
            messages = self.client.beta.threads.messages.list(
                thread_id=self.coordinator_thread.id,
                order="desc",
                limit=1
            )
            
            return messages.data[0].content[0].text.value
            
        except Exception as e:
            print(f"❌ Error in coordinator action handling: {e}")
            return "I'm sorry, I encountered an error while processing your request. Please try again."
    
    def _handle_agent_response(self, response: AgentResponse) -> str:
        """Handle response from a specialized agent"""
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "agent": response.agent_type.value,
            "content": response.message,
            "timestamp": time.time()
        })
        
        # Handle any handoff requests
        if response.handoff_request:
            handoff = response.handoff_request
            print(f"🔄 Agent {handoff.from_agent.value} requesting handoff to {handoff.to_agent.value}: {handoff.reason}")
            
            if handoff.to_agent in self.agents:
                self.current_agent = handoff.to_agent
                # Merge handoff context with existing context, ensuring history is preserved
                self.conversation_context.update(handoff.context)
                self.conversation_context["conversation_history"] = self.conversation_history.copy()
                self.conversation_context["handoff_chain"] = self.conversation_context.get("handoff_chain", []) + [
                    {
                        "from": handoff.from_agent.value,
                        "to": handoff.to_agent.value,
                        "reason": handoff.reason,
                        "timestamp": time.time()
                    }
                ]
                
                # Process with new agent
                new_response = self.agents[handoff.to_agent].process_message(
                    handoff.user_message, self.conversation_context
                )
                return self._handle_agent_response(new_response)
            else:
                # Fall back to coordinator
                self.current_agent = AgentType.COORDINATOR
                return f"{response.message}\n\nI'll need to connect you with another specialist, but that service isn't available right now."
        
        # If agent completed its task, return to coordinator
        if response.completed:
            self.current_agent = AgentType.COORDINATOR
            print(f"✅ {response.agent_type.value} agent completed task, returning to coordinator")
        
        return response.message
    
    def _create_history_summary(self) -> str:
        """Create a formatted summary of conversation history"""
        if not self.conversation_history:
            return "No previous conversation history."
        
        summary_lines = []
        for entry in self.conversation_history[-10:]:  # Last 10 messages for context
            if entry["role"] == "user":
                summary_lines.append(f"User: {entry['content']}")
            else:
                agent_name = entry.get("agent", "Unknown")
                summary_lines.append(f"{agent_name}: {entry['content']}")
        
        return "\n".join(summary_lines)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation state"""
        return {
            "current_agent": self.current_agent.value,
            "context": self.conversation_context,
            "history_length": len(self.conversation_history),
            "available_agents": [agent.value for agent in self.agents.keys()],
            "recent_history": self.conversation_history[-5:] if self.conversation_history else []
        }
    
    def cleanup_assistants(self):
        """Clean up all assistants at the API level to prevent resource leaks"""
        print("🧹 Cleaning up assistants...")
        
        try:
            # Clean up coordinator assistant
            if self.coordinator_assistant:
                self.client.beta.assistants.delete(self.coordinator_assistant.id)
                print(f"✅ Deleted coordinator assistant {self.coordinator_assistant.id}")
                self.coordinator_assistant = None
            
            # Clean up agent assistants
            for agent_type, agent in self.agents.items():
                if hasattr(agent, 'assistant') and agent.assistant:
                    try:
                        self.client.beta.assistants.delete(agent.assistant.id)
                        print(f"✅ Deleted {agent_type.value} assistant {agent.assistant.id}")
                        agent.assistant = None
                    except Exception as e:
                        print(f"⚠️ Error deleting {agent_type.value} assistant: {e}")
                        
        except Exception as e:
            print(f"❌ Error during assistant cleanup: {e}")
    
    def __del__(self):
        """Cleanup when coordinator is destroyed"""
        try:
            self.cleanup_assistants()
        except:
            pass  # Ignore errors during destruction
