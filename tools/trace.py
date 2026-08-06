import json
from datetime import datetime
from pathlib import Path

from ..core.config import TOOL_TRACE_LOG

# 单条结果预览的最大字符数（完整结果在会话上下文中，日志只留预览）
_RESULT_PREVIEW_CHARS = 200


class ToolTracer:
    """工具调用记录器：内存环形缓冲 + JSONL 持久化。"""

    def __init__(self, log_path: Path = TOOL_TRACE_LOG, memory_limit: int = 50):
        self.log_path = Path(log_path)
        self.memory_limit = memory_limit
        self.entries: list[dict] = []

    def record(self, tool_name: str, tool_input: dict, result: str, duration_ms: float) -> dict:
        """记录一次工具调用，返回日志条目。"""
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tool": tool_name,
            "input": tool_input,
            "ok": not result.startswith("Error"),
            "duration_ms": round(duration_ms, 1),
            "result_chars": len(result),
            "result_preview": result[:_RESULT_PREVIEW_CHARS]
                              + ("..." if len(result) > _RESULT_PREVIEW_CHARS else ""),
        }

        self.entries.append(entry)
        if len(self.entries) > self.memory_limit:
            self.entries.pop(0)

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass  # 日志写入失败不影响工具主流程

        return entry

    def recent(self, n: int = 10) -> list[dict]:
        """返回最近 n 条调用记录（新的在后）。"""
        return self.entries[-n:]

    @staticmethod
    def format_entry(entry: dict) -> str:
        """把日志条目格式化为单行文本，供 /trace 展示。"""
        status = "OK " if entry["ok"] else "ERR"
        args = json.dumps(entry["input"], ensure_ascii=False, default=str)
        if len(args) > 40:
            args = args[:40] + "..."
        return (f"[{entry['ts']}] {status} {entry['tool']}({args}) "
                f"-> {entry['result_chars']} chars, {entry['duration_ms']} ms")


# 全局 trace 单例（registry.execute_tool 与 runner 的 /trace 命令共用）
TRACER = ToolTracer()
