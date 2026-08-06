"""异常体系：框架统一的自定义异常类型。"""

class AgentError(Exception):
    """框架基础异常，所有自定义异常的父类。"""


class ConfigError(AgentError):
    """配置错误：.env 缺失、必需环境变量未配置、客户端创建失败等。"""


class ToolExecutionError(AgentError):
    """工具执行失败（预留：tools/ 层后续统一抛此异常）。"""


class SkillNotFoundError(AgentError):
    """技能不存在（预留：core/skill.py 后续可改抛此异常）。"""


class MemoryStoreError(AgentError):
    """记忆读写失败（预留：core/memory.py 后续可改抛此异常）。"""


class SessionNotFoundError(AgentError):
    """会话不存在：切换 / 加载会话时未找到指定的 session id。"""
