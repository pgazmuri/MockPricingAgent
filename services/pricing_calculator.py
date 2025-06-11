"""
Mathematical Calculator Tool

This module provides simple mathematical calculation functions that the OpenAI Assistant
can use to perform reliable step-by-step drug pricing calculations.
"""

import json

class MathCalculator:
    """Simple mathematical calculator for reliable calculations"""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers"""
        return round(a + b, 2)
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a"""
        return round(a - b, 2)
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers"""
        return round(a * b, 2)
    
    def divide(self, a: float, b: float) -> float:
        """Divide a by b"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return round(a / b, 2)
    
    def calculate_percentage(self, amount: float, percentage: float) -> float:
        """Calculate percentage of an amount (e.g., 20% of 100 = 20)"""
        return round(amount * (percentage / 100), 2)
    
    def apply_minimum(self, value: float, minimum: float) -> float:
        """Return the larger of two values (apply minimum)"""
        return round(max(value, minimum), 2)
    
    def apply_maximum(self, value: float, maximum: float) -> float:
        """Return the smaller of two values (apply maximum/cap)"""
        return round(min(value, maximum), 2)
