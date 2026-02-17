"""
Calculator Tool — Safe math expression evaluator.
"""

import ast
import math
import operator
import logging
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Allowed operators for safe evaluation
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed math functions
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    """Recursively evaluate an AST node safely."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value}")
    elif isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(operand)
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
            func = _FUNCTIONS[node.func.id]
            args = [_safe_eval(arg) for arg in node.args]
            if callable(func):
                return func(*args)
            return func  # constants like pi, e
        raise ValueError(f"Unsupported function: {getattr(node.func, 'id', '?')}")
    elif isinstance(node, ast.Name):
        if node.id in _FUNCTIONS:
            val = _FUNCTIONS[node.id]
            if not callable(val):
                return val
        raise ValueError(f"Unknown variable: {node.id}")
    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Safe math expression evaluator."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate mathematical expressions safely. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, pi, e."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate, e.g. '2 + 3 * 4' or 'sqrt(16)'"
                }
            },
            "required": ["expression"],
        }

    async def execute(self, **kwargs) -> str:
        expression = kwargs.get("expression", "")
        if not expression:
            return "Error: No expression provided."

        try:
            tree = ast.parse(expression, mode="eval")
            result = _safe_eval(tree)
            logger.info("Calculator: %s = %s", expression, result)
            return f"{result}"
        except Exception as e:
            logger.warning("Calculator error for '%s': %s", expression, e)
            return f"Error: {e}"
