import json
import time
from typing import List, Dict, Any
from openai import OpenAI
from mock_services import MockPBMServices
from pricing_calculator import MathCalculator
import keys

class DrugPricingAssistant:
    """Manages the OpenAI Assistant for drug pricing conversations"""
    
    def __init__(self):
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
        self.pbm_services = MockPBMServices()
        self.math_calculator = MathCalculator()
        self.assistant = None
        self.thread = None
        
        # Define the function tools for the assistant
        self.tools = [            {
                "type": "function",
                "function": {
                    "name": "ndc_lookup",
                    "description": "Search for drugs by name to find specific drug products. Returns multiple matching drugs to help disambiguate.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "drug_name": {
                                "type": "string",
                                "description": "The drug name or active ingredient to search for (e.g., 'metformin', 'lisinopril', 'atorvastatin')"
                            },
                            "dose": {
                                "type": "string",
                                "description": "The dose/strength if known (e.g., '10mg', '500mg', '20mg/mL') - optional"
                            },
                            "qty": {
                                "type": "integer",
                                "description": "Quantity needed (e.g., 30, 90) - optional"
                            },
                            "dosage_form": {
                                "type": "string",
                                "description": "The dosage form if known (e.g., 'tablet', 'capsule', 'cream', 'foam', 'liquid', 'injection') - optional"
                            }
                        },
                        "required": ["drug_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_eligibility",
                    "description": "Verify member eligibility and get basic member information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {
                                "type": "string",
                                "description": "The member ID to check eligibility for"
                            },
                            "date_of_birth": {
                                "type": "string",
                                "description": "Member's date of birth in YYYY-MM-DD format (optional for verification)"
                            }
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_plan_benefits",
                    "description": "Get detailed plan benefit structure including tier copays, deductibles, and out-of-pocket maximums",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "plan_id": {
                                "type": "string",
                                "description": "The plan ID to get benefit details for"
                            }
                        },
                        "required": ["plan_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_member_utilization",
                    "description": "Get member's year-to-date spending, deductible progress, and prescription history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "member_id": {
                                "type": "string",
                                "description": "The member ID to get utilization for"
                            },
                            "plan_year": {
                                "type": "integer",
                                "description": "The plan year (default 2025)",
                                "default": 2025
                            }
                        },
                        "required": ["member_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_formulary",
                    "description": "Check if a drug is covered by the plan and get tier information and restrictions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ndc": {
                                "type": "string",
                                "description": "The 11-digit NDC code for the drug"
                            },
                            "plan_id": {
                                "type": "string",
                                "description": "The plan ID to check formulary for"
                            }
                        },
                        "required": ["ndc", "plan_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_drug_cost",
                    "description": "Get wholesale price, plan negotiated price, and dispensing fees for a drug",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ndc": {
                                "type": "string",
                                "description": "The 11-digit NDC code for the drug"
                            }
                        },
                        "required": ["ndc"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_coupons",
                    "description": "Check for available manufacturer coupons and discount programs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ndc": {
                                "type": "string",
                                "description": "The 11-digit NDC code for the drug"
                            },
                            "member_id": {
                                "type": "string",
                                "description": "The member ID (optional, for eligibility checking)"
                            }
                        },
                        "required": ["ndc"]
                    }
                }            },
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers together",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {
                                "type": "number",
                                "description": "First number"
                            },
                            "b": {
                                "type": "number",
                                "description": "Second number"
                            }
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "subtract",
                    "description": "Subtract second number from first number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {
                                "type": "number",
                                "description": "Number to subtract from"
                            },
                            "b": {
                                "type": "number",
                                "description": "Number to subtract"
                            }
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "multiply",
                    "description": "Multiply two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {
                                "type": "number",
                                "description": "First number"
                            },
                            "b": {
                                "type": "number",
                                "description": "Second number"
                            }
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "divide",
                    "description": "Divide first number by second number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {
                                "type": "number",
                                "description": "Number to divide"
                            },
                            "b": {
                                "type": "number",
                                "description": "Number to divide by"
                            }
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_percentage",
                    "description": "Calculate percentage of an amount",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "The amount to calculate percentage of"
                            },
                            "percentage": {
                                "type": "number",
                                "description": "The percentage (e.g., 20 for 20%)"
                            }
                        },
                        "required": ["amount", "percentage"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_minimum",
                    "description": "Apply a minimum value (return the larger of two values)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "number",
                                "description": "The value to check"
                            },
                            "minimum": {
                                "type": "number",
                                "description": "The minimum threshold"
                            }
                        },
                        "required": ["value", "minimum"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_maximum",
                    "description": "Apply a maximum value (return the smaller of two values)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "number",
                                "description": "The value to check"
                            },
                            "maximum": {
                                "type": "number",
                                "description": "The maximum threshold"
                            }
                        },
                        "required": ["value", "maximum"]
                    }
                }
            }
        ]    
    def create_assistant(self):
        """Create the OpenAI Assistant with drug pricing instructions and tools"""
        instructions = """
You are a helpful drug pricing assistant for a Pharmacy Benefits Manager (PBM). 
Your role is to help customers understand what their prescription drugs may cost based on their insurance plan.

MEMBER INFORMATION: For this demo, assume you're helping member ID "DEMO123456" with birthdate "1985-03-15". 
Always use this member information when checking eligibility and calculating pricing.

IMPORTANT USER EXPERIENCE GUIDELINES:
- NEVER mention "NDC" or "National Drug Code" to the user - this is internal pharmacy terminology
- Work behind the scenes to find the specific drug product the user needs
- If multiple drug options exist, ask user-friendly questions about:
  * Strength/dose (e.g., "What strength do you take - 10mg, 20mg, or 40mg?")
  * Form (e.g., "Do you take tablets, capsules, or liquid?")
  * Brand vs generic preference
  * Quantity needed and days supply (e.g., "How many pills and for how many days?")

WORKFLOW:
1. **Drug Identification**: Use ndc_lookup to find drug options, then help user specify exactly what they need
2. **Data Gathering**: Automatically check eligibility, plan benefits, utilization, formulary, costs, and coupons
3. **Step-by-Step Calculation**: Use the mathematical functions (add, subtract, multiply, divide, calculate_percentage, apply_minimum, apply_maximum) to calculate final pricing step by step, showing your work
4. **Explanation**: Clearly explain each calculation step and the final cost breakdown in user-friendly terms

CALCULATION APPROACH:
- Use multiply to calculate total drug cost (price per unit × quantity) 
- Use add to include dispensing fees
- Use subtract to apply deductible amounts
- Use calculate_percentage for coinsurance calculations
- Use apply_minimum/apply_maximum for copays and benefit limits
- Show each step clearly so the user understands how their final cost was calculated

When you have multiple drug options from ndc_lookup:
- Present choices in simple terms (strength, form, brand/generic)
- Help narrow down to ONE specific product before calculating pricing
- Ask for quantity and days supply if not provided

Be conversational, helpful, and show your mathematical work clearly to build trust and transparency.
"""
        
        self.assistant = self.client.beta.assistants.create(
            name="Drug Pricing Assistant",
            instructions=instructions,
            model="gpt-4-1106-preview",
            tools=self.tools
        )
        
        return self.assistant
    
    def create_thread(self):
        """Create a new conversation thread"""
        self.thread = self.client.beta.threads.create()
        return self.thread
    
    def send_message(self, message: str) -> str:
        """Send a message and get the assistant's response with function calling"""
        
        # Add the user message to the thread
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=message
        )
        
        # Run the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id
        )
        
        # Wait for completion and handle function calls
        while run.status in ['queued', 'in_progress', 'requires_action']:
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )
            
            # Handle function calls
            if run.status == 'requires_action':
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"🔧 Calling function: {function_name} with args: {function_args}")
                    
                    # Call the appropriate mock service
                    if function_name == "ndc_lookup":
                        result = self.pbm_services.ndc_lookup(**function_args)
                        output = result.model_dump_json()
                        print(f"💊 NDC Lookup Results:")
                        for i, drug in enumerate(result.drugs, 1):
                            print(f"   {i}. {drug.name} ({drug.strength}) - {drug.dosage_form}")
                            print(f"      NDC: {drug.ndc}, Manufacturer: {drug.manufacturer}")
                    elif function_name == "check_eligibility":
                        result = self.pbm_services.check_eligibility(**function_args)
                        output = result.model_dump_json()
                        print(f"✅ Eligibility Check Result:")
                        if result.is_eligible and result.member_info:
                            print(f"   Member: {result.member_info.first_name} {result.member_info.last_name}")
                            print(f"   Plan ID: {result.member_info.plan_id}")
                            print(f"   DOB: {result.member_info.date_of_birth}")
                        for msg in result.messages:
                            print(f"   Message: {msg}")
                    elif function_name == "get_plan_benefits":
                        result = self.pbm_services.get_plan_benefits(**function_args)
                        output = result.model_dump_json()
                        print(f"📋 Plan Benefits:")
                        print(f"   Plan: {result.plan_name} ({result.plan_year})")
                        print(f"   Deductible: ${result.deductible}")
                        print(f"   Out-of-Pocket Max: ${result.out_of_pocket_max}")
                        print(f"   Tier 1 (Generic): ${result.tier_1_copay or 'N/A'} copay, {result.tier_1_coinsurance or 'N/A'} coinsurance")
                        print(f"   Tier 2 (Preferred): ${result.tier_2_copay or 'N/A'} copay, {result.tier_2_coinsurance or 'N/A'} coinsurance")
                    elif function_name == "get_member_utilization":
                        result = self.pbm_services.get_member_utilization(**function_args)
                        output = result.model_dump_json()
                        print(f"📊 Member Utilization ({result.plan_year}):")
                        print(f"   Deductible: ${result.deductible_met} spent")
                        print(f"   Out-of-Pocket: ${result.out_of_pocket_met} spent")
                        print(f"   Total Paid by Member: ${result.total_paid_by_member}")
                        print(f"   Prescriptions Filled: {result.prescription_count}")
                    elif function_name == "check_formulary":
                        result = self.pbm_services.check_formulary(**function_args)
                        output = result.model_dump_json()
                        print(f"📖 Formulary Check:")
                        coverage_status = "✅ Covered" if result.is_covered else "❌ Not covered"
                        print(f"   Status: {coverage_status}")
                        if result.is_covered:
                            print(f"   Tier: {result.tier}")
                            print(f"   Prior Auth Required: {result.prior_auth_required}")
                            print(f"   Step Therapy Required: {result.step_therapy_required}")
                    elif function_name == "get_drug_cost":
                        result = self.pbm_services.get_drug_cost(**function_args)
                        output = result.model_dump_json()
                        print(f"💰 Drug Cost Information:")
                        print(f"   Wholesale Price: ${result.wholesale_price}")
                        print(f"   Plan Negotiated Price: ${result.plan_negotiated_price}")
                        print(f"   Dispensing Fee: ${result.dispensing_fee}")
                    elif function_name == "check_coupons":
                        result = self.pbm_services.check_coupons(**function_args)
                        output = result.model_dump_json()
                        print(f"🎟️ Available Coupons:")
                        eligible_coupons = [c for c in result.available_coupons if c.eligible]
                        if eligible_coupons:
                            for coupon in eligible_coupons:
                                print(f"   • {coupon.name} ({coupon.discount_type})")
                                print(f"     Discount: ${coupon.discount_value if coupon.discount_type == 'fixed' else str(coupon.discount_value) + '%'}")
                                if coupon.max_savings:
                                    print(f"     Max Savings: ${coupon.max_savings}")
                        else:
                            print("   No eligible coupons found")
                    # Mathematical calculator functions
                    elif function_name == "add":
                        result = self.math_calculator.add(**function_args)
                        output = json.dumps({"result": result})
                        print(f"📊 Math result: {function_args['a']} + {function_args['b']} = {result}")
                    elif function_name == "subtract":
                        result = self.math_calculator.subtract(**function_args)
                        output = json.dumps({"result": result})
                        print(f"📊 Math result: {function_args['a']} - {function_args['b']} = {result}")
                    elif function_name == "multiply":
                        result = self.math_calculator.multiply(**function_args)
                        output = json.dumps({"result": result})
                        print(f"📊 Math result: {function_args['a']} × {function_args['b']} = {result}")
                    elif function_name == "divide":
                        try:
                            result = self.math_calculator.divide(**function_args)
                            output = json.dumps({"result": result})
                            print(f"📊 Math result: {function_args['a']} ÷ {function_args['b']} = {result}")
                        except ValueError as e:
                            output = json.dumps({"error": str(e)})
                            print(f"❌ Math error: {str(e)}")
                    elif function_name == "calculate_percentage":
                        result = self.math_calculator.calculate_percentage(**function_args)
                        output = json.dumps({"result": result})
                        print(f"📊 Math result: {function_args['percentage']}% of {function_args['amount']} = {result}")
                    elif function_name == "apply_minimum":
                        result = self.math_calculator.apply_minimum(**function_args)
                        output = json.dumps({"result": result})
                        print(f"📊 Math result: max({function_args['value']}, {function_args['minimum']}) = {result}")
                    elif function_name == "apply_maximum":
                        result = self.math_calculator.apply_maximum(**function_args)
                        output = json.dumps({"result": result})
                        print(f"📊 Math result: min({function_args['value']}, {function_args['maximum']}) = {result}")
                    else:
                        output = json.dumps({"error": f"Unknown function: {function_name}"})
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": output
                    })
                
                # Submit the tool outputs
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
        
        # Get the latest messages
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id,
            order="desc",
            limit=1
        )
        
        return messages.data[0].content[0].text.value
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the full conversation history"""
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id,
            order="asc"
        )
        
        history = []
        for message in messages.data:
            history.append({
                "role": message.role,
                "content": message.content[0].text.value
            })
        
        return history
