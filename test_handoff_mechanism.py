#!/usr/bin/env python3
"""
Test the handoff mechanism in the refactored pricing agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI
import keys
from agent_coordinator import MultiAgentCoordinator, AgentType
from pricing_agent import PricingAgent

def test_handoff_mechanism():
    """Test that handoffs work properly"""
    print("🧪 Testing handoff mechanism...")
    
    # Create coordinator and pricing agent
    coordinator = MultiAgentCoordinator()
    client = OpenAI(api_key=keys.OPENAI_API_KEY)
    pricing_agent = PricingAgent(client)
    
    # Register the pricing agent
    coordinator.register_agent(pricing_agent)
    
    # Test message that should trigger a handoff
    test_message = "I need to login to check my prescription status"
    
    print(f"\n📤 Sending test message: '{test_message}'")
    print("🔄 Expected: Should hand off to authentication agent\n")
    
    # Process the message through coordinator
    response_chunks = []
    try:
        for chunk in coordinator.process_message(test_message):
            response_chunks.append(chunk)
            print(chunk, end='', flush=True)
        
        print(f"\n\n✅ Response completed")
        print(f"📊 Current agent: {coordinator.current_agent.value}")
        print(f"📊 Pending handoff: {coordinator.pending_handoff is not None}")
        
        if coordinator.pending_handoff:
            handoff = coordinator.pending_handoff
            print(f"🔄 Handoff details:")
            print(f"   From: {handoff.from_agent.value}")
            print(f"   To: {handoff.to_agent.value}")
            print(f"   Reason: {handoff.reason}")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_handoff_mechanism()
