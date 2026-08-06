import os
from pathlib import Path

import anthropic  # 走 Anthropic 接口
from dotenv import load_dotenv

from .exceptions import ConfigError

# 包根目录（lemons_agents/）
PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# 全局路径
SKILLS_DIR = PACKAGE_ROOT / "Skill"         # skill 仓库
MEMORY_DIR = PACKAGE_ROOT / "memory"        # 记忆机制目录
TEMPLATES_DIR = PACKAGE_ROOT / "templates"  # 提示词模版目录
SESSIONS_DIR = PACKAGE_ROOT / "sessions"    # 会话存储目录（每个 session 一个 JSON 文件）
LOG_DIR = PACKAGE_ROOT / "logs"             # 运行日志目录
TOOL_TRACE_LOG = LOG_DIR / "tool_trace.jsonl"  # 工具调用 trace 日志（一行一条 JSON）
COMPACT_PROMPT_PATH = TEMPLATES_DIR / "agent" / "compact_prompt.md"

ENV_PATH = PACKAGE_ROOT / ".env"


def _require_env(name: str) -> str:
    """读取必需的环境变量，缺失或为占位符时抛出带指引的 ConfigError。"""
    value = os.environ.get(name)
    if not value or value == "your_api_key_here":
        raise ConfigError(
            f"缺少必需的环境变量 {name}。\n"
            f"请编辑 {ENV_PATH}，填入有效的 {name} 后重试。\n"
        )
    return value


def create_client() -> anthropic.Anthropic:
    """加载 .env 并创建 Anthropic 客户端，失败时抛出 ConfigError。"""
    if not ENV_PATH.exists():
        raise ConfigError(
            f"配置文件不存在：{ENV_PATH}\n"
            f"请创建该文件并至少写入：\n"
            f"  ANTHROPIC_API_KEY=你的密钥\n"
            f"  ANTHROPIC_BASE_URL=https://api.anthropic.com\n"
            f"  ANTHROPIC_MODEL=模型名"
        )

    # override=True：项目 .env 优先于 shell 环境变量，
    # 防止 shell 里残留的同名旧值（如旧 TAVILY_API_KEY）悄悄覆盖项目配置
    load_dotenv(ENV_PATH, override=True)  # 加载环境变量

    api_key = _require_env("ANTHROPIC_API_KEY")
    base_url = os.environ.get("ANTHROPIC_BASE_URL")  # 可选，SDK 有默认值

    try:
        return anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url
        )
    except Exception as exc:
        raise ConfigError(f"Anthropic 客户端创建失败：{exc}") from exc


def _load_model() -> str:
    return _require_env("ANTHROPIC_MODEL")


client = create_client()  # 全局客户端单例（import 时即完成配置校验）
MODEL = _load_model()     # 模型获取

# 记忆压缩相关常量
RECENT_MESSAGES = 10  # 最近消息数（压缩后保留）
COMPACT_AFTER_MESSAGES = int(os.environ.get("AGENT_MEMORY_COMPACT_AFTER", "18"))  # 触发压缩的历史消息阈值

# 上下文管理相关常量（core/context.py 使用）
MAX_TURNS = int(os.environ.get("AGENT_MAX_TURNS", "20"))  # 最大对话轮次（一轮 = 一条用户文本消息）
CONTEXT_MAX_MESSAGES = int(os.environ.get("AGENT_CONTEXT_MAX_MESSAGES", "40"))  # 上下文中最多保留的消息条数
TOOL_RESULT_MAX_CHARS = int(os.environ.get("AGENT_TOOL_RESULT_MAX_CHARS", "2000"))  # 单条工具结果最大字符数（超出截断）
