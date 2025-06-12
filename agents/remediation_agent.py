"""
IT Remediation Agent

Specialized agent for executing approved remediation plans using mock IT operations tools.
Simulates remediation actions and provides realistic feedback on execution.
"""

import json
import time
from typing import Dict, Any, Optional, List
from core.agent_coordinator import BaseAgent, AgentType
from openai import OpenAI
from core.shared_prompts import get_shared_context_awareness, get_shared_handoff_rules


class RemediationAgent(BaseAgent):
    """Specialized agent for executing IT remediation plans"""
    
    def __init__(self, client: OpenAI, model: str = "gpt-4.1"):
        super().__init__(client, AgentType.REMEDIATION, model=model)
        
        # Set agent-specific properties
        self.agent_name = "Remediation"
        self.agent_emoji = "🔧"
        
        # Initialize configuration
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the remediation agent"""
        
        base_prompt = """
You are a specialized IT operations remediation specialist who executes approved fixes and recovery procedures.
Your expertise is in safely implementing solutions while minimizing business impact.

REMEDIATION CAPABILITIES:
- Execute restart procedures for services and servers
- Apply configuration changes and patches
- Perform rollback operations when needed
- Monitor system recovery and validate fixes
- Coordinate with teams for complex changes

AVAILABLE MOCK TOOLS:
- restart_service: Restart services on servers
- restart_server: Restart entire servers (high impact)
- apply_patch: Apply software patches or updates
- update_configuration: Modify application or system configuration
- rollback_deployment: Rollback recent deployments
- verify_fix: Validate that remediation resolved the issue
- notify_teams: Send notifications about remediation actions

REMEDIATION APPROACH:
1. Review the approved remediation plan from Analysis
2. Confirm understanding of the steps with the user
3. Execute steps in the correct order with progress updates
4. Validate each step before proceeding to the next
5. Provide clear feedback on success/failure of each action
6. Verify the overall fix resolves the original issue

SAFETY PRINCIPLES:
- Always confirm high-impact actions (server restarts) with user first
- Execute changes incrementally when possible
- Monitor for unexpected side effects after each step
- Have rollback plans ready for major changes
- Provide realistic timelines for each remediation step

IMPORTANT: You work with MOCK tools that simulate real actions. Provide realistic feedback about:
- Expected execution times
- Potential risks and side effects
- Success/failure scenarios based on the context
- Post-remediation validation steps
"""
        
        # Shared context awareness and handoff rules
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.REMEDIATION)
        
        remediation_guidelines = """
REMEDIATION GUIDELINES:
- Always review the remediation plan before starting execution
- Confirm each high-impact step with the user before executing
- Provide progress updates during execution
- Simulate realistic execution times and outcomes
- If a step fails, suggest alternative approaches or rollback
- Always validate that the fix resolves the original problem
"""
        
        return base_prompt + context_awareness + handoff_rules + remediation_guidelines
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the remediation agent"""
        base_tools = [
            {
                "type": "function",
                "function": {
                    "name": "restart_service",
                    "description": "Restart a specific service on a server",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {"type": "string", "description": "Name of the server"},
                            "service_name": {"type": "string", "description": "Name of the service to restart"},
                            "force": {"type": "boolean", "description": "Force restart if service is unresponsive", "default": False}
                        },
                        "required": ["server_name", "service_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "restart_server",
                    "description": "Restart an entire server (high impact operation)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {"type": "string", "description": "Name of the server to restart"},
                            "graceful": {"type": "boolean", "description": "Perform graceful shutdown first", "default": True}
                        },
                        "required": ["server_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_patch",
                    "description": "Apply a software patch or update",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {"type": "string", "description": "Target server"},
                            "patch_id": {"type": "string", "description": "Patch identifier"},
                            "patch_description": {"type": "string", "description": "Description of what the patch fixes"}
                        },
                        "required": ["server_name", "patch_id", "patch_description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rollback_deployment",
                    "description": "Rollback a recent deployment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "deployment_id": {"type": "string", "description": "ID of deployment to rollback"},
                            "target_version": {"type": "string", "description": "Version to rollback to"}
                        },
                        "required": ["deployment_id", "target_version"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_fix",
                    "description": "Verify that remediation resolved the original issue",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "check_type": {"type": "string", "description": "Type of verification to perform"},
                            "expected_result": {"type": "string", "description": "What should be true if fix worked"}
                        },
                        "required": ["check_type", "expected_result"]
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
        """Handle tool calls for remediation"""
        try:
            if function_name == "restart_service":
                server_name = function_args.get("server_name", "")
                service_name = function_args.get("service_name", "")
                force = function_args.get("force", False)
                
                print(f"🔧 Restarting service {service_name} on {server_name} (force={force})")
                
                # Simulate service restart with realistic timing
                time.sleep(1)  # Simulate processing time
                
                result = {
                    "action": "restart_service",
                    "server": server_name,
                    "service": service_name,
                    "status": "success",
                    "execution_time": "3.2 seconds",
                    "message": f"Service {service_name} restarted successfully on {server_name}",
                    "next_steps": "Monitor service health for 5 minutes to ensure stability"
                }
                
                print(f"✅ Service restart completed: {result['message']}")
                return json.dumps(result)
            
            elif function_name == "restart_server":
                server_name = function_args.get("server_name", "")
                graceful = function_args.get("graceful", True)
                
                print(f"🔧 Restarting server {server_name} (graceful={graceful})")
                print("⚠️  This is a high-impact operation that will cause temporary downtime")
                
                # Simulate server restart with realistic timing
                time.sleep(2)  # Simulate processing time
                
                result = {
                    "action": "restart_server",
                    "server": server_name,
                    "status": "success", 
                    "downtime": "2 minutes 45 seconds",
                    "message": f"Server {server_name} restarted successfully",
                    "boot_time": "1 minute 30 seconds",
                    "service_startup": "1 minute 15 seconds",
                    "next_steps": "Verify all services are running and applications are responding"
                }
                
                print(f"✅ Server restart completed: {result['message']}")
                return json.dumps(result)
            
            elif function_name == "apply_patch":
                server_name = function_args.get("server_name", "")
                patch_id = function_args.get("patch_id", "")
                patch_description = function_args.get("patch_description", "")
                
                print(f"🔧 Applying patch {patch_id} to {server_name}")
                print(f"📝 Patch description: {patch_description}")
                
                # Simulate patch application
                time.sleep(1.5)
                
                result = {
                    "action": "apply_patch",
                    "server": server_name,
                    "patch_id": patch_id,
                    "status": "success",
                    "execution_time": "4 minutes 12 seconds",
                    "message": f"Patch {patch_id} applied successfully to {server_name}",
                    "reboot_required": False,
                    "next_steps": "Verify patch resolved the issue and monitor for side effects"
                }
                
                print(f"✅ Patch application completed: {result['message']}")
                return json.dumps(result)
            
            elif function_name == "rollback_deployment":
                deployment_id = function_args.get("deployment_id", "")
                target_version = function_args.get("target_version", "")
                
                print(f"🔧 Rolling back deployment {deployment_id} to version {target_version}")
                
                # Simulate rollback
                time.sleep(2)
                
                result = {
                    "action": "rollback_deployment",
                    "deployment_id": deployment_id,
                    "target_version": target_version,
                    "status": "success",
                    "execution_time": "6 minutes 30 seconds",
                    "message": f"Deployment rollback completed to version {target_version}",
                    "services_restarted": ["web-service", "api-service"],
                    "next_steps": "Verify application functionality and monitor for errors"
                }
                
                print(f"✅ Rollback completed: {result['message']}")
                return json.dumps(result)
            
            elif function_name == "verify_fix":
                check_type = function_args.get("check_type", "")
                expected_result = function_args.get("expected_result", "")
                
                print(f"🔍 Verifying fix: {check_type}")
                print(f"🎯 Expected result: {expected_result}")
                
                # Simulate verification
                time.sleep(1)
                
                result = {
                    "action": "verify_fix",
                    "check_type": check_type,
                    "expected_result": expected_result,
                    "actual_result": expected_result,  # Assume success for demo
                    "status": "success",
                    "verification_time": "30 seconds",
                    "message": "Verification completed successfully - fix appears to be working",
                    "confidence": "High"
                }
                
                print(f"✅ Verification completed: {result['message']}")
                return json.dumps(result)
            
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
