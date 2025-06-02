#!/usr/bin/env python3
"""
Test script to verify handoff context passing is working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_coordinator import MultiAgentCoordinator
from pricing_agent import PricingAgent
from openai import OpenAI
import keys

def test_handoff_context():
    """Test that context is properly passed between agents during handoffs"""
    
    print("🧪 Testing Handoff Context Passing")
    print("=" * 50)
    
    # Initialize coordinator and agents
    coordinator = MultiAgentCoordinator()
    
    # Create and register pricing agent (simulates the flow)
    client = OpenAI(api_key=keys.OPENAI_API_KEY)
    pricing_agent = PricingAgent(client)
    coordinator.register_agent(pricing_agent)
    
    # Simulate a conversation that should trigger handoff
    test_messages = [
        "I need help with drug pricing",
        "Now I need to check my prescription status"  # This should trigger handoff to pharmacy
    ]
    
    print("\n📝 Testing conversation flow:")
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Message {i}: {message} ---")
        
        # Collect full response
        response_parts = []
        for chunk in coordinator.process_message(message):
            response_parts.append(chunk)
            print(chunk, end="", flush=True)
        
        print(f"\n\n📊 After message {i}:")
        print(f"Current agent: {coordinator.current_agent.value}")
        print(f"Conversation history length: {len(coordinator.conversation_history)}")
        
        # Show last few conversation entries
        print("Last conversation entries:")
        for entry in coordinator.conversation_history[-3:]:
            role = entry.get("role", "unknown")
            agent = entry.get("agent", "")
            content = entry.get("content", "")[:100] + "..." if len(entry.get("content", "")) > 100 else entry.get("content", "")
            print(f"  {role} ({agent}): {content}")
        
        print("-" * 30)
    
    print("\n✅ Test completed")

if __name__ == "__main__":
    test_handoff_context()
