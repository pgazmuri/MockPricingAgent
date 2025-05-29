#!/usr/bin/env python3
"""
Mock Drug Pricing Agent - OpenAI Assistant API Demonstration

This application demonstrates how to use the OpenAI Assistant API with function calling
to create a conversational drug pricing agent for a Pharmacy Benefits Manager (PBM).

The agent helps customers:
1. Find the right drug by searching NDC database
2. Disambiguate between multiple drug options
3. Check eligibility and plan benefits
4. Calculate accurate pricing with discounts and coupons

Key features demonstrated:
- OpenAI Assistant API with function calling
- Natural conversation flow
- Complex multi-step workflows
- Mock services using OpenAI Completions API
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from assistant_manager import DrugPricingAssistant
import keys

console = Console()

def print_header():
    """Print the application header"""
    header_text = Text("🏥 Mock Drug Pricing Agent", style="bold blue")
    subtitle_text = Text("OpenAI Assistant API Demonstration with Function Calling", style="dim")
    
    panel = Panel(
        f"{header_text}\n{subtitle_text}",
        title="PBM Drug Pricing Assistant",
        border_style="blue"
    )
    console.print(panel)

def print_help():
    """Print help information"""
    help_text = """
Available commands:
• Type any drug name to search for pricing (e.g., "metformin", "Lipitor")
• Ask questions like "What will my Advil cost?" or "How much is generic Nexium?"
• Provide member ID when asked for eligibility checking
• Type 'help' to see this message again
• Type 'quit' or 'exit' to end the session
• Type 'history' to see conversation history

Example interactions:
- "I need pricing for metformin"
- "What's my copay for Lipitor 20mg?"
- "My member ID is ABC123456"
- "How much will 90 days of atorvastatin cost?"

The assistant will automatically:
1. Find your specific drug from multiple options
2. Check your eligibility and plan benefits
3. Look up your year-to-date spending progress
4. Calculate exact pricing with all discounts
5. Show you the complete cost breakdown
"""
    console.print(Panel(help_text.strip(), title="How to Use", border_style="green"))

def print_function_call_info():
    """Print information about function calling"""
    info_text = """
🔧 Advanced Function Calling Features:

This demo shows how the OpenAI Assistant API orchestrates multiple services
to calculate accurate drug pricing, just like a real PBM system:

1. 📋 NDC Lookup - Search drug database and handle multiple matches
2. ✅ Eligibility Check - Verify member coverage and get basic info
3. 📊 Plan Benefits - Get detailed tier structure and benefit limits
4. 📈 Member Utilization - Check year-to-date spending and deductible progress
5. 💊 Formulary Check - Verify drug coverage and tier placement
6. 💰 Drug Costs - Get wholesale and plan negotiated pricing
7. 🎫 Coupon Check - Find available manufacturer discounts
8. 🧮 Pricing Calculator - Perform complex mathematical calculations

The assistant automatically determines which services to call and in what order,
then uses a mathematical calculator to ensure accurate pricing calculations!

Watch for function call indicators (🔧) showing the step-by-step process!
"""
    console.print(Panel(info_text.strip(), title="Advanced PBM Function Calling Demo", border_style="yellow"))

def main():
    """Main application loop"""
    
    # Check if API key is configured
    if not keys.OPENAI_API_KEY or keys.OPENAI_API_KEY == "your-openai-api-key-here":
        console.print("[red]Error: Please configure your OpenAI API key in keys.py[/red]")
        console.print("Set OPENAI_API_KEY = 'your-actual-api-key'")
        return
    
    print_header()
    print_function_call_info()
    print_help()
    
    # Initialize the assistant
    console.print("\n[yellow]Initializing Drug Pricing Assistant...[/yellow]")
    
    try:
        assistant_manager = DrugPricingAssistant()
        assistant_manager.create_assistant()
        assistant_manager.create_thread()
        
        console.print("[green]✅ Assistant ready! Start by asking about drug pricing.[/green]\n")
        
        # Main conversation loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("\n[yellow]Thank you for using the Drug Pricing Assistant![/yellow]")
                    break
                
                if user_input.lower() == 'help':
                    print_help()
                    continue
                
                if user_input.lower() == 'history':
                    history = assistant_manager.get_conversation_history()
                    console.print("\n[bold]Conversation History:[/bold]")
                    for msg in history:
                        role_color = "blue" if msg["role"] == "user" else "green"
                        console.print(f"[{role_color}]{msg['role'].title()}:[/{role_color}] {msg['content']}")
                    continue
                
                if not user_input:
                    continue
                
                # Send message to assistant
                console.print("\n[yellow]🤖 Assistant is thinking...[/yellow]")
                
                response = assistant_manager.send_message(user_input)
                
                # Display assistant response
                console.print(f"\n[bold green]Assistant:[/bold green] {response}")
                
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Session interrupted. Goodbye![/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")
                console.print("Please try again or type 'quit' to exit.")
    
    except Exception as e:
        console.print(f"[red]Failed to initialize assistant: {str(e)}[/red]")
        console.print("Please check your API key and try again.")

if __name__ == "__main__":
    main()
