#!/usr/bin/env python3
"""
Quick test of the IT Operations multi-agent system
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.it_ops_tools import ITOpsTools
from agents.investigator_agent import InvestigatorAgent
from openai import OpenAI
import config.keys as keys

def test_it_ops_tools():
    """Test the IT operations tools"""
    print("🔧 Testing IT Operations Tools...")
    
    # Initialize tools
    client = OpenAI(api_key=keys.OPENAI_API_KEY)
    tools = ITOpsTools(client)
    
    # Test Splunk search
    print("\n🔍 Testing Splunk search...")
    result = tools.splunk_search(
        query="index=main host=server01 ERROR",
        time_frame="last 4 hours",
        context="Server ABC was shut down, investigating connectivity issues"
    )
    
    if "error" in result:
        print(f"❌ Splunk test failed: {result['error']}")
    else:
        print(f"✅ Splunk search found {result.get('results_count', 0)} events")
        print(f"📝 Summary: {result.get('summary', 'No summary')}")
    
    # Test flow logs
    print("\n🌐 Testing flow logs...")
    result = tools.check_flow_logs(
        vm_name="VM-Web01",
        time_frame="last 24 hours",
        context="Server having connectivity issues, SQL port 1433 blocked"
    )
    
    if "error" in result:
        print(f"❌ Flow logs test failed: {result['error']}")
    else:
        denied_count = len(result.get('denied_connections', []))
        print(f"✅ Flow logs check found {denied_count} denied connections")
        print(f"📝 Analysis: {result.get('summary', 'No analysis')}")
    
    print("\n✅ IT Operations Tools test completed!")

def test_investigator_agent():
    """Test the investigator agent"""
    print("\n🔍 Testing Investigator Agent...")
    
    client = OpenAI(api_key=keys.OPENAI_API_KEY)
    agent = InvestigatorAgent(client)
    
    print(f"✅ Investigator Agent initialized: {agent.agent_name} {agent.agent_emoji}")
    print(f"📊 Available tools: {len(agent.tools)}")
    
    # List available tools
    tool_names = [tool['function']['name'] for tool in agent.tools if tool['type'] == 'function']
    print(f"🔧 Tools: {', '.join(tool_names)}")
    
    print("✅ Investigator Agent test completed!")

if __name__ == "__main__":
    print("🚀 IT Operations Multi-Agent System Test")
    print("=" * 50)
    
    try:
        test_it_ops_tools()
        test_investigator_agent()
        
        print("\n🎉 All tests completed successfully!")
        print("\n💡 You can now run the full application with:")
        print("   python multi_agent_app.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
