"""测试包初始化。

路径引导：把包的上级目录（工作区根）加入 sys.path，保证无论从哪个
工作目录、以哪种方式（CLI / PyCharm runner）运行测试，
`from lemons_agents.xxx import ...` 都能解析。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
