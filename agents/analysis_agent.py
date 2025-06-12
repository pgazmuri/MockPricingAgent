"""
IT Analysis Agent

Specialized agent for analyzing investigation findings and recommending next steps.
Uses conversation history to determine root cause and suggest remediation plans.
"""

import json
import time
from typing import Dict, Any, Optional, List
from core.agent_coordinator import BaseAgent, AgentType
from openai import OpenAI
from core.shared_prompts import get_shared_context_awareness, get_shared_handoff_rules


class AnalysisAgent(BaseAgent):
    """Specialized agent for analyzing investigation findings and planning next steps"""
    
    def __init__(self, client: OpenAI, model: str = "o4-mini"):
        super().__init__(client, AgentType.ANALYSIS, model=model)
        
        # Set agent-specific properties
        self.agent_name = "Analysis"
        self.agent_emoji = "🧠"
        
        # Initialize configuration
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the analysis agent"""
        
        base_prompt = """
You are a specialized IT operations analyst who reviews investigation findings and recommends next steps.
Your expertise is in correlating evidence, determining root causes, and creating actionable remediation plans.

ANALYSIS APPROACH:
1. Review all investigation data collected so far (Splunk logs, flow logs, ServiceNow tickets, deployments)
2. Identify patterns and correlations between different data sources
3. Determine the most likely root cause based on evidence
4. Create a specific, actionable remediation plan
5. Present findings clearly and get user confirmation before proceeding

ANALYSIS CAPABILITIES:
- Timeline correlation: Match events across different systems
- Root cause analysis: Identify the underlying issue from symptoms
- Impact assessment: Determine scope and severity of the problem
- Risk evaluation: Assess potential consequences of remediation actions
- Plan creation: Develop step-by-step remediation procedures

ANALYSIS OUTPUT FORMAT:
When analyzing findings, provide:
1. **Summary of Evidence**: Key findings from each data source
2. **Timeline Analysis**: Chronological sequence of events
3. **Root Cause**: Most likely cause based on evidence correlation
4. **Impact Assessment**: Affected systems and business impact
5. **Recommended Actions**: Specific steps to resolve the issue
6. **Risk Assessment**: Potential risks of the recommended actions

IMPORTANT PRINCIPLES:
- Base conclusions only on evidence presented in the conversation
- Clearly distinguish between facts and hypotheses
- Provide specific, actionable recommendations
- Always confirm the plan with the user before recommending handoff to remediation
- If evidence is insufficient, request additional investigation

You do NOT perform investigations yourself - you analyze what the Investigator has already found.
You do NOT execute remediation - you create plans for the Remediation agent to follow.
"""
        
        # Shared context awareness and handoff rules
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.ANALYSIS)
        
        analysis_guidelines = """
ANALYSIS GUIDELINES:
- Review the entire conversation history to understand what investigation has been done
- Look for correlations between timing of deployments, errors, and outages
- Consider both technical and operational factors (planned maintenance, resource constraints, etc.)
- Provide confidence levels for your conclusions (High/Medium/Low confidence)
- If multiple root causes are possible, rank them by likelihood
- Always ask for user confirmation before recommending remediation handoff
"""
        
        return base_prompt + context_awareness + handoff_rules + analysis_guidelines
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the analysis agent"""
        base_tools = []
        
        # Add the handoff tool from base class
        handoff_tool = self.get_handoff_tool()
        if handoff_tool:
            base_tools.append(handoff_tool)
        
        return base_tools
    
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls for analysis"""
        try:
            # Analysis agent primarily uses conversation history, no special tools needed
            # All tool calls would be handoffs
            return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
