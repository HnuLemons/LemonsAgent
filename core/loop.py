from .compactor import compact_history
from .config import MODEL, SOUL_PATH, client
from .context import ContextManager
from .memory import MEMORY
from .skill import SKILL_LOADER
from ..tools.registry import TOOLS, execute_tool

# 人设文件路径来自 config（由 .env 的 AGENT_SOUL_FILE 决定，默认 templates/SOUL.md）


def _load_soul() -> str:
    """读取人设文件；缺失/读取失败时回退到默认人设，保证 Agent 可用。"""
    try:
        return SOUL_PATH.read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(f"[人设文件读取失败，使用默认人设]: {exc}")
        return "你是一个乐于助人的 AI 助手，使用中文回复。"


def build_system_prompt() -> str:
    memory = MEMORY.read_memory()
    user_profile = MEMORY.read_user()
    today_episode = MEMORY.read_today_episode()

    return f"""
{_load_soul()}

遇到不熟悉的专题时，请先调用 load_skill 工具加载对应的知识，再给出回答。

【长期记忆 MEMORY.md】
{memory}

【用户画像 USER.md】
{user_profile}

【今日情景记忆】
{today_episode or "(今天还没有压缩出的情景记忆)"}

当前可用技能：
{SKILL_LOADER.get_descriptions()}"""


def agent_turn(context: ContextManager) -> None:
    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=1000,
            system=build_system_prompt(),
            tools=TOOLS,
            messages=context.get_messages(),
        ) as stream:
            streamed = False
            for text_delta in stream.text_stream:
                if not streamed:
                    print("[Agent]: ", end="", flush=True)
                    streamed = True
                print(text_delta, end="", flush=True)
            message = stream.get_final_message()
        if streamed:
            print("\n")  # 流式输出结束后换行收尾

        context.add_assistant_message(message.content)
        MEMORY.append_history({"role": "assistant", "content": message.content})

        if message.stop_reason != "tool_use":
            if not streamed:
                # 模型未返回任何文本块（流式过程中没有打印任何内容）
                print("[Agent]: (模型未返回文本内容)\n")
            # 复杂压缩（LLM 摘要）：达到阈值时压缩旧消息并写回上下文
            context.replace(compact_history(context.get_messages()))
            return

        tool_results = []
        for block in message.content:
            if block.type != "tool_use":
                continue
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": execute_tool(block),
            })

        context.add_tool_results(tool_results)
        MEMORY.append_history({"role": "user", "content": tool_results})
