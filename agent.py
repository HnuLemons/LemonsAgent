"""agent 的主启动方法。

运行方式（两种均可）：
    # 方式一：在 LemonsAgent 工作区根目录下，以包模块方式运行（推荐）
    python -m lemons_agents.agent

    # 方式二：直接运行本脚本（自动回退为绝对导入）
    python lemons_agents/agent.py

依赖：anthropic、python-dotenv、pyyaml
配置： lemons_agents/.env
"""
import sys
from pathlib import Path

if __package__:
    # 以 python -m lemons_agents.agent 方式运行：使用包内相对导入
    from .core.runner import AgentRunner
else:
    # 直接运行脚本时没有父包，把工作区根目录加入 sys.path 后改用绝对导入
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lemons_agents.core.runner import AgentRunner


def main():
    AgentRunner().run()


if __name__ == "__main__":
    main()
