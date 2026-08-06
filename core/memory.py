import json
from datetime import datetime
from pathlib import Path

from .config import MEMORY_DIR, TEMPLATES_DIR


def _json_safe(value):
    """把 Anthropic SDK 返回的消息内容安全地转换为可 JSON 序列化的结构。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    return str(value)


class MemoryStore:
    def __init__(self, memory_dir: Path, templates_dir: Path):
        self.memory_dir = memory_dir
        self.memory_file = memory_dir / "MEMORY.md"              # 核心记忆文件
        self.history_file = memory_dir / "history.jsonl"         # 原始对话记录
        self.episode_dir = memory_dir / "Contextual memory"      # 情景记忆目录
        self.user_file = templates_dir / "USER.md"               # 用户档案

    def ensure_files(self) -> bool:  # 用于确认文件路径是否存在
        """创建缺失的目录与文件。返回 False 表示文件系统不可用（后续操作应跳过）。"""
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)  # 父目录不存在则创建，存在也不报错
            self.episode_dir.mkdir(parents=True, exist_ok=True)
            self.user_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.memory_file.exists():  # 初始化
                self.memory_file.write_text("# Long-term Memory\n\n", encoding="utf-8")
            if not self.user_file.exists():
                self.user_file.write_text("# User Profile\n\n", encoding="utf-8")
            if not self.history_file.exists():
                self.history_file.touch()
            return True
        except OSError as exc:
            print(f"[记忆文件初始化失败]: {exc}")
            return False

    def append_history(self, message: dict):
        if not self.ensure_files():
            return
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),  # isoformat 时间戳转换函数
            "role": message.get("role"),
            "content": _json_safe(message.get("content")),
        }
        try:
            with self.history_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"[对话记录写入失败]: {exc}")

    def read_memory(self) -> str:
        if not self.ensure_files():
            return ""
        try:
            return self.memory_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[长期记忆读取失败]: {exc}")
            return ""

    def write_memory(self, text: str):
        if not self.ensure_files():
            return
        try:
            self.memory_file.write_text(text.strip() + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"[长期记忆写入失败]: {exc}")

    def read_user(self) -> str:
        if not self.ensure_files():
            return ""
        try:
            return self.user_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[用户档案读取失败]: {exc}")
            return ""

    def write_user(self, text: str):
        if not self.ensure_files():
            return
        try:
            self.user_file.write_text(text.strip() + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"[用户档案写入失败]: {exc}")

    def today_episode_file(self) -> Path:
        return self.episode_dir / f"{datetime.now():%Y-%m-%d}.md"

    def read_today_episode(self) -> str:
        if not self.ensure_files():
            return ""
        path = self.today_episode_file()
        try:
            return path.read_text(encoding="utf-8") if path.exists() else ""
        except OSError as exc:
            print(f"[情景记忆读取失败]: {exc}")
            return ""

    def append_episode(self, text: str):
        if not self.ensure_files():
            return
        try:
            with self.today_episode_file().open("a", encoding="utf-8") as f:
                f.write("\n" + text.strip() + "\n")
        except OSError as exc:
            print(f"[情景记忆写入失败]: {exc}")


# 全局记忆存储单例（与原始代码中的 MEMORY 对应）
MEMORY = MemoryStore(MEMORY_DIR, TEMPLATES_DIR)
