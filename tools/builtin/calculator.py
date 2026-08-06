import ast
import operator

# 允许的二元运算符白名单
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# 允许的一元运算符白名单
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval(node):
    """递归求值 AST 节点，遇到白名单外的语法直接抛 ValueError。"""
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"不支持的常量: {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    raise ValueError(f"不支持的表达式语法: {ast.dump(node)}")


def calculate(expression: str) -> str:
    """求值数学表达式，返回字符串结果；任何失败都返回错误说明而不是抛出。"""
    expression = expression.strip()
    if not expression:
        return "Error: 表达式为空"

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree)
    except ZeroDivisionError:
        return f"Error: 除数为 0 -> {expression}"
    except (ValueError, SyntaxError) as exc:
        return f"Error: 无法计算表达式 '{expression}': {exc}"
    except OverflowError:
        return f"Error: 计算结果溢出 -> {expression}"

    # 整数结果去掉 .0，输出更干净
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{expression} = {result}"
