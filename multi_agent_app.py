"""
Multi-Agent Healthcare Assistant Application

This is the main application that demonstrates the multi-agent architecture
with clean handoffs between specialized agents for healthcare services.

Agents:
- Coordinator: Routes requests and manages handoffs
- Authentication: Member verification and security
- Pricing: Drug costs and insurance calculations  
- Pharmacy: Prescription management and refills
- Benefits: Plan coverage and formulary information
- Clinical: Drug interactions and therapeutic alternatives
"""

import sys
import time
import signal
import atexit
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout
from rich.columns import Columns

from openai import OpenAI
import keys

# Import all agents
from agent_coordinator import MultiAgentCoordinator, AgentType
from auth_agent import AuthenticationAgent
from pricing_agent import PricingAgent
from pharmacy_agent import PharmacyAgent
from benefits_agent import BenefitsAgent
from clinical_agent import ClinicalAgent


class MultiAgentHealthcareApp:
    """Main application for multi-agent healthcare assistance"""
    
    def __init__(self):
        self.console = Console()
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
        self.coordinator = MultiAgentCoordinator()
        self.setup_agents()
        
    def setup_agents(self):
        """Initialize and register all specialized agents"""
        self.console.print("🚀 Initializing Multi-Agent Healthcare System...", style="bold blue")
        
        # Create and register agents
        agents = [
            ("Authentication Agent", AuthenticationAgent(self.client)),
            ("Pricing Agent", PricingAgent(self.client)),
            ("Pharmacy Agent", PharmacyAgent(self.client)),
            ("Benefits Agent", BenefitsAgent(self.client)),
            ("Clinical Agent", ClinicalAgent(self.client))
        ]
        
        for name, agent in agents:
            self.coordinator.register_agent(agent)
            self.console.print(f"✅ {name} initialized")
        
        self.console.print("\\n🎛️ Multi-Agent Coordinator ready!", style="bold green")
    
    def display_welcome(self):
        """Display welcome message and available services"""
        welcome_text = Text()
        welcome_text.append("🏥 Healthcare Multi-Agent Assistant\\n", style="bold blue")
        welcome_text.append("Intelligent healthcare services with specialized experts\\n\\n")
        
        # Create services table
        table = Table(title="Available Services", show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan")
        table.add_column("Services", style="white")
        table.add_column("Examples", style="dim")
        
        services = [
            ("🔐 Authentication", "Member verification, login, security", "\"Login with member ID\", \"Verify my identity\""),
            ("💰 Pricing", "Drug costs, insurance calculations", "\"How much is Lisinopril?\", \"Calculate my copay\""),
            ("🏥 Pharmacy", "Prescriptions, refills, transfers", "\"Check my prescriptions\", \"Request refill\""),
            ("📋 Benefits", "Plan coverage, formulary, benefits", "\"What's covered?\", \"Check my plan\""),
            ("⚕️ Clinical", "Drug interactions, alternatives", "\"Check interactions\", \"Find alternatives\"")
        ]
        
        for agent, service, examples in services:
            table.add_row(agent, service, examples)
        
        panel = Panel(
            Columns([welcome_text, table]),
            title="🤖 Multi-Agent Healthcare System",
            border_style="blue"
        )
        
        self.console.print(panel)
        self.console.print("\\n💡 The system will automatically route your questions to the right specialist!", style="dim")
        self.console.print("🔄 Agents can hand off to each other when you need different services.\\n", style="dim")
    
    def display_conversation_state(self):
        """Display current conversation state and agent status"""
        summary = self.coordinator.get_conversation_summary()
        
        state_table = Table(show_header=False, box=None, padding=(0, 1))
        state_table.add_column("Field", style="bold")
        state_table.add_column("Value", style="cyan")
        
        state_table.add_row("Current Agent:", summary["current_agent"].title())
        state_table.add_row("Available Agents:", ", ".join(summary["available_agents"]))
        state_table.add_row("Conversation Length:", str(summary["history_length"]))
        
        if summary["context"]:
            context_str = ", ".join([f"{k}: {v}" for k, v in list(summary["context"].items())[:3]])
            if len(context_str) > 50:
                context_str = context_str[:50] + "..."
            state_table.add_row("Context:", context_str)
        
        panel = Panel(
            state_table,
            title="📊 Conversation State",
            border_style="dim",
            width=50
        )
        
        return panel
    
    def run_demo_scenarios(self):
        """Run several demo scenarios to show agent handoffs"""
        self.console.print("\\n🎭 Running Demo Scenarios", style="bold yellow")
        self.console.print("Watch how agents hand off to each other based on your needs!\\n")
        
        scenarios = [
            {
                "title": "🔐 Authentication → 💰 Pricing Handoff",
                "description": "Starting with login, then asking about drug costs",
                "messages": [
                    "I need to log in with member ID DEMO123456",
                    "Now I want to know how much Lisinopril costs"
                ]
            },
            {
                "title": "💰 Pricing → 🏥 Pharmacy Handoff", 
                "description": "Price inquiry leads to prescription management",
                "messages": [
                    "What's the cost of my Metformin prescription?",
                    "Can I get a refill for that prescription?"
                ]
            },
            {
                "title": "📋 Benefits → ⚕️ Clinical Handoff",
                "description": "Coverage question leads to clinical alternatives",
                "messages": [
                    "Is Nexium covered by my plan?",
                    "What are some alternatives if it's not covered?"
                ]
            },
            {
                "title": "⚕️ Clinical → 💰 Pricing Handoff",
                "description": "Drug interaction check leads to cost comparison",
                "messages": [
                    "Check interactions between Lisinopril and Metformin",
                    "How much would the alternative drugs cost?"
                ]
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            self.console.print(f"\\n📋 Scenario {i}: {scenario['title']}", style="bold")
            self.console.print(f"   {scenario['description']}", style="dim")
            
            user_input = Prompt.ask(f"\\n[bold]Run this scenario?[/bold]", choices=["y", "n", "s"], default="y")
            
            if user_input == "n":
                continue
            elif user_input == "s":
                break
                
            for message in scenario["messages"]:
                self.console.print(f"\\n👤 [bold]User:[/bold] {message}")
                
                # Show processing indicator
                with Live("🤔 Processing...", console=self.console) as live:
                    response = self.coordinator.process_message(message)
                    live.update("✅ Complete!")
                
                self.console.print(f"🤖 [bold]Assistant:[/bold] {response}")
                
                # Show conversation state
                state_panel = self.display_conversation_state()
                self.console.print(state_panel)
                
                time.sleep(1)  # Brief pause between messages
        
        self.console.print("\\n✨ Demo scenarios complete! Now try your own questions.", style="bold green")
    
    def run_interactive_session(self):
        """Run interactive chat session"""
        self.console.print("\\n💬 Interactive Chat Session", style="bold blue")
        self.console.print("Type your questions and see the agents work together!")
        self.console.print("Commands: 'help', 'status', 'demo', 'quit'\\n")
        
        while True:
            try:
                # Show current state
                state_panel = self.display_conversation_state()
                self.console.print(state_panel)
                
                # Get user input
                user_input = Prompt.ask("\\n[bold cyan]You[/bold cyan]")
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'help':
                    self.display_welcome()
                    continue
                elif user_input.lower() == 'status':
                    summary = self.coordinator.get_conversation_summary()
                    self.console.print(f"Current state: {summary}", style="dim")
                    continue
                elif user_input.lower() == 'demo':
                    self.run_demo_scenarios()
                    continue
                
                # Process with coordinator
                with Live("🤔 Processing your request...", console=self.console) as live:
                    response = self.coordinator.process_message(user_input)
                    live.update("✅ Response ready!")
                
                # Display response in a nice panel
                response_panel = Panel(
                    response,
                    title=f"🤖 {self.coordinator.current_agent.value.title()} Agent",
                    border_style="green"
                )
                self.console.print(response_panel)
                
            except KeyboardInterrupt:
                self.console.print("\\n\\n👋 Session interrupted. Goodbye!", style="bold yellow")
                break
            except Exception as e:
                self.console.print(f"\\n❌ Error: {str(e)}", style="bold red")
                self.console.print("Please try again or type 'quit' to exit.")
    
    def run(self):
        """Main application entry point"""
        try:
            # Display welcome
            self.display_welcome()
            
            # Ask user what they want to do
            choice = Prompt.ask(
                "\\n[bold]What would you like to do?[/bold]",
                choices=["demo", "chat", "both"],
                default="both"
            )
            
            if choice in ["demo", "both"]:
                self.run_demo_scenarios()
            
            if choice in ["chat", "both"]:
                self.run_interactive_session()
            
            self.console.print("\\n👋 Thank you for using the Multi-Agent Healthcare System!", style="bold blue")
            
        except KeyboardInterrupt:
            self.console.print("\\n\\n👋 Application terminated. Goodbye!", style="bold yellow")
        except Exception as e:
            self.console.print(f"\\n❌ Application error: {str(e)}", style="bold red")
            sys.exit(1)


def main():
    """Application entry point"""
    app = MultiAgentHealthcareApp()
    app.run()


if __name__ == "__main__":
    main()
