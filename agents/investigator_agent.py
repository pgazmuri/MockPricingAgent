"""
IT Investigator Agent

Specialized agent for investigating server and application outages using IT operations tools.
Can search Splunk logs, check flow logs, review ServiceNow tickets, and analyze deployments.
"""

import json
import time
from typing import Dict, Any, Optional, List
from core.agent_coordinator import BaseAgent, AgentType
from openai import OpenAI
from core.shared_prompts import get_shared_context_awareness, get_shared_handoff_rules
from core.it_environment import ITEnvironment
from core.session_context import SessionContext
from services.it_ops_tools import (
    ITOpsTools, 
    get_splunk_search_tool,
    get_check_flow_logs_tool, 
    get_check_snow_tickets_tool,
    get_deployments_tool
)


class InvestigatorAgent(BaseAgent):
    """Specialized agent for IT outage investigation"""
    def __init__(self, client: OpenAI, session_context: SessionContext = None, model: str = "gpt-4.1"):
        super().__init__(client, AgentType.INVESTIGATOR, model=model)
        
        # Set agent-specific properties
        self.agent_name = "Investigator"
        self.agent_emoji = "🔍"
        
        # Use provided session context or create new one
        self.session_context = session_context or SessionContext()
        self.it_tools = ITOpsTools(client, self.session_context)
        
        # Initialize configuration
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the investigator agent"""
        
        # Get IT environment knowledge
        splunk_context = ITEnvironment.get_splunk_context()
        investigation_patterns = ITEnvironment.get_investigation_patterns()
        
        base_prompt = f"""
You are a friendly IT investigator who helps operations staff gather information about server and application outages.
Your role is DATA GATHERING ONLY - you collect evidence but don't determine root causes (that's for the Analysis agent).

{splunk_context}

{investigation_patterns}

YOUR INVESTIGATION STYLE:
- Be conversational and helpful, like talking to a colleague who needs assistance
- Ask natural questions: "Do you know which server is having issues?" instead of "Provide the server name"
- Gather information step by step, explaining what you're looking for as you go
- When you find obvious next steps, just do them (don't ask permission for logical follow-ups)
- Focus on collecting facts, not analyzing what they mean

INVESTIGATION WORKFLOW:
1. Ask friendly questions to understand the problem scope. If the user doesn't know specifics: look for related issues in splunk logs.
2. Once you have a server/service name, start gathering data automatically:
   - Check server heartbeat status first
   - Look for recent deployments (within last few hours)
   - Search for application errors around the problem time
   - Check ServiceNow for maintenance windows or known issues

EXAMPLE CONVERSATION STYLE:
❌ "Please provide the server name and timeframe for investigation"
✅ "Do you know which server is having problems? Once I have that, I can start looking through the logs"

❌ "Analysis suggests the deployment caused the issue"
✅ "I found a deployment 30 minutes before the issue started. Let me hand this over to Analysis to figure out if it's related"

WHEN TO GATHER MORE DATA vs HAND OFF:
- Keep investigating if: You have obvious next data sources to check
- AUTOMATICALLY hand off to ANALYSIS when: You have sufficient evidence from 2-3 different sources (logs, deployments, tickets, network)
- Don't ask "Should I hand this off?" - just do it when you have enough data for analysis
- Example: "I've gathered data from Splunk logs, checked recent deployments, and reviewed ServiceNow tickets. Let me hand this over to Analysis to determine the root cause."

TOOL USAGE:
- Always use realistic server names like WEB-PROD-01, SQL-PROD-02, APP-DEV-01
- Explain what you're searching for before running each tool
- Share interesting findings as you discover them, but don't draw conclusions
"""
        
        # Shared context awareness and handoff rules
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.INVESTIGATOR)
        
        investigation_guidelines = """
INVESTIGATION GUIDELINES:
- Start with friendly questions to understand the problem
- Use tools to gather data, explaining what you're looking for
- Share findings without analyzing root causes
- When you have sufficient data from multiple sources, hand off to ANALYSIS
- Never ask permission for obvious next investigation steps
- Be conversational and collaborative, not robotic or demanding
"""
        
        return base_prompt + context_awareness + handoff_rules + investigation_guidelines
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the investigator agent"""
        base_tools = [
            get_splunk_search_tool(),
            get_check_flow_logs_tool(),
            get_check_snow_tickets_tool(),
            get_deployments_tool()
        ]
        
        # Add the handoff tool from base class
        handoff_tool = self.get_handoff_tool()
        if handoff_tool:
            base_tools.append(handoff_tool)
        
        return base_tools
    
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls for IT investigation"""
        try:
            if function_name == "splunk_search":
                query = function_args.get("query", "")
                time_frame = function_args.get("time_frame", "last 24 hours")
                context = function_args.get("context", "")
                
                print(f"🔍 Searching Splunk: {query} ({time_frame})")
                
                result = self.it_tools.splunk_search(query, time_frame, context)
                
                if "error" in result:
                    print(f"❌ Splunk Error: {result['error']}")
                else:
                    print(f"📊 Found {result.get('results_count', 0)} events")
                    if result.get('events'):
                        print(f"📝 Summary: {result.get('summary', 'No summary available')}")
                
                return json.dumps(result)
            
            elif function_name == "check_flow_logs":
                vm_name = function_args.get("vm_name", "")
                time_frame = function_args.get("time_frame", "last 24 hours")
                context = function_args.get("context", "")
                
                print(f"🌐 Checking flow logs for {vm_name} ({time_frame})")
                
                result = self.it_tools.check_flow_logs(vm_name, time_frame, context)
                
                if "error" in result:
                    print(f"❌ Flow Log Error: {result['error']}")
                else:
                    denied_count = len(result.get('denied_connections', []))
                    print(f"🚫 Found {denied_count} denied connections")
                    if result.get('summary'):
                        print(f"📝 Analysis: {result['summary']}")
                
                return json.dumps(result)
            
            elif function_name == "check_snow_tickets":
                vm_name = function_args.get("vm_name", "")
                time_frame = function_args.get("time_frame", "last 7 days")
                context = function_args.get("context", "")
                
                print(f"🎫 Checking ServiceNow tickets for {vm_name} ({time_frame})")
                
                result = self.it_tools.check_snow_tickets(vm_name, time_frame, context)
                
                if "error" in result:
                    print(f"❌ ServiceNow Error: {result['error']}")
                else:
                    ticket_count = result.get('tickets_found', 0)
                    print(f"📋 Found {ticket_count} related tickets")
                    if result.get('summary'):
                        print(f"📝 Summary: {result['summary']}")
                
                return json.dumps(result)
            
            elif function_name == "get_deployments":
                vm_name = function_args.get("vm_name", "")
                time_frame = function_args.get("time_frame", "last 7 days")
                context = function_args.get("context", "")
                
                print(f"🚀 Checking deployments for {vm_name} ({time_frame})")
                
                result = self.it_tools.get_deployments(vm_name, time_frame, context)
                
                if "error" in result:
                    print(f"❌ Deployment Error: {result['error']}")
                else:
                    deployment_count = result.get('deployments_found', 0)
                    print(f"🔧 Found {deployment_count} deployments")
                    if result.get('summary'):
                        print(f"📝 Summary: {result['summary']}")
                
                return json.dumps(result)
            
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
