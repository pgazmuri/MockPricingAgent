"""
IT Operations Tools

This module provides mock IT operations tools for investigating server and application outages.
Each tool uses OpenAI to generate realistic mock data based on context scenarios.
"""

import json
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI
from datetime import datetime, timedelta
from core.session_context import SessionContext
from core.it_environment import ITEnvironment


class ITOpsTools:
    """Mock IT operations tools for outage investigation"""
    
    def __init__(self, client: OpenAI = None, session_context: SessionContext = None):
        self.client = client or OpenAI()
        self.session_context = session_context or SessionContext()
    def splunk_search(self, query: str, time_frame: str, context: str = "") -> Dict[str, Any]:
        """
        Search Splunk logs using SPL (Splunk Processing Language)
        
        Args:
            query: Splunk query in SPL format
            time_frame: Time frame for search (e.g., "last 24 hours", "last 4 hours")
            context: Context scenario for realistic mock data generation
            
        Returns:
            Dictionary containing search results
        """
        # Combine user-provided context with session context
        session_scenario = self.session_context.get_context()
        full_context = f"Session Scenario: {session_scenario}\nSpecific Context: {context}" if context else f"Session Scenario: {session_scenario}"
        
        # Get IT environment context for realistic data generation
        splunk_context = ITEnvironment.get_splunk_context()
        investigation_patterns = ITEnvironment.get_investigation_patterns()
        system_prompt = f"""
        You are a Splunk search engine. Generate realistic IT log search results that MUST match the session scenario exactly.
        
        {splunk_context}
        
        {investigation_patterns}
        
        Query: {query}
        Time Frame: {time_frame}
        
        CRITICAL: You MUST follow this session scenario exactly:
        {full_context}
        
        SCENARIO COMPLIANCE RULES:
        1. If the scenario mentions specific server names (e.g., "abc-prod-01"), those EXACT servers must appear in results
        2. If the scenario describes specific issues (e.g., "out of memory errors"), those EXACT issues must appear in logs
        3. If the scenario mentions missing ServiceNow tickets, ensure no tickets are found for those systems
        4. If the scenario mentions specific resource groups (e.g., "Regardo"), include that in deployment/infrastructure data
        5. The timeline and symptoms MUST match what's described in the scenario
        
        Return results as JSON with this structure:
        {{
            "search_id": "search_id_here",
            "query": "{query}",
            "time_frame": "{time_frame}",
            "results_count": number_of_results,
            "events": [
                {{
                    "timestamp": "ISO_timestamp",
                    "host": "hostname",
                    "source": "log_source",
                    "sourcetype": "log_type", 
                    "index": "index_name",
                    "event": "actual_log_message",
                    "severity": "INFO|WARN|ERROR|CRITICAL",
                    "component": "service_or_component_name"
                }}
            ]
        }}
        
        IMPORTANT: The search results MUST reflect the session scenario accurately. If querying for down servers and the scenario mentions "abc-prod-01 is down", then abc-prod-01 MUST appear as down. If the scenario mentions "out of memory errors", those MUST appear in application logs.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate Splunk search results for: {query}"}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            return {
                "error": f"Splunk search failed: {str(e)}",
                "query": query,
                "time_frame": time_frame
            }
    
    def check_flow_logs(self, vm_name: str, time_frame: str, context: str = "") -> Dict[str, Any]:
        """
        Check network flow logs for a VM
        
        Args:
            vm_name: Name of the virtual machine
            time_frame: Time frame to check (e.g., "last 24 hours")
            context: Context scenario for realistic mock data generation
            
        Returns:
            Dictionary containing flow log analysis
        """
        # Combine user-provided context with session context
        session_scenario = self.session_context.get_context()
        full_context = f"Session Scenario: {session_scenario}\nSpecific Context: {context}" if context else f"Session Scenario: {session_scenario}"
        system_prompt = f"""
        You are a network flow log analyzer. Generate realistic network flow log data that MUST match the session scenario.
        
        VM Name: {vm_name}
        Time Frame: {time_frame}
        
        CRITICAL: You MUST follow this session scenario exactly:
        {full_context}
        
        SCENARIO COMPLIANCE RULES:
        1. If the scenario mentions specific servers (e.g., "abc-prod-01"), include flow data for those exact servers
        2. If the scenario mentions connectivity issues, show denied/failed connections
        3. If the scenario mentions specific resource groups, reference those in connection patterns
        4. Match the timeline described in the scenario
        Return results as JSON with this structure:
        {{
            "vm_name": "{vm_name}",
            "time_frame": "{time_frame}",
            "total_flows": number_of_flows,
            "denied_connections": [
                {{
                    "timestamp": "ISO_timestamp",
                    "source_ip": "ip_address",
                    "destination_ip": "ip_address", 
                    "destination_port": port_number,
                    "protocol": "TCP|UDP",
                    "action": "DENY|ALLOW",
                    "reason": "Security_group_rule|NACL|etc"
                }}
            ],
            "top_destinations": [
                {{
                    "ip": "ip_address",
                    "port": port_number,
                    "connection_count": count,
                    "status": "successful|failed"
                }}
            ]
        }}
        
        IMPORTANT: Generate realistic network flow data that matches the context scenario. Focus on denied connections, unusual traffic patterns, or connectivity issues if mentioned in the scenario.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze flow logs for VM: {vm_name}"}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            return {
                "error": f"Flow log check failed: {str(e)}",
                "vm_name": vm_name,
                "time_frame": time_frame
            }
    
    def check_snow_tickets(self, vm_name: str, time_frame: str, context: str = "") -> Dict[str, Any]:
        """
        Check ServiceNow (SNOW) for tickets related to a VM
        
        Args:
            vm_name: Name of the virtual machine
            time_frame: Time frame to check for tickets
            context: Context scenario for realistic mock data generation
            
        Returns:
            Dictionary containing related tickets
        """        # Combine user-provided context with session context
        session_scenario = self.session_context.get_context()
        full_context = f"Session Scenario: {session_scenario}\nSpecific Context: {context}" if context else f"Session Scenario: {session_scenario}"
        
        system_prompt = f"""
        You are a ServiceNow ticket system. Generate realistic IT service tickets that MUST match the session scenario.
        
        VM Name: {vm_name}
        Time Frame: {time_frame}
        
        CRITICAL: You MUST follow this session scenario exactly:
        {full_context}
        
        SCENARIO COMPLIANCE RULES:
        1. If the scenario says "no log of it in service now" or "no ServiceNow tickets", return 0 tickets found
        2. If the scenario mentions specific servers, only show tickets for those exact servers if they exist
        3. If the scenario mentions specific resource groups, include those in ticket descriptions
        4. Match the timeline described in the scenario
        Return results as JSON with this structure:
        {{
            "vm_name": "{vm_name}",
            "time_frame": "{time_frame}",
            "tickets_found": number_of_tickets,
            "tickets": [
                {{
                    "ticket_number": "INC/CHG/REQ_number",
                    "type": "Incident|Change|Request",
                    "title": "ticket_title",
                    "description": "detailed_description",
                    "status": "New|In Progress|Resolved|Closed",
                    "priority": "P1|P2|P3|P4",
                    "created_date": "ISO_timestamp",
                    "assigned_to": "engineer_name",
                    "affected_systems": ["list_of_systems"]
                }}
            ]
        }}
        
        IMPORTANT: If the scenario specifically mentions "no log of it in service now", you MUST return tickets_found: 0 and an empty tickets array.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Search ServiceNow tickets for VM: {vm_name}"}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            return {
                "error": f"ServiceNow search failed: {str(e)}",
                "vm_name": vm_name,
                "time_frame": time_frame
            }
    def get_deployments(self, vm_name: str, time_frame: str, context: str = "") -> Dict[str, Any]:
        """
        Get deployment and infrastructure changes from ARM control plane
        
        Args:
            vm_name: Name of the virtual machine
            time_frame: Time frame to check for deployments
            context: Context scenario for realistic mock data generation
            
        Returns:
            Dictionary containing deployment information
        """
        # Combine user-provided context with session context
        session_scenario = self.session_context.get_context()
        full_context = f"Session Scenario: {session_scenario}\nSpecific Context: {context}" if context else f"Session Scenario: {session_scenario}"
        
        system_prompt = f"""
        You are an Azure Resource Manager (ARM) control plane API. Generate realistic deployment and infrastructure change data that MUST match the session scenario.
        
        VM Name: {vm_name}
        Time Frame: {time_frame}
        
        CRITICAL: You MUST follow this session scenario exactly:
        {full_context}
        
        SCENARIO COMPLIANCE RULES:
        1. If the scenario mentions specific resource groups (e.g., "Regardo"), those MUST appear in deployment data
        2. If the scenario mentions specific servers (e.g., "abc-prod-01"), include deployments for those exact servers
        3. Match the timeline described in the scenario for when issues started
        4. If the scenario implies memory/resource issues, show related infrastructure changes
        
        Return results as JSON with this structure:
        {{
            "vm_name": "{vm_name}",
            "time_frame": "{time_frame}",
            "deployments_found": number_of_deployments,
            "deployments": [
                {{
                    "deployment_id": "deployment_id",
                    "deployment_name": "deployment_name",
                    "resource_group": "resource_group_name",
                    "timestamp": "ISO_timestamp",
                    "status": "Succeeded|Failed|Running|Cancelled",
                    "operation_type": "Create|Update|Delete",
                    "resources_changed": [
                        {{
                            "resource_type": "Microsoft.Compute/virtualMachines",
                            "resource_name": "resource_name",
                            "action": "Created|Updated|Deleted",
                            "changes": ["list_of_specific_changes"]
                        }}
                    ],
                    "initiated_by": "user_or_automation",
                    "duration": "duration_in_minutes"
                }}
            ],
            "infrastructure_changes": [
                {{
                    "change_type": "Network|Compute|Storage|Security",
                    "description": "description_of_change",
                    "timestamp": "ISO_timestamp",
                    "impact": "High|Medium|Low"
                }}
            ]
        }}
        
        IMPORTANT: If the scenario mentions resource groups like "Regardo", those MUST appear in the deployment data. Match server names and timelines exactly.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Get deployments for VM: {vm_name}"}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            return {
                "error": f"Deployment check failed: {str(e)}",
                "vm_name": vm_name,
                "time_frame": time_frame
            }


# OpenAI function definitions for the tools
def get_splunk_search_tool():
    """Get OpenAI function definition for Splunk search"""
    return {
        "type": "function",
        "function": {
            "name": "splunk_search",
            "description": """Search Splunk logs using SPL (Splunk Processing Language) for system events, errors, and deployment data.

Available indexes and source types:
- index=main sourcetype=heartbeat (server heartbeats every 5 min)
- index=app sourcetype=application (application logs and errors)  
- index=deployment sourcetype=pipeline (CI/CD pipeline logs)
- index=security (authentication and firewall events)
- index=metrics (performance metrics)

Common queries:
- Server status: index=main sourcetype=heartbeat host=HOSTNAME | stats latest(_time)
- Recent deployments: index=deployment earliest=-4h | table _time pipeline_name status
- App errors: index=app severity=ERROR earliest=-2h | timechart span=10m count""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "Splunk search query in SPL format using proper index and sourcetype (e.g., 'index=main sourcetype=heartbeat host=WEB-PROD-01', 'index=deployment pipeline_name=\"web-app-pipeline\" earliest=-4h')"
                    },
                    "time_frame": {
                        "type": "string",
                        "description": "Time frame for the search (e.g., 'last 24 hours', 'last 4 hours', 'last 30 minutes')"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about the issue being investigated for more realistic results"
                    }
                },
                "required": ["query", "time_frame"]
            }
        }
    }

def get_check_flow_logs_tool():
    """Get OpenAI function definition for checking flow logs"""
    return {
        "type": "function",
        "function": {
            "name": "check_flow_logs",
            "description": "Check network flow logs for a VM to identify connectivity issues, denied traffic, or unusual network patterns",
            "parameters": {
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Name of the virtual machine to check flow logs for"
                    },
                    "time_frame": {
                        "type": "string",
                        "description": "Time frame to analyze (e.g., 'last 24 hours', 'last 4 hours')"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about connectivity issues or suspected network problems"
                    }
                },
                "required": ["vm_name", "time_frame"]
            }
        }
    }

def get_check_snow_tickets_tool():
    """Get OpenAI function definition for checking ServiceNow tickets"""
    return {
        "type": "function",
        "function": {
            "name": "check_snow_tickets",
            "description": "Check ServiceNow for tickets related to a VM to see if there were planned maintenance, incidents, or changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Name of the virtual machine to search tickets for"
                    },
                    "time_frame": {
                        "type": "string",
                        "description": "Time frame to search for tickets (e.g., 'last 7 days', 'last 24 hours')"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about the type of issue or maintenance expected"
                    }
                },
                "required": ["vm_name", "time_frame"]
            }
        }
    }

def get_deployments_tool():
    """Get OpenAI function definition for getting deployments"""
    return {
        "type": "function",
        "function": {
            "name": "get_deployments",
            "description": "Get deployment and infrastructure changes from ARM control plane to identify recent changes that might cause issues",
            "parameters": {
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Name of the virtual machine to check deployments for"
                    },
                    "time_frame": {
                        "type": "string",
                        "description": "Time frame to check for deployments (e.g., 'last 7 days', 'last 24 hours')"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about suspected infrastructure changes or deployment issues"
                    }
                },
                "required": ["vm_name", "time_frame"]
            }
        }
    }
