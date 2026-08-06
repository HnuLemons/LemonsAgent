import json
import uuid
from datetime import datetime
from pathlib import Path

from .config import SESSIONS_DIR
from .exceptions import SessionNotFoundError
from .memory import _json_safe


class Session:
    """一个独立的会话：id + 创建时间 + 独立的消息历史。"""

    def __init__(self, session_id: str, created_at: str, history: list[dict] | None = None):
        self.id = session_id
        self.created_at = created_at
        self.history: list[dict] = history if history is not None else []

    def preview(self, max_chars: int = 20) -> str:
        """取首条用户消息作为会话预览（用于 /list 展示）。"""
        for msg in self.history:
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                text = msg["content"].replace("\n", " ")
                return text[:max_chars] + ("..." if len(text) > max_chars else "")
        return "(空会话)"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "history": _json_safe(self.history),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            session_id=data["id"],
            created_at=data.get("created_at", ""),
            history=data.get("history", []),
        )


class SessionManager:
    """会话管理器：负责会话的创建、保存、加载与列举。"""

    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        # 只取文件名部分，防止 session_id 被注入路径穿越字符（如 ../）
        safe_name = Path(session_id).name
        return self.sessions_dir / f"{safe_name}.json"

    @staticmethod
    def _new_id() -> str:
        return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"

    def create(self) -> Session:
        """创建一个新会话（尚未落盘，首轮对话后由 save 持久化）。"""
        return Session(session_id=self._new_id(), created_at=datetime.now().isoformat(timespec="seconds"))

    def save(self, session: Session):
        """把会话完整写入磁盘（每轮对话后调用，覆盖写保证与内存一致）。"""
        path = self._path(session.id)
        path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, session_id: str) -> Session:
        """按 id 加载会话，支持 id 前缀匹配（如只输入前几位）。"""
        session_id = self._resolve_id(session_id)
        path = self._path(session_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SessionNotFoundError(f"会话文件损坏或不可读：{path.name}（{exc}）") from exc
        return Session.from_dict(data)

    def list(self) -> list[Session]:
        """列出所有会话，按创建时间升序。"""
        sessions = []
        for f in sorted(self.sessions_dir.glob("*.json")):
            try:
                sessions.append(Session.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError, KeyError):
                continue  # 跳过损坏的会话文件，不影响其他会话
        return sessions

    def _resolve_id(self, session_id: str) -> str:
        """精确匹配失败时尝试唯一前缀匹配，都不满足则抛 SessionNotFoundError。"""
        if self._path(session_id).exists():
            return session_id
        matches = [s.id for s in self.list() if s.id.startswith(session_id)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise SessionNotFoundError(
                f"会话 id 前缀 '{session_id}' 匹配到 {len(matches)} 个会话，请输入更长的前缀"
            )
        raise SessionNotFoundError(f"未找到会话 '{session_id}'，可用 /list 查看所有会话")
