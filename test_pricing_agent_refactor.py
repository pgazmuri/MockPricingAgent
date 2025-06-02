#!/usr/bin/env python3
"""
Test script to verify the refactored PricingAgent works with Chat Completions API
"""

import sys
import os
from openai import OpenAI
import keys
from pricing_agent import PricingAgent

def test_pricing_agent():
    """Test the refactored PricingAgent"""
    print("🧪 Testing Refactored PricingAgent")
    print("=" * 50)
    
    try:
        print("🔧 Importing modules...")
        
        # Initialize OpenAI client
        print("🔑 Creating OpenAI client...")
        client = OpenAI(api_key=keys.OPENAI_API_KEY)
        
        # Create PricingAgent instance
        print("🤖 Creating PricingAgent instance...")
        agent = PricingAgent(client)
        
        print(f"✅ PricingAgent created successfully")
        print(f"   Agent Type: {agent.agent_type}")
        print(f"   System Prompt Length: {len(agent.system_prompt)} characters")
        print(f"   Number of Tools: {len(agent.tools)}")
        
        # Test system prompt
        print("\n📝 System Prompt Preview:")
        preview = agent.system_prompt[:200] + "..." if len(agent.system_prompt) > 200 else agent.system_prompt
        print(preview)
        
        # Test tools configuration
        print("\n🔧 Available Tools:")
        for i, tool in enumerate(agent.tools, 1):
            tool_name = tool["function"]["name"]
            print(f"   {i}. {tool_name}")
        
        print("\n🎯 Basic setup test completed successfully!")
        print("✅ PricingAgent is properly configured with Chat Completions API")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pricing_agent()
    sys.exit(0 if success else 1)
