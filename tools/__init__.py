"""工具系统层。

包级初始化：暴露工具注册表、执行入口与调用 trace。

    from lemons_agents.tools import TOOLS, execute_tool, TRACER
"""
from .registry import TOOLS, execute_tool
from .trace import TRACER, ToolTracer

__all__ = ["TOOLS", "execute_tool", "TRACER", "ToolTracer"]
