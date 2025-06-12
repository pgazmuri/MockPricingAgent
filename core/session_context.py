"""
Session Context Manager

Manages scenario context that gets passed to IT operations tools
but not directly to agents, allowing for realistic mock data generation.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SessionContext:
    """Manages session-level context for tool mock data generation"""
    
    def __init__(self):
        self.scenario_context = "Normal operations, no specific issues known"
        self.session_start = datetime.now()
        self.session_id = f"session_{int(self.session_start.timestamp())}"
    
    def set_scenario(self, context: str) -> None:
        """Set the background scenario context for tool calls"""
        self.scenario_context = context
        print(f"📝 Scenario context updated: {context}")
    
    def get_context(self) -> str:
        """Get current scenario context"""
        return self.scenario_context
    
    def reset(self) -> None:
        """Reset to default context"""
        old_context = self.scenario_context
        self.scenario_context = "Normal operations, no specific issues known"
        print(f"🔄 Scenario reset from: '{old_context}' to default")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        return {
            "session_id": self.session_id,
            "scenario": self.scenario_context,
            "session_start": self.session_start.isoformat(),
            "duration_minutes": int((datetime.now() - self.session_start).total_seconds() / 60)
        }
    
    def display_status(self) -> str:
        """Get formatted status for display"""
        info = self.get_session_info()
        return f"Session: {info['session_id']} | Duration: {info['duration_minutes']}m | Scenario: {info['scenario'][:50]}{'...' if len(info['scenario']) > 50 else ''}"
