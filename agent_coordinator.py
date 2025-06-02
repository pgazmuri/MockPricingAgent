"""
Multi-Agent Coordinator

This module manages multiple specialized agents and handles conversation handoffs
between them based on user intent and conversation context.

Now uses OpenAI Completion API with streaming instead of Assistant API.
"""

import json
import time
from typing import List, Dict, Any, Optional, Iterator, Generator
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
    """Base class for all specialized agents using Completion API with streaming"""
    
    def __init__(self, client: OpenAI, agent_type: AgentType, coordinator=None, model: str = "gpt-4o-mini"):
        self.client = client
        self.agent_type = agent_type
        self.coordinator = coordinator  # Reference to coordinator for handoffs
        self.model = model  # Allow each agent to specify its model
        self.conversation_history = []
        self.tools = []
        self.system_prompt = ""
          # Agent-specific properties (can be overridden by subclasses)
        self.agent_name = agent_type.value.title()
        self.agent_emoji = "🤖"
    
    def request_handoff(self, to_agent: AgentType, reason: str, context_summary: str, user_message: str):
        """Request a handoff to another agent"""
        if self.coordinator:
            # Merge local agent conversation history with coordinator history for complete context
            merged_history = self.coordinator.conversation_history.copy()
            
            # Add ALL messages from this agent's conversation history that aren't already in coordinator history
            for msg in self.conversation_history:
                if msg not in merged_history:
                    # Include all message types: user, assistant, tool, etc.
                    merged_history.append(msg)
            
            # Include full conversation history and current context in handoff
            handoff_context = {
                "summary": context_summary,
                "conversation_history": merged_history,
                "previous_agent": self.agent_type.value,
                "handoff_reason": reason
            }
            
            handoff_request = HandoffRequest(
                from_agent=self.agent_type,
                to_agent=to_agent,
                context=handoff_context,
                reason=reason,
                user_message=user_message
            )
            self.coordinator.pending_handoff = handoff_request
            print(f"🔄 {self.agent_type.value} agent requesting handoff to {to_agent.value}: {reason}")
    
    
    def create_agent(self) -> None:
        """Create the agent configuration - to be implemented by subclasses"""
        raise NotImplementedError
    
    def process_message(self, message: str, context: Dict[str, Any] = None) -> Iterator[str]:
        """Process a message and return streaming response with potential handoff, using a tool-call loop with 5-iteration failsafe."""
        agent_name = getattr(self, 'agent_name', self.agent_type.value.title())
        print(f"{getattr(self, 'agent_emoji', '🤖')} {agent_name} Agent processing: {message}")
        try:
            # Add user message to conversation history FIRST
            self.conversation_history.append({"role": "user", "content": message})
            # Build initial messages for completion
            messages = self._build_messages(message, context)
            tools = self.tools            
            for loop_count in range(5):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.7
                )
                msg = response.choices[0].message                # If tool calls, handle them
                if msg.tool_calls:
                    # Add assistant message with tool calls to conversation history first
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments
                                }
                            } for call in msg.tool_calls
                        ]
                    })
                    
                    for call in msg.tool_calls:
                        fn_name = call.function.name
                        fn_args = json.loads(call.function.arguments)
                        print(f"🔧 {agent_name} Agent calling: {fn_name} with {fn_args}")                        
                        if fn_name == "request_handoff":
                            agent_type_str = fn_args["agent_type"]
                            reason = fn_args["reason"]
                            context_summary = fn_args["context_summary"]
                            
                            # Add tool result to conversation history for handoff context
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": json.dumps({"handoff_requested": True, "reason": reason})
                            })
                            
                            self.request_handoff(
                                to_agent=AgentType(agent_type_str),
                                reason=reason,
                                context_summary=context_summary,
                                user_message=message
                            )
                            # Handoff happens silently - no message yielded, break from loop
                            return
                        else:
                            if hasattr(self, 'handle_tool_call'):
                                result = self.handle_tool_call(fn_name, fn_args)
                            else:
                                result = json.dumps({"error": f"No handler for function {fn_name}"})
                            # 3️⃣ feed the result back
                            messages.append({
                                "role": "assistant",
                                "content": msg.content,
                                "tool_calls": [
                                    {
                                        "id": call.id,
                                        "type": "function",
                                        "function": {
                                            "name": fn_name,
                                            "arguments": call.function.arguments
                                        }
                                    }
                                ]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": result
                            })
                    continue  # ask the model again
                else:
                    # No tool calls, yield the final answer
                    if msg.content:
                        self.conversation_history.append({"role": "assistant", "content": msg.content})
                        for word in msg.content.split():
                            yield word + " "
                        break
            else:
                # Failsafe: too many tool call loops
                yield "I'm sorry, I wasn't able to complete your request after several attempts. Please try again or rephrase."
        except Exception as e:
            print(f"❌ Error in {agent_name} Agent: {e}")
            yield f"I'm sorry, I encountered an error processing your request: {str(e)}"
    
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls - to be implemented by subclasses"""
        raise NotImplementedError(f"Agent must implement handle_tool_call for function: {function_name}")
    def _build_messages(self, message: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Build messages array for completion API"""
        messages = [{"role": "system", "content": self.system_prompt}]
          # Use conversation history from context (for handoffs) or local history
        conversation_history = []
        if context and "conversation_history" in context:
            # Use coordinator's conversation history for handoffs
            conversation_history = context["conversation_history"]  # Keep full conversation history
        else:
            # Use agent's local conversation history
            conversation_history = self.conversation_history  # Keep full conversation history
          # Add conversation history to messages
        for msg in conversation_history:
            if isinstance(msg, dict) and "role" in msg:
                # Handle different message types properly
                if msg["role"] == "assistant" and "tool_calls" in msg:
                    # Assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": msg.get("content"),
                        "tool_calls": msg["tool_calls"]
                    })
                elif msg["role"] == "tool":
                    # Tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": msg.get("tool_call_id"),
                        "content": msg.get("content", "")
                    })
                elif "content" in msg:
                    # Regular user/assistant message
                    messages.append({"role": msg["role"], "content": msg["content"]})
                # Skip messages without content or tool_calls (invalid messages)
            
        # Add handoff context if provided, including original request summary and reason
        if context:
            context_summary_parts = []
            # pick up summary under either key
            if "summary" in context:
                context_summary_parts.append(f"Original context summary: {context['summary']}")
            elif "context_summary" in context:
                context_summary_parts.append(f"Original context summary: {context['context_summary']}")
            # include explicit reason and previous agent
            if "handoff_reason" in context:
                context_summary_parts.append(f"Handoff reason: {context['handoff_reason']}")
            if "previous_agent" in context:
                context_summary_parts.append(f"Previous agent: {context['previous_agent']}")
            if context_summary_parts:
                context_msg = "\n".join(context_summary_parts)
                # insert immediately after system prompt for clarity
                messages.insert(1, {"role": "system", "content": context_msg})
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _stream_completion(self, messages: List[Dict[str, Any]]) -> Iterator[str]:
        """Stream completion from OpenAI"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools if self.tools else None,
                tool_choice="auto" if self.tools else None,
                stream=True,
                temperature=0.7
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"❌ Error in streaming completion: {e}")
            yield f"I'm sorry, I encountered an error: {str(e)}"

class MultiAgentCoordinator:
    """Coordinates multiple agents and manages handoffs using streaming completion API"""
    
    def __init__(self, coordinator_model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
        self.coordinator_model = coordinator_model  # Allow specifying coordinator model
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.conversation_context = {}
        self.current_agent = AgentType.COORDINATOR
        self.conversation_history = []
        self.pending_handoff: Optional[HandoffRequest] = None
        self.coordinator_tools = self._create_coordinator_tools()
        self.coordinator_system_prompt = self._create_coordinator_system_prompt()
    def _create_coordinator_system_prompt(self) -> str:
        """Create the coordinator system prompt"""
        return """
You are a smart coordinator for a healthcare/pharmacy system with multiple specialized agents.

Your ONLY job is to understand user intent and immediately hand off to the appropriate specialist. 
DO NOT respond to the user directly - ALWAYS use the request_handoff function immediately.

AVAILABLE AGENTS:
- PRICING: Drug cost calculations, insurance benefits, pricing estimates
- AUTHENTICATION: Member verification, login, security checks  
- PHARMACY: Prescription status, refills, transfers, pickup notifications
- BENEFITS: Plan details, coverage rules, prior authorizations
- CLINICAL: Drug interactions, alternatives, clinical criteria

HANDOFF RULES:
- For prescription refills, status, transfers, pickup → hand off to PHARMACY
- For authentication, login, verification → hand off to AUTHENTICATION  
- For drug costs, pricing, insurance → hand off to PRICING
- For plan details, coverage → hand off to BENEFITS
- For drug interactions, alternatives → hand off to CLINICAL

IMPORTANT: Never respond to the user directly. Always use request_handoff function immediately to transfer to the appropriate agent. The specialist will handle the actual response.
"""
    
    def _create_coordinator_tools(self) -> List[Dict[str, Any]]:
        """Create coordinator tools for handoffs"""
        return [
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
            }        ]
    
    def register_agent(self, agent: BaseAgent):
        """Register a specialized agent"""
        agent.coordinator = self  # Give agent reference to coordinator
        self.agents[agent.agent_type] = agent
        print(f"🤖 Registered {agent.agent_type.value} agent")
    
    def process_message(self, user_message: str) -> Iterator[str]:
        """Process user message and coordinate between agents with streaming"""
        print(f"\n👤 User: {user_message}")
        print(f"🎛️ Current agent: {self.current_agent.value}")
        
        # Clear any pending handoffs from previous interactions
        self.pending_handoff = None
        
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
            print(f"🎯 Continuing conversation with {self.current_agent.value} agent...")
            
            # Collect the agent's response
            agent_response_parts = []
            for chunk in current_agent.process_message(user_message, self.conversation_context):
                agent_response_parts.append(chunk)
                yield chunk
            
            # Add agent's response to coordinator conversation history
            if agent_response_parts:
                full_response = "".join(agent_response_parts).strip()
                if full_response:
                    self.conversation_history.append({
                        "role": "assistant",
                        "agent": self.current_agent.value,
                        "content": full_response,
                        "timestamp": time.time()
                    })
                  # Check for pending handoffs after streaming is complete
            if self.pending_handoff:
                # Process handoffs recursively to handle chained handoffs
                for chunk in self._process_handoff_chain(user_message):
                    yield chunk
            return
        
        # Otherwise, use coordinator to determine routing
        print(f"🎛️ Using coordinator to route message...")
        for chunk in self._coordinate_request(user_message):
            yield chunk
    
    def _coordinate_request(self, user_message: str) -> Iterator[str]:
        """Use coordinator to determine which agent should handle the request"""
        print(f"🎛️ Coordinator analyzing request...")
        
        try:
            # Create a summary of conversation history for the coordinator
            history_summary = self._create_history_summary()
            
            # Build messages for coordinator
            messages = [
                {"role": "system", "content": self.coordinator_system_prompt}
            ]
              # Add conversation history context
            context_message = f"User request: {user_message}\n\nCurrent context: {json.dumps(self.conversation_context)}\n\nConversation history:\n{history_summary}"
            messages.append({"role": "user", "content": context_message})
              
            # Try to get completion with tool calls - coordinator MUST use tools
            try:
                response = self.client.chat.completions.create(
                    model=self.coordinator_model,
                    messages=messages,
                    tools=self.coordinator_tools,
                    tool_choice="required",  # Force tool usage
                    temperature=0.7
                )
                
                # Check if there are tool calls (handoffs)
                if response.choices[0].message.tool_calls:
                    for tool_call in response.choices[0].message.tool_calls:
                        if tool_call.function.name == "request_handoff":
                            function_args = json.loads(tool_call.function.arguments)
                            agent_type_str = function_args["agent_type"]
                            reason = function_args["reason"]
                            context_summary = function_args["context_summary"]
                            
                            print(f"🔄 Handoff requested: {agent_type_str} - {reason}")
                            
                            # Update context with handoff info
                            self.conversation_context["handoff_reason"] = reason
                            self.conversation_context["context_summary"] = context_summary
                            self.conversation_context["previous_agent"] = self.current_agent.value                            # Perform handoff
                            target_agent_type = AgentType(agent_type_str)
                            if target_agent_type in self.agents:
                                print(f"🎯 Transferring to {agent_type_str} agent...")
                                self.current_agent = target_agent_type
                                target_agent = self.agents[target_agent_type]
                                
                                # Collect and stream response from target agent
                                target_response_parts = []
                                for chunk in target_agent.process_message(user_message, self.conversation_context):
                                    target_response_parts.append(chunk)
                                    yield chunk
                                
                                # Add target agent's response to coordinator conversation history
                                if target_response_parts:
                                    target_full_response = "".join(target_response_parts).strip()
                                    if target_full_response:
                                        self.conversation_history.append({
                                            "role": "assistant",
                                            "agent": target_agent_type.value,
                                            "content": target_full_response,
                                            "timestamp": time.time()
                                        })
                                
                                # Check for chained handoffs after initial handoff
                                if self.pending_handoff:
                                    for chunk in self._process_handoff_chain(user_message):
                                        yield chunk
                                return
                            else:
                                yield f"I'm sorry, the {agent_type_str} agent is not available right now."
                                return                
                # If no tool calls were made (shouldn't happen with tool_choice="required"), 
                # fallback to a generic response
                yield "I'm sorry, I couldn't understand your request. Could you please rephrase it?"
                return
                        
            except Exception as e:
                print(f"❌ Error in coordinator completion: {e}")
                yield "I'm sorry, I'm having trouble processing your request right now. Please try again."
        except Exception as e:
            print(f"❌ Error in coordinator: {e}")
            yield "I'm sorry, I encountered an error while processing your request. Please try again."
    
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

    def _add_to_conversation_history(self, role: str, content: str, agent_type: str = None):
        """Add message to conversation history"""
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        if agent_type:
            entry["agent"] = agent_type
        self.conversation_history.append(entry)
        
        # Keep all conversation history - no truncation
    
    def _create_history_summary(self) -> str:
        """Create a formatted summary of conversation history"""
        if not self.conversation_history:
            return "No previous conversation history."
        summary_lines = []
        for entry in self.conversation_history:  # Keep all conversation history
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
    
    def reset_conversation(self):
        """Reset conversation state but keep agents registered"""
        self.conversation_context = {}
        self.current_agent = AgentType.COORDINATOR
        self.conversation_history = []
        print("🔄 Conversation state reset")
    
    def switch_to_coordinator(self):
        """Manually switch back to coordinator"""
        self.current_agent = AgentType.COORDINATOR
        print("🎛️ Switched to coordinator")
    def _process_handoff_chain(self, original_message: str, max_handoffs: int = 3) -> Iterator[str]:
        """Process a chain of handoffs to handle cases where agents hand off to each other"""
        handoff_count = 0
        
        while self.pending_handoff and handoff_count < max_handoffs:
            handoff = self.pending_handoff
            self.pending_handoff = None  # Clear the handoff
            handoff_count += 1
            
            print(f"🔄 Processing handoff #{handoff_count} to {handoff.to_agent.value}: {handoff.reason}")
            
            # Perform the handoff
            if handoff.to_agent in self.agents:
                self.current_agent = handoff.to_agent
                # Update context with latest conversation history BEFORE handoff
                self.conversation_context.update(handoff.context)
                self.conversation_context["conversation_history"] = self.conversation_history.copy()
                
                # Continue with the new agent
                new_agent = self.agents[handoff.to_agent]
                new_agent_response_parts = []
                for chunk in new_agent.process_message(handoff.user_message, self.conversation_context):
                    new_agent_response_parts.append(chunk)
                    yield chunk
                
                # Add new agent's response to coordinator conversation history
                if new_agent_response_parts:
                    new_full_response = "".join(new_agent_response_parts).strip()
                    if new_full_response:
                        self.conversation_history.append({
                            "role": "assistant",
                            "agent": handoff.to_agent.value,
                            "content": new_full_response,
                            "timestamp": time.time()
                        })
                
                # Check if this agent also requested a handoff (chained handoff)
                # Continue the loop to process the next handoff
            else:
                yield f"\n\nI'm sorry, the {handoff.to_agent.value} agent is not available right now."
                break
        
        if handoff_count >= max_handoffs:
            print(f"⚠️ Maximum handoff chain limit ({max_handoffs}) reached")
            yield "\n\nI've transferred your request through multiple specialists. Please let me know if you need further assistance."
