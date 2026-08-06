from .config import CONTEXT_MAX_MESSAGES, MAX_TURNS, TOOL_RESULT_MAX_CHARS


def _is_user_text(msg: dict) -> bool:
    """是否为用户文本消息（一轮对话的起点）。tool_result 也是 role=user，需区分。"""
    return msg.get("role") == "user" and isinstance(msg.get("content"), str)


def _truncate_tool_results(messages: list[dict], max_chars: int) -> list[dict]:
    """就地截断超长工具结果：保留头尾各一半，中间标注省略字符数。"""
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            text = block.get("content")
            if isinstance(text, str) and len(text) > max_chars:
                half = max_chars // 2
                omitted = len(text) - max_chars
                block["content"] = (
                    text[:half]
                    + f"\n...[中间省略 {omitted} 字符]...\n"
                    + text[-half:]
                )
    return messages


class ContextManager:
    """上下文管理器：消息的写入、读取、轮次统计与基础压缩。

    messages 列表即"当前上下文"，由 Session 持有并持久化，
    因此持续对话 / 重启恢复后都能记住之前的状态。
    """

    def __init__(
        self,
        messages: list[dict] | None = None,
        max_turns: int = MAX_TURNS,
        max_messages: int = CONTEXT_MAX_MESSAGES,
        tool_result_max_chars: int = TOOL_RESULT_MAX_CHARS,
    ):
        self.messages: list[dict] = messages if messages is not None else []
        self.max_turns = max_turns
        self.max_messages = max_messages
        self.tool_result_max_chars = tool_result_max_chars

    # ---- 写入 ----

    def add_user_message(self, text: str):
        """写入一条用户输入（新一轮对话的开始）。"""
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, content):
        """写入一条 assistant 消息（text 块 + tool_use 块都保留）。"""
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, tool_results: list[dict]):
        """写入工具执行结果（user 角色的 tool_result 块列表，写入前截断超长项）。"""
        message = {"role": "user", "content": tool_results}
        _truncate_tool_results([message], self.tool_result_max_chars)
        self.messages.append(message)

    # ---- 状态 ----

    @property
    def turn_count(self) -> int:
        """对话轮次 = 用户文本消息的条数。"""
        return sum(1 for m in self.messages if _is_user_text(m))

    def is_over_limit(self) -> bool:
        """是否超出限制（轮次或消息数）。"""
        return self.turn_count > self.max_turns or len(self.messages) > self.max_messages

    # ---- 读取 ----

    def get_messages(self) -> list[dict]:
        """返回发给模型的上下文（先做一次基础压缩）。"""
        self.apply_basic_compression()
        return self.messages

    # ---- 基础压缩 ----

    def apply_basic_compression(self):
        """基础压缩：截断超长工具结果 + 超限则从头部滑动丢弃。

        丢弃时对齐配对边界：循环丢弃直到首条消息是用户文本消息，
        保证不会出现"孤立的 tool_result"或"半截 tool_use"——
        否则下一轮 API 调用会因配对不完整报 400。
        """
        _truncate_tool_results(self.messages, self.tool_result_max_chars)

        dropped = 0
        while self.is_over_limit() and self.messages:
            self.messages.pop(0)
            dropped += 1
            # 对齐边界：首条必须是用户文本消息，否则继续丢
            while self.messages and not _is_user_text(self.messages[0]):
                self.messages.pop(0)
                dropped += 1

        if dropped:
            print(f"[上下文基础压缩]: 丢弃最旧 {dropped} 条消息，"
                  f"剩余 {len(self.messages)} 条 / {self.turn_count} 轮")

    # ---- 替换与回滚 ----

    def replace(self, messages: list[dict]):
        """整体替换上下文（供 compactor.py 的 LLM 压缩写回结果）。"""
        self.messages = messages

    def rollback(self, mark: int):
        """回滚到指定位置（agent_turn 中途失败时丢弃本轮未完成的消息）。"""
        del self.messages[mark:]

    def __len__(self) -> int:
        return len(self.messages)
