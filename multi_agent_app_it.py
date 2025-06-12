"""
Multi-Agent IT Operations Assistant Application

This is the main application that demonstrates the multi-agent architecture
with clean handoffs between specialized agents for IT operations and outage investigation.

Agents:
- Coordinator: Routes requests and manages handoffs
- Authentication: User verification and security
- Investigator: Server and application outage investigation
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
import config.keys as keys

# Import all agents
from core.agent_coordinator import MultiAgentCoordinator, AgentType, CoordinationMode
from agents.auth_agent import AuthenticationAgent
from agents.investigator_agent import InvestigatorAgent


class MultiAgentITOpsApp:
    """Main application for multi-agent IT operations assistance"""
    
    def __init__(self, coordination_mode: CoordinationMode = CoordinationMode.SWARM):
        self.console = Console()
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
        self.coordinator = MultiAgentCoordinator(coordination_mode=coordination_mode)
        self.setup_agents()
        
    def setup_agents(self):
        """Initialize and register all specialized agents"""
        self.console.print("🚀 Initializing Multi-Agent IT Operations System...", style="bold blue")
        
        # Create and register agents
        agents = [
            ("Authentication Agent", AuthenticationAgent(self.client)),
            ("Investigator Agent", InvestigatorAgent(self.client))
        ]
        
        for name, agent in agents:
            self.coordinator.register_agent(agent)
            self.console.print(f"✅ {name} initialized")
        
        self.console.print("\n🎛️ Multi-Agent Coordinator ready!", style="bold green")
        
    def display_welcome(self):
        """Display welcome message and available services"""
        welcome_text = Text()
        welcome_text.append("🖥️ IT Operations Multi-Agent Assistant\n", style="bold blue")
        welcome_text.append("Intelligent IT outage investigation with specialized experts\n")
        welcome_text.append(f"Mode: {self.coordinator.get_coordination_mode().value.upper()}\n\n", style="bold magenta")
        
        # Create services table
        table = Table(title="Available Services", show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan")
        table.add_column("Services", style="white")
        table.add_column("Examples", style="dim")
        
        services = [
            ("🔐 Authentication", "User verification, login, security", "\"Login with user ID\", \"Verify my identity\""),
            ("🔍 Investigator", "Outage investigation, log analysis", "\"Server ABC is down\", \"Check network issues for VM-Web01\"")
        ]
        
        for agent, service, examples in services:
            table.add_row(agent, service, examples)
        
        panel = Panel(
            Columns([welcome_text, table]),
            title="🤖 Multi-Agent IT Operations System",
            border_style="blue"
        )
        self.console.print(panel)
        
        mode = self.coordinator.get_coordination_mode()
        if mode == CoordinationMode.COORDINATOR:
            self.console.print("🎛️ COORDINATOR MODE: Agents always route back to coordinator for decision making", style="dim")
        else:
            self.console.print("🔗 SWARM MODE: Agents can hand off directly to each other when needed", style="dim")
        
        self.console.print("💡 The system will automatically route your questions to the right specialist!", style="dim")
        self.console.print("🔄 Try asking follow-up questions to see how agents work together.\n", style="dim")
    
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
    
    def switch_coordination_mode(self):
        """Switch between coordinator and swarm modes and reset conversation"""
        current_mode = self.coordinator.get_coordination_mode()
        new_mode = CoordinationMode.COORDINATOR if current_mode == CoordinationMode.SWARM else CoordinationMode.SWARM
        
        self.console.print(f"\n🔄 Switching from {current_mode.value.upper()} to {new_mode.value.upper()} mode...", style="bold yellow")
        
        # Set the new coordination mode
        self.coordinator.set_coordination_mode(new_mode)
        
        # Update system prompts and tools for all agents
        for agent in self.coordinator.agents.values():
            agent.system_prompt = agent.get_system_prompt()
            agent.tools = agent.get_tools()
        
        # Reset conversation state for clean start in new mode
        self.coordinator.reset_conversation()
        
        self.console.print(f"✅ Successfully switched to {new_mode.value.upper()} mode!", style="bold green")
        self.console.print("💫 Conversation state has been reset for the new coordination mode.", style="dim")
        self.display_welcome()
        
    def run_demo_scenarios(self):
        """Run several demo scenarios to show agent handoffs"""
        self.console.print("\n🎭 Running Demo Scenarios", style="bold yellow")
        self.console.print("Watch how agents hand off to each other based on your needs!\n")
        
        scenarios = [
            {
                "title": "🔐 Authentication → 🔍 Investigation Handoff",
                "description": "Starting with login, then investigating an outage",
                "messages": [
                    "I need to log in with user ID ops_admin_123",
                    "Server ABC is down, can you investigate?"
                ]
            },
            {
                "title": "🔍 Multi-Tool Investigation", 
                "description": "Using multiple investigation tools for comprehensive analysis",
                "messages": [
                    "VM-Web01 is having connectivity issues",
                    "Check the flow logs and recent deployments"
                ]
            },
            {
                "title": "🔍 Log Analysis Workflow",
                "description": "Splunk search followed by ticket correlation",
                "messages": [
                    "Search Splunk for errors on server DB-Prod-01",
                    "Check if there are any ServiceNow tickets for this server"
                ]
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            self.console.print(f"\n📋 Scenario {i}: {scenario['title']}", style="bold")
            self.console.print(f"   {scenario['description']}", style="dim")
            
            user_input = Prompt.ask(f"\n[bold]Run this scenario?[/bold]", choices=["y", "n", "s"], default="y")
            if user_input == "n":
                continue
            elif user_input == "s":
                break
                
            for message in scenario["messages"]:
                self.console.print(f"\n👤 [bold]User:[/bold] {message}")
                
                # Show processing indicator
                with Live("🤔 Processing...", console=self.console) as live:
                    response_text = ""
                    for chunk in self.coordinator.process_message(message):
                        response_text += chunk
                    live.update("✅ Complete!")
                
                self.console.print(f"🤖 [bold]Assistant:[/bold] {response_text}")
                
                # Show conversation state
                state_panel = self.display_conversation_state()
                self.console.print(state_panel)
                
                time.sleep(1)  # Brief pause between messages
        
        self.console.print("\n✨ Demo scenarios complete! Now try your own questions.", style="bold green")
        
    def run_interactive_session(self):
        """Run interactive chat session"""
        self.console.print("\n💬 Interactive Chat Session", style="bold blue")
        self.console.print("Type your questions and see the agents work together!")
        self.console.print("Commands: 'help', 'status', 'demo', 'mode', 'quit'\n")
        
        while True:
            try:
                # Show current state
                state_panel = self.display_conversation_state()
                self.console.print(state_panel)
                
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
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
                elif user_input.lower() == 'mode':
                    self.switch_coordination_mode()
                    continue
                
                # Process with coordinator
                with Live("🤔 Processing your request...", console=self.console) as live:
                    response_text = ""
                    for chunk in self.coordinator.process_message(user_input):
                        response_text += chunk
                        live.update(f"🤔 Processing... {response_text[-20:]}")
                    live.update("✅ Response ready!")
                
                # Display response in a nice panel
                response_panel = Panel(
                    response_text,
                    title=f"🤖 {self.coordinator.current_agent.value.title()} Agent",
                    border_style="green"
                )
                self.console.print(response_panel)
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 Session interrupted. Goodbye!", style="bold yellow")
                break
            except Exception as e:
                self.console.print(f"\n❌ Error: {str(e)}", style="bold red")
                self.console.print("Please try again or type 'quit' to exit.")
    
    def run(self):
        """Main application entry point"""
        try:
            # Display welcome
            self.display_welcome()
            
            # Ask user what they want to do
            choice = Prompt.ask(
                "\n[bold]What would you like to do?[/bold]",
                choices=["demo", "chat", "both"],
                default="both"
            )
            
            if choice in ["demo", "both"]:
                self.run_demo_scenarios()
            
            if choice in ["chat", "both"]:
                self.run_interactive_session()
            
            self.console.print("\n👋 Thank you for using the Multi-Agent IT Operations System!", style="bold blue")
            
        except KeyboardInterrupt:
            self.console.print("\n\n👋 Application terminated. Goodbye!", style="bold yellow")
        except Exception as e:
            self.console.print(f"\n❌ Application error: {str(e)}", style="bold red")
            sys.exit(1)


def main():
    """Application entry point"""
    app = MultiAgentITOpsApp()
    app.run()


if __name__ == "__main__":
    main()
