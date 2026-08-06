"""核心框架层。

包级初始化（即框架文档中的 init.py / 初始化方法）：
对外暴露核心单例与常用入口，使使用方可以直接写：

    from lemons_agents.core import AgentRunner, MEMORY, SKILL_LOADER

而不必关心内部模块路径。

注意：以下导入顺序按模块依赖关系排列
（config → memory / skill → compactor → loop → runner），请勿随意调整，
否则 tools.registry 回导 core.skill 时可能出现循环导入。
"""
from .config import (
    COMPACT_AFTER_MESSAGES,
    COMPACT_PROMPT_PATH,
    MEMORY_DIR,
    MODEL,
    PACKAGE_ROOT,
    RECENT_MESSAGES,
    SKILLS_DIR,
    TEMPLATES_DIR,
    client,
)
from .memory import MEMORY, MemoryStore
from .skill import SKILL_LOADER, SkillLoader
from .session import Session, SessionManager
from .context import ContextManager
from .compactor import compact_history
from .loop import agent_turn, build_system_prompt
from .runner import AgentRunner

__all__ = [
    # config
    "client",
    "MODEL",
    "PACKAGE_ROOT",
    "SKILLS_DIR",
    "MEMORY_DIR",
    "TEMPLATES_DIR",
    "COMPACT_PROMPT_PATH",
    "RECENT_MESSAGES",
    "COMPACT_AFTER_MESSAGES",
    # memory
    "MemoryStore",
    "MEMORY",
    # skill
    "SkillLoader",
    "SKILL_LOADER",
    # session
    "Session",
    "SessionManager",
    # context
    "ContextManager",
    # compactor
    "compact_history",
    # loop
    "build_system_prompt",
    "agent_turn",
    # runner
    "AgentRunner",
]
