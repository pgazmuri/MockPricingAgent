"""
Core functionality for the Multi-Agent Healthcare System.

This package contains the coordinator, models, and shared components
that enable multi-agent coordination and communication.
"""

from .agent_coordinator import MultiAgentCoordinator, AgentType, CoordinationMode
from .models import *
from .shared_prompts import *

__all__ = [
    'MultiAgentCoordinator',
    'AgentType',
    'CoordinationMode'
]
