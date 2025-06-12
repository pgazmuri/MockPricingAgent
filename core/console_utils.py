"""
Console Utilities

Centralized utilities for displaying information in the console with consistent formatting.
"""

import json
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def display_tool_result(function_name: str, function_args: Dict[str, Any], result: str, agent_name: str = "", agent_emoji: str = "🔧") -> None:
    """
    Display tool call results in a bounded box similar to conversation state display.
    
    Args:
        function_name: Name of the function that was called
        function_args: Arguments passed to the function
        result: JSON string result from the function
        agent_name: Name of the agent calling the tool (optional)
        agent_emoji: Emoji for the agent (optional)
    """
    console = Console()
    
    # Parse result to extract key information
    try:
        result_data = json.loads(result)
    except json.JSONDecodeError:
        result_data = {"raw_result": result}
    
    # Create table for tool call information
    tool_table = Table(show_header=False, box=None, padding=(0, 1))
    tool_table.add_column("Field", style="bold yellow")
    tool_table.add_column("Value", style="white")
    
    # Add basic tool information
    tool_table.add_row("Function:", function_name)
    
    # Format arguments (limit length for display)
    args_str = ", ".join([f"{k}={v}" for k, v in function_args.items()])
    if len(args_str) > 60:
        args_str = args_str[:60] + "..."
    tool_table.add_row("Arguments:", args_str)
    
    # Extract and display key result fields
    if isinstance(result_data, dict):
        # For structured results, show key fields
        key_fields = ["status", "count", "total", "found", "result", "message", "error"]
        
        for field in key_fields:
            if field in result_data:
                value = result_data[field]
                if isinstance(value, (list, dict)):
                    # For complex types, show count or summary
                    if isinstance(value, list):
                        display_value = f"{len(value)} items"
                    else:
                        display_value = f"{len(value)} fields"
                else:
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:50] + "..."
                tool_table.add_row(f"{field.title()}:", display_value)
    else:
        # For simple results, show the value directly
        display_value = str(result_data)
        if len(display_value) > 60:
            display_value = display_value[:60] + "..."
        tool_table.add_row("Result:", display_value)
    
    # Create title with agent info if provided
    if agent_name:
        title = f"{agent_emoji} {agent_name} Tool Result"
    else:
        title = f"{agent_emoji} Tool Result"
    
    # Create panel with tool result
    panel = Panel(
        tool_table,
        title=title,
        border_style="blue",
        width=80
    )
    
    console.print(panel)


def display_brief_tool_result(function_name: str, summary: str, agent_emoji: str = "🔧") -> None:
    """
    Display a brief tool result for simple cases.
    
    Args:
        function_name: Name of the function that was called
        summary: Brief summary of the result
        agent_emoji: Emoji for the tool call
    """
    console = Console()
    
    # Create a simple text display
    result_text = Text()
    result_text.append(f"{agent_emoji} ", style="bold blue")
    result_text.append(f"{function_name}: ", style="bold yellow")
    result_text.append(summary, style="white")
    
    # Create a simple panel
    panel = Panel(
        result_text,
        border_style="dim blue",
        padding=(0, 1),
        width=80
    )
    
    console.print(panel)


def get_tool_summary(function_name: str, result_data: Dict[str, Any]) -> str:
    """
    Generate a brief summary of tool results for console display.
    
    Args:
        function_name: Name of the function
        result_data: Parsed result data
    
    Returns:
        Brief summary string
    """
    if "error" in result_data:
        return f"❌ Error: {result_data['error']}"
    
    # Function-specific summaries
    if function_name == "splunk_search":
        count = result_data.get("results_count", 0)
        return f"📊 Found {count} events"
    
    elif function_name == "check_flow_logs":
        denied = len(result_data.get("denied_connections", []))
        return f"🚫 Found {denied} denied connections"
    
    elif function_name == "check_snow_tickets":
        tickets = result_data.get("tickets_found", 0)
        return f"📋 Found {tickets} tickets"
    
    elif function_name == "get_deployments":
        deployments = result_data.get("deployments_found", 0)
        return f"🚀 Found {deployments} deployments"
    
    elif function_name in ["ndcLookup", "ndc_lookup"]:
        if "result" in result_data and isinstance(result_data["result"], list):
            return f"💊 Found {len(result_data['result'])} drugs"
        return "💊 Drug lookup completed"
    
    elif function_name in ["calculateRxPrice", "calculate_rx_price"]:
        if "result" in result_data and "member_cost" in result_data["result"]:
            cost = result_data["result"]["member_cost"]
            return f"💰 Member cost: ${cost}"
        return "💰 Price calculated"
    
    elif function_name == "verify_member_identity":
        verified = result_data.get("verified", False)
        return f"✅ Identity verified" if verified else "❌ Identity not verified"
    
    elif function_name == "check_drug_interactions":
        interactions = result_data.get("total_interactions", 0)
        return f"⚠️ Found {interactions} interactions"
    
    # Generic summary
    if "count" in result_data:
        return f"📊 Count: {result_data['count']}"
    elif "total" in result_data:
        return f"📊 Total: {result_data['total']}"
    elif "status" in result_data:
        return f"📊 Status: {result_data['status']}"
    else:
        return "✅ Completed successfully"
