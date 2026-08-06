import json
import re
from datetime import datetime

from .config import (
    COMPACT_AFTER_MESSAGES,
    COMPACT_PROMPT_PATH,
    MODEL,
    RECENT_MESSAGES,
    client,
)
from .memory import MEMORY, _json_safe


# 辅助工具函数
def _messages_to_text(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        role = msg.get("role", "?")
        content = json.dumps(_json_safe(msg.get("content")), ensure_ascii=False)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _extract_tag(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def compact_history(history: list[dict]) -> list[dict]:
    if len(history) <= COMPACT_AFTER_MESSAGES:
        return history

    old_messages = history[:-RECENT_MESSAGES]
    recent_messages = history[-RECENT_MESSAGES:]
    if not old_messages:
        return history

    prompt_template = COMPACT_PROMPT_PATH.read_text(encoding="utf-8")  # 读取提示词模版
    prompt = prompt_template.format(  # 填充提示词模版
        old_conversation=_messages_to_text(old_messages),
        current_memory=MEMORY.read_memory(),
        current_user=MEMORY.read_user(),
        today_episode=MEMORY.read_today_episode(),
        now_hhmm=datetime.now().strftime("%H:%M"),
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system="你是记忆整理员。请严格按要求输出 XML，不要输出额外解释。",
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in message.content if b.type == "text"), "")
    except Exception as exc:
        print(f"[记忆压缩失败，保留完整 history]: {exc}")
        return history

    episode = _extract_tag(text, "episode")
    updated_memory = _extract_tag(text, "updated_memory")
    updated_user = _extract_tag(text, "updated_user")

    if episode:
        MEMORY.append_episode(episode)
    if updated_memory:
        MEMORY.write_memory(updated_memory)
    if updated_user:
        MEMORY.write_user(updated_user)

    print(f"[记忆已压缩]: old={len(old_messages)} recent={len(recent_messages)}")
    return recent_messages
