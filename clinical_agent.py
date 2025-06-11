"""
Specialized Clinical Agent

Handles drug interactions, clinical criteria, therapeutic alternatives, and medical guidance.
Can hand off to other agents when needed (e.g., pricing, benefits, pharmacy).
Now uses OpenAI Chat Completions API with streaming instead of Assistants API.
"""

import json
import time
from typing import Dict, Any, Optional, List
from agent_coordinator import BaseAgent, AgentType
from openai import OpenAI
from shared_prompts import get_shared_context_awareness, get_shared_handoff_rules


class ClinicalAgent(BaseAgent):
    """Specialized agent for clinical and medical guidance"""
    
    def __init__(self, client: OpenAI, model: str = "gpt-4.1"):
        super().__init__(client, AgentType.CLINICAL, model=model)
        
        # Set agent-specific properties
        self.agent_name = "Clinical"
        self.agent_emoji = "⚕️"
        
        # Initialize tools and system prompt
        self.system_prompt = self.get_system_prompt()
        self.tools = self.get_tools()
        
    def get_system_prompt(self) -> str:
        """Get the system prompt for the clinical agent"""
        base_prompt = """
You are a specialized clinical pharmacist expert for a healthcare system.
Your expertise is in drug interactions, therapeutic alternatives, clinical criteria, and medication safety.
Provide clear, evidence-based clinical information in concise responses.
Use the 'request_handoff' function only when services outside your clinical domain are needed.
"""
        context_awareness = get_shared_context_awareness()
        handoff_rules = get_shared_handoff_rules(AgentType.CLINICAL)
        clarification_rules = """
CLARIFICATION_RULES:
- After providing clinical recommendations, answer follow-up questions directly, such as 'What does that interaction imply?' or 'How serious is this?'
- Avoid handoffs for clarifications within the clinical scope.
- Only hand off pricing, coverage, prescription management, or authentication questions outside the clinical domain.
"""
        return base_prompt + context_awareness + handoff_rules + clarification_rules
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools configuration for the clinical agent"""
        base_tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_drug_interactions",
                    "description": "Check for drug-drug interactions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_list": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of drugs to check for interactions"
                            },
                            "member_id": {"type": "string", "description": "Member ID (optional)"}
                        },
                        "required": ["drug_list"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_therapeutic_alternatives",
                    "description": "Find therapeutic alternatives for a drug",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name to find alternatives for"},
                            "indication": {"type": "string", "description": "Medical condition/indication"},
                            "contraindications": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Known allergies or contraindications"
                            }
                        },
                        "required": ["drug_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_clinical_criteria",
                    "description": "Check clinical criteria for drug approval",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name"},
                            "indication": {"type": "string", "description": "Medical indication"},
                            "member_id": {"type": "string", "description": "Member ID"},
                            "age": {"type": "integer", "description": "Patient age (optional)"}
                        },
                        "required": ["drug_name", "indication", "member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_allergies",
                    "description": "Check for drug allergies and cross-sensitivities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {"type": "string", "description": "Member ID"},
                            "drug_name": {"type": "string", "description": "Drug to check"}
                        },
                        "required": ["member_id", "drug_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_dosing_guidance",
                    "description": "Get dosing recommendations based on patient factors",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name"},
                            "indication": {"type": "string", "description": "Medical indication"},
                            "age": {"type": "integer", "description": "Patient age"},
                            "weight": {"type": "number", "description": "Patient weight in kg (optional)"},
                            "renal_function": {"type": "string", "description": "Renal function status (optional)"}
                        },
                        "required": ["drug_name", "indication", "age"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "safety_alert_check",
                    "description": "Check for FDA safety alerts and warnings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {"type": "string", "description": "Drug name"},
                            "alert_type": {
                                "type": "string", 
                                "enum": ["boxed_warning", "safety_communication", "recall"],
                                "description": "Type of safety alert (optional)"
                            }
                        },
                        "required": ["drug_name"]                    }
                }
            }
        ]
        
        # Add the handoff tool from base class
        handoff_tool = self.get_handoff_tool()
        if handoff_tool:
            base_tools.append(handoff_tool)
            
        return base_tools
    
    def handle_tool_call(self, function_name: str, function_args: Dict[str, Any]) -> str:
        """Handle tool calls with console output"""
        try:
            if function_name == "check_drug_interactions":
                drug_list = function_args.get("drug_list", [])
                
                print(f"⚠️ Checking interactions for drugs: {', '.join(drug_list)}")
                
                # Mock interaction checking
                if len(drug_list) >= 2:
                    mock_result = {
                        "drugs_checked": drug_list,
                        "interactions_found": [
                            {
                                "drug_a": drug_list[0],
                                "drug_b": drug_list[1] if len(drug_list) > 1 else drug_list[0],
                                "severity": "Moderate",
                                "mechanism": "Both medications can lower blood pressure",
                                "clinical_effect": "Increased risk of hypotension",
                                "recommendation": "Monitor blood pressure closely. Consider dose adjustment.",
                                "documentation": "Well-documented"
                            }
                        ],
                        "total_interactions": 1
                    }
                else:
                    mock_result = {
                        "drugs_checked": drug_list,
                        "interactions_found": [],
                        "total_interactions": 0,
                        "message": "No interactions found with single drug"
                    }
                
                print(f"⚠️ Found {mock_result['total_interactions']} interaction(s)")
                return json.dumps(mock_result)
                
            elif function_name == "find_therapeutic_alternatives":
                drug_name = function_args.get("drug_name", "")
                indication = function_args.get("indication", "")
                contraindications = function_args.get("contraindications", [])
                
                print(f"🔄 Finding alternatives for {drug_name}")
                
                mock_result = {
                    "original_drug": drug_name,
                    "indication": indication,
                    "alternatives": [
                        {
                            "drug_name": "Lisinopril",
                            "drug_class": "ACE Inhibitor",
                            "mechanism": "ACE inhibition",
                            "efficacy": "Similar efficacy for hypertension",
                            "safety_profile": "Generally well tolerated",
                            "cost_category": "Generic - Low cost"
                        },
                        {
                            "drug_name": "Losartan",
                            "drug_class": "ARB",
                            "mechanism": "Angiotensin receptor blocking",
                            "efficacy": "Equivalent efficacy",
                            "safety_profile": "Lower cough incidence than ACE inhibitors",
                            "cost_category": "Generic - Low cost"
                        }
                    ],
                    "contraindications_considered": contraindications
                }
                
                print(f"🔄 Found {len(mock_result['alternatives'])} alternative(s)")
                return json.dumps(mock_result)
                
            elif function_name == "check_clinical_criteria":
                drug_name = function_args.get("drug_name", "")
                indication = function_args.get("indication", "")
                member_id = function_args.get("member_id", "")
                
                print(f"📋 Checking clinical criteria for {drug_name}")
                
                mock_result = {
                    "drug_name": drug_name,
                    "indication": indication,
                    "member_id": member_id,
                    "criteria_met": True,
                    "clinical_requirements": [
                        {
                            "requirement": "Appropriate diagnosis",
                            "status": "Met",
                            "evidence": "ICD-10 code I10 - Essential hypertension"
                        },
                        {
                            "requirement": "First-line therapy trial",
                            "status": "Met",
                            "evidence": "Previous ACE inhibitor trial documented"
                        },
                        {
                            "requirement": "Age appropriateness",
                            "status": "Met",
                            "evidence": "Patient age 39 - within approved range"
                        }
                    ],
                    "approval_recommendation": "Approve - All clinical criteria met"
                }
                
                print(f"✅ Clinical criteria: {mock_result['approval_recommendation']}")
                return json.dumps(mock_result)
                
            elif function_name == "check_allergies":
                member_id = function_args.get("member_id", "")
                drug_name = function_args.get("drug_name", "")
                
                print(f"🚨 Checking allergies for {drug_name}")
                
                mock_result = {
                    "member_id": member_id,
                    "drug_checked": drug_name,
                    "allergy_found": False,
                    "member_allergies": [
                        {
                            "allergen": "Penicillin",
                            "reaction": "Rash",
                            "severity": "Mild",
                            "date_reported": "2020-03-15"
                        }
                    ],
                    "cross_sensitivity_check": {
                        "potential_cross_reactions": [],
                        "safe_to_use": True
                    }
                }
                
                status = "Safe" if mock_result["safe_to_use"] else "Caution"
                print(f"🚨 Allergy check: {status}")
                return json.dumps(mock_result)
                
            elif function_name == "get_dosing_guidance":
                drug_name = function_args.get("drug_name", "")
                indication = function_args.get("indication", "")
                age = function_args.get("age", 0)
                
                print(f"💊 Getting dosing guidance for {drug_name}")
                
                mock_result = {
                    "drug_name": drug_name,
                    "indication": indication,
                    "patient_age": age,
                    "recommended_dosing": {
                        "starting_dose": "5mg once daily",
                        "maximum_dose": "40mg once daily",
                        "titration_schedule": "Increase by 5-10mg every 2-4 weeks as tolerated",
                        "special_considerations": [
                            "Take with or without food",
                            "Monitor blood pressure and kidney function",
                            "Reduce dose in elderly patients"
                        ]
                    },
                    "age_specific_notes": "Adult dosing appropriate for age 39",
                    "monitoring_parameters": [
                        "Blood pressure",
                        "Serum creatinine",
                        "Serum potassium"
                    ]
                }
                
                print(f"💊 Dosing: {mock_result['recommended_dosing']['starting_dose']}")
                return json.dumps(mock_result)
                
            elif function_name == "safety_alert_check":
                drug_name = function_args.get("drug_name", "")
                alert_type = function_args.get("alert_type")
                
                print(f"⚠️ Checking safety alerts for {drug_name}")
                
                mock_result = {
                    "drug_name": drug_name,
                    "alert_type_checked": alert_type or "all",
                    "active_alerts": [
                        {
                            "alert_type": "safety_communication",
                            "date_issued": "2024-08-15",
                            "title": "Risk of angioedema with ACE inhibitors",
                            "summary": "Rare but serious risk of angioedema, particularly in first month of therapy",
                            "action_required": "Monitor patients for signs of angioedema, especially during initiation",
                            "severity": "Important"
                        }
                    ],
                    "recalls": [],
                    "boxed_warnings": []
                }
                
                print(f"⚠️ Found {len(mock_result['active_alerts'])} active alert(s)")
                return json.dumps(mock_result)
            
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            error_msg = f"Error in {function_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
