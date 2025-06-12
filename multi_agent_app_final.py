"""
Multi-Agent IT Operations Assistant Application

This is the main application that demonstrates the multi-agent architecture
for IT operations and outage investigation with session context management.

Agents:
- Coordinator: Routes requests and manages handoffs
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

# Import all agents and session context
from core.agent_coordinator import MultiAgentCoordinator, AgentType, CoordinationMode
from agents.investigator_agent import InvestigatorAgent
from agents.analysis_agent import AnalysisAgent
from agents.remediation_agent import RemediationAgent
from core.session_context import SessionContext


class MultiAgentITOpsApp:
    """Main application for multi-agent IT operations assistance"""
    
    def __init__(self, coordination_mode: CoordinationMode = CoordinationMode.SWARM):
        self.console = Console()
        self.client = OpenAI(api_key=keys.OPENAI_API_KEY)
        self.coordinator = MultiAgentCoordinator(coordination_mode=coordination_mode)
        self.session_context = SessionContext()
        self.setup_agents()
        
    def setup_agents(self):
        """Initialize and register all specialized agents"""
        self.console.print("🚀 Initializing Multi-Agent IT Operations System...", style="bold blue")        # Create and register agents with shared session context
        investigator = InvestigatorAgent(self.client, self.session_context)
        analysis = AnalysisAgent(self.client, model="gpt-4o-mini")  # Using better model for analysis
        remediation = RemediationAgent(self.client)
        
        agents = [
            ("Investigator Agent", investigator),
            ("Analysis Agent", analysis),
            ("Remediation Agent", remediation)
        ]
        
        for name, agent in agents:
            self.coordinator.register_agent(agent)
            self.console.print(f"✅ {name} initialized")
        
        self.console.print("\n🎛️ Multi-Agent Coordinator ready!", style="bold green")
        
    def display_welcome(self):
        """Display welcome message and available services"""
        welcome_text = Text()
        welcome_text.append("🖥️ IT Operations Multi-Agent Assistant\n", style="bold blue")
        welcome_text.append("Intelligent IT outage investigation with session context\n")
        welcome_text.append(f"Mode: {self.coordinator.get_coordination_mode().value.upper()}\n\n", style="bold magenta")
        
        # Display current session context
        session_info = self.session_context.display_status()
        welcome_text.append(f"📝 {session_info}\n\n", style="dim")
        
        # Create services table
        table = Table(title="Available Services", show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan")
        table.add_column("Services", style="white")
        table.add_column("Examples", style="dim")
        services = [
            ("🔍 Investigator", "Outage investigation, log analysis", "\"Server ABC is down\", \"Check VM-Web01 logs\""),
            ("🧠 Analysis", "Root cause analysis, remediation planning", "\"Analyze findings\", \"What should we do next?\""),
            ("🔧 Remediation", "Execute fixes and recovery procedures", "\"Execute the plan\", \"Restart the service\"")
        ]
        
        for agent, service, examples in services:
            table.add_row(agent, service, examples)
        
        # Create session commands table
        commands_table = Table(title="Session Commands", show_header=True, header_style="bold yellow")
        commands_table.add_column("Command", style="cyan")
        commands_table.add_column("Description", style="white")
        commands_table.add_column("Example", style="dim")
        
        session_commands = [
            ("set-scenario", "Set background scenario context", "\"set-scenario Server ABC network issues\""),
            ("show-scenario", "Display current scenario", "\"show-scenario\""),
            ("reset-scenario", "Reset to default scenario", "\"reset-scenario\"")
        ]
        
        for cmd, desc, example in session_commands:
            commands_table.add_row(cmd, desc, example)
        
        panel = Panel(
            Columns([welcome_text, table, commands_table]),
            title="🤖 Multi-Agent IT Operations System",
            border_style="blue"
        )
        self.console.print(panel)
        
        mode = self.coordinator.get_coordination_mode()
        if mode == CoordinationMode.COORDINATOR:
            self.console.print("🎛️ COORDINATOR MODE: Agents always route back to coordinator for decision making", style="dim")
        else:
            self.console.print("🔗 SWARM MODE: Direct investigation without routing", style="dim")
        
        self.console.print("💡 The system will automatically investigate IT issues using realistic mock data!", style="dim")
        self.console.print("🎭 Try different scenarios to see how context affects investigation results.\n", style="dim")
    
    def display_conversation_state(self):
        """Display current conversation state and agent status"""
        summary = self.coordinator.get_conversation_summary()
        
        state_table = Table(show_header=False, box=None, padding=(0, 1))
        state_table.add_column("Field", style="bold")
        state_table.add_column("Value", style="cyan")
        
        state_table.add_row("Current Agent:", summary["current_agent"].title())
        state_table.add_row("Available Agents:", ", ".join(summary["available_agents"]))
        state_table.add_row("Conversation Length:", str(summary["history_length"]))
        state_table.add_row("Session Context:", self.session_context.get_context()[:50] + "..." if len(self.session_context.get_context()) > 50 else self.session_context.get_context())
        
        if summary["context"]:
            context_str = ", ".join([f"{k}: {v}" for k, v in list(summary["context"].items())[:2]])
            if len(context_str) > 40:
                context_str = context_str[:40] + "..."
            state_table.add_row("Agent Context:", context_str)
        
        panel = Panel(
            state_table,
            title="📊 Conversation State",
            border_style="dim",
            width=60
        )
        
        return panel
    
    def handle_session_commands(self, user_input: str) -> bool:
        """Handle session context commands, return True if command was handled"""
        lower_input = user_input.lower().strip()
        
        if lower_input.startswith("set-scenario "):
            scenario = user_input[13:].strip()  # Remove "set-scenario " prefix
            if scenario:
                self.session_context.set_scenario(scenario)
                self.console.print(f"✅ Scenario updated: {scenario}", style="bold green")
            else:
                self.console.print("❌ Please provide a scenario description", style="bold red")
            return True
            
        elif lower_input == "show-scenario":
            current = self.session_context.get_context()
            info = self.session_context.get_session_info()
            self.console.print(f"📝 Current scenario: {current}", style="bold")
            self.console.print(f"🕒 Session duration: {info['duration_minutes']} minutes", style="dim")
            return True
            
        elif lower_input == "reset-scenario":
            self.session_context.reset()
            self.console.print("🔄 Scenario reset to default", style="bold yellow")
            return True
            
        return False
    
    def run_demo_scenarios(self):
        """Run several demo scenarios to show different investigation contexts"""
        self.console.print("\n🎭 Running Demo Scenarios", style="bold yellow")
        self.console.print("Watch how session context affects investigation results!\n")
        
        scenarios = [
            {
                "title": "🔧 Planned Maintenance Investigation",
                "scenario": "Scheduled SQL server maintenance window, servers were rebooted at 2 AM",
                "messages": [
                    "Database connectivity issues started this morning",
                    "Check ServiceNow tickets for any related maintenance"
                ]
            },
            {
                "title": "🚨 Network Security Incident", 
                "scenario": "Potential security breach, port 1433 being blocked by firewall, suspicious traffic detected",
                "messages": [
                    "SQL Server connections are being denied",
                    "Check flow logs for VM-DB-01 and look for denied connections"
                ]
            },
            {
                "title": "🔍 Application Performance Issue",
                "scenario": "Web application slow response times, high CPU usage on web servers",
                "messages": [
                    "Users reporting slow website performance",
                    "Search Splunk for errors on VM-Web01 in the last 4 hours"
                ]
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            self.console.print(f"\n📋 Scenario {i}: {scenario['title']}", style="bold")
            self.console.print(f"   Context: {scenario['scenario']}", style="dim")
            
            user_input = Prompt.ask(f"\n[bold]Run this scenario?[/bold]", choices=["y", "n", "s"], default="y")
            if user_input == "n":
                continue
            elif user_input == "s":
                break
            
            # Set the scenario context
            self.session_context.set_scenario(scenario['scenario'])
            self.console.print(f"📝 Scenario context set: {scenario['scenario']}", style="bold cyan")
            
            for message in scenario["messages"]:
                self.console.print(f"\n👤 [bold]User:[/bold] {message}")
                
                # Show processing indicator
                with Live("🤔 Investigating...", console=self.console) as live:
                    response_text = ""
                    for chunk in self.coordinator.process_message(message):
                        response_text += chunk
                    live.update("✅ Investigation complete!")
                
                self.console.print(f"🤖 [bold]Assistant:[/bold] {response_text}")
                
                # Show conversation state
                state_panel = self.display_conversation_state()
                self.console.print(state_panel)
                
                time.sleep(1)  # Brief pause between messages
        
        # Reset scenario after demos
        self.session_context.reset()
        self.console.print("\n✨ Demo scenarios complete! Scenario reset to default.", style="bold green")
        
    def run_interactive_session(self):
        """Run interactive chat session"""
        self.console.print("\n💬 Interactive Chat Session", style="bold blue")
        self.console.print("Type your questions and see the investigation tools work with context!")
        self.console.print("Commands: 'help', 'status', 'demo', 'mode', 'set-scenario <text>', 'show-scenario', 'reset-scenario', 'quit'\n")
        
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
                elif self.handle_session_commands(user_input):
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
