import time

from ..core.skill import SKILL_LOADER
from .base import BaseTool
from .builtin.calculator import calculate
from .builtin.run_command import run_shell_command
from .builtin.search import web_search
from .trace import TRACER
from .builtin.weather import get_weather


# ---- 工具定义（BaseTool 子类）----

class RunCommandTool(BaseTool):
    name = "run_command"
    description = "在终端执行一条 shell 命令并返回输出"
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的 shell 命令"},
        },
        "required": ["command"],
    }

    def run(self, tool_input: dict) -> str:
        command = tool_input["command"]
        print(f"[执行命令]: {command}")
        output = run_shell_command(command)
        print(f"[命令输出]: {output}")
        return output


class LoadSkillTool(BaseTool):
    name = "load_skill"
    description = "加载指定技能的详细知识内容，在回答相关问题前调用"
    input_schema = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "技能名称，必须是系统提示中列出的可用技能之一",
            },
        },
        "required": ["skill_name"],
    }

    def run(self, tool_input: dict) -> str:
        skill_name = tool_input["skill_name"]
        print(f"[加载技能]: {skill_name}")
        return SKILL_LOADER.get_content(skill_name)


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "计算数学表达式，支持四则运算、幂、取余、整除、括号"
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "要计算的数学表达式，如 (3+5)*2"},
        },
        "required": ["expression"],
    }

    def run(self, tool_input: dict) -> str:
        expression = tool_input["expression"]
        print(f"[计算]: {expression}")
        return calculate(expression)


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "搜索网络实时信息（Tavily API），返回相关网页标题、链接与摘要"
    input_schema = {
        "type": "object",
        "properties": {
            "query":       {"type": "string",  "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "最大返回结果数，默认 5"},
        },
        "required": ["query"],
    }

    def run(self, tool_input: dict) -> str:
        query = tool_input["query"]
        max_results = tool_input.get("max_results", 5)
        print(f"[搜索]: {query}")
        return web_search(query, max_results)


class WeatherTool(BaseTool):
    name = "weather"
    description = "查询指定城市的实时天气情况，包括天气、气温、湿度、风力"
    input_schema = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名，如 北京、上海"},
        },
        "required": ["city"],
    }

    def run(self, tool_input: dict) -> str:
        city = tool_input["city"]
        print(f"[天气查询]: {city}")
        return get_weather(city)


# ---- 工具注册表 ----

REGISTERED_TOOLS: list[BaseTool] = [
    RunCommandTool(),
    LoadSkillTool(),
    CalculatorTool(),
    WebSearchTool(),
    WeatherTool(),
]

# 供 Anthropic tool_use 使用的工具描述列表（由注册表自动生成）
TOOLS = [t.to_schema() for t in REGISTERED_TOOLS]

# 工具名 -> 执行方法 的分发表
_DISPATCH = {t.name: t.run for t in REGISTERED_TOOLS}


def execute_tool(block) -> str:
    """
        执行模型请求的工具调用。
    """
    run = _DISPATCH.get(block.name)
    if run is None:
        return f"Error: Unknown tool '{block.name}'"

    start = time.perf_counter()
    try:
        result = run(block.input or {})
    except Exception as exc:
        result = f"Error: tool '{block.name}' 执行失败: {exc}"

    if not isinstance(result, str):
        result = str(result)

    duration_ms = (time.perf_counter() - start) * 1000
    TRACER.record(block.name, block.input or {}, result, duration_ms)
    return result
