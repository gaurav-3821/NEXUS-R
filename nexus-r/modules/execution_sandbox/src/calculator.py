import ast
import operator
import re
import math
from typing import Any

class SafeCalculator:
    def __init__(self):
        # We only want to intercept queries that are purely mathematical expressions.
        # If there's text like "what is 2+2" or "explain 2+2", we return None.
        self.math_only_pat = re.compile(r"^[\d\+\-\*\/\.\(\)\s\^\%]+$")
        
        # Mapping of ast operators to python operators
        self.ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
    def evaluate(self, query: str) -> str | None:
        """Evaluate a math expression safely. Returns answer string, or None if not pure math."""
        clean_query = query.strip()
        
        # Replace ^ with ** for python ast
        clean_query = clean_query.replace("^", "**")
        
        # Fast fail if it contains non-math characters
        if not self.math_only_pat.match(clean_query):
            # Special case for basic math functions like sqrt(16)
            if not re.match(r"^[\w\(\)\d\.\s]+$", clean_query):
                return None
                
        try:
            tree = ast.parse(clean_query, mode='eval')
            result = self._eval_node(tree.body)
            # Formatting: if it's a float that is exactly an integer, format it as such.
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return str(result)
        except Exception:
            return None
            
    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric constants allowed")
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = type(node.op)
            if op in self.ops:
                return self.ops[op](left, right)
            raise ValueError(f"Unsupported operator: {op}")
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = type(node.op)
            if op in self.ops:
                return self.ops[op](operand)
            raise ValueError(f"Unsupported unary operator: {op}")
        elif isinstance(node, ast.Call):
            # Safe subset of math functions
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name == "sqrt":
                    if len(node.args) != 1:
                        raise ValueError("sqrt takes exactly one argument")
                    return math.sqrt(self._eval_node(node.args[0]))
            raise ValueError("Unsupported function call")
        raise ValueError(f"Unsupported AST node: {type(node)}")
