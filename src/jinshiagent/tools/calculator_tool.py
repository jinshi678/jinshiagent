"""内置工具集 — 计算器工具

安全地计算数学表达式，支持基础算术运算。

使用示例::

    from jinshiagent.tools.calculator_tool import calculator

    result = calculator("12 * 8 + 3")
    print(result)  # 99

    result = calculator("2 ** 10")
    print(result)  # 1024
"""

from __future__ import annotations

import ast
import logging
import operator
from typing import Any

logger = logging.getLogger("jinshiagent.tools.calculator")

# 允许的运算符映射
_SAFE_OPERATORS: dict[type, Any] = {
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

# 允许的内置函数
_SAFE_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "int": int,
    "float": float,
}


def calculator(expression: str) -> str:
    """安全地计算数学表达式。

    支持加减乘除、幂运算、取模、括号和部分内置函数（abs/round/min/max）。
    不使用 eval()，基于 AST 解析确保安全性。

    Args:
        expression: 数学表达式字符串，例如 "12 * 8 + 3"

    Returns:
        计算结果文本

    Examples:
        >>> calculator("2 + 3 * 4")
        '14'
        >>> calculator("2 ** 10")
        '1024'
    """
    logger.debug("计算表达式: %s", expression)

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        logger.debug("计算结果: %s = %s", expression, result)
        return str(result)
    except SyntaxError as e:
        return f"表达式语法错误: {e}"
    except ZeroDivisionError:
        return "计算错误: 除以零"
    except (ValueError, TypeError) as e:
        return f"计算错误: {e}"
    except Exception as e:
        return f"计算失败: {e}"


def _eval_node(node: ast.AST) -> Any:
    """递归求值 AST 节点，仅允许安全的运算。"""
    if isinstance(node, ast.Constant):  # 数字字面量
        return node.value
    if isinstance(node, ast.Name):  # 变量名
        if node.id in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[node.id]
        raise ValueError(f"不允许的变量: {node.id}")
    if isinstance(node, ast.BinOp):  # 二元运算
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不允许的运算符: {type(node.op).__name__}")
        return op_func(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):  # 一元运算
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不允许的运算符: {type(node.op).__name__}")
        return op_func(_eval_node(node.operand))
    if isinstance(node, ast.Call):  # 函数调用
        func = _eval_node(node.func)
        args = [_eval_node(arg) for arg in node.args]
        return func(*args)
    if isinstance(node, ast.Attribute):
        raise ValueError("不允许属性访问")
    raise ValueError(f"不允许的表达式类型: {type(node).__name__}")
