"""Bounded arithmetic evaluator: no Python eval, names, attributes, or I/O."""

import ast
import json
import operator

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
FUNCTIONS = {"sum": sum, "min": min, "max": max, "sorted": sorted, "abs": abs, "len": len}


def calculate(expression: str) -> dict:
    if len(expression) > 12000:
        raise ValueError("expression too long")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 1500:
        raise ValueError("expression too complex")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return float(node.value)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [visit(x) for x in node.elts]
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            a, b = visit(node.left), visit(node.right)
            if not isinstance(a, (float, int)) or not isinstance(b, (float, int)):
                raise ValueError("arithmetic operands must be numeric")
            return OPERATORS[type(node.op)](a, b)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            x = visit(node.operand)
            return x if isinstance(node.op, ast.UAdd) else -x
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in FUNCTIONS or node.keywords or len(node.args) != 1:
                raise ValueError("allowed functions take one positional argument")
            return FUNCTIONS[node.func.id](visit(node.args[0]))
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            if node.slice.step is not None:
                raise ValueError("slice step unsupported")
            start = int(visit(node.slice.lower)) if node.slice.lower else None
            end = int(visit(node.slice.upper)) if node.slice.upper else None
            return visit(node.value)[start:end]
        raise ValueError("unsupported arithmetic syntax")

    result = visit(tree)
    json.dumps(result, allow_nan=False)
    return {"value": result}
