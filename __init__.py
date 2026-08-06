"""
构建最小可用Agent--LemonsAgent
包级初始化：暴露版本号与最常用入口。

    from lemons_agents import AgentRunner
    AgentRunner().run()
"""
from .core.runner import AgentRunner

__version__ = "0.1.0"

__all__ = ["AgentRunner", "__version__"]
