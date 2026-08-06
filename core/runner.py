from .context import ContextManager
from .exceptions import SessionNotFoundError
from .loop import agent_turn
from .memory import MEMORY
from .session import SessionManager
from ..tools.trace import TRACER

_HELP = """可用命令：
  /new          创建新会话
  /list         列出所有会话
  /switch <id>  切换到指定会话（支持 id 前缀，如 /switch 20260806）
  /trace [n]    查看最近 n 条工具调用记录（默认 10 条）
  /help         显示本帮助
  /exit         退出（或直接 Ctrl+D / Ctrl+C）"""


class AgentRunner:
    def __init__(self):
        self.session_manager = SessionManager()
        self.session = self.session_manager.create()
        # ContextManager 直接包装 session.history（同一列表引用），
        # 因此对上下文的所有修改都会反映到会话，随 save 一起持久化
        self.context = ContextManager(self.session.history)

    # ---- 斜杠命令 ----

    def _cmd_new(self):
        self.session = self.session_manager.create()
        self.context = ContextManager(self.session.history)
        print(f"[已创建新会话]: {self.session.id}")

    def _cmd_list(self):
        sessions = self.session_manager.list()
        if not sessions:
            print("[暂无历史会话]")
            return
        print("所有会话（* 为当前会话）：")
        for s in sessions:
            mark = "*" if s.id == self.session.id else " "
            print(f" {mark} {s.id}  ({len(s.history)} 条消息)  {s.preview()}")
        # 当前会话可能还没落盘（还没说过话），单独提示
        if all(s.id != self.session.id for s in sessions):
            print(f" * {self.session.id}  (0 条消息)  (空会话，尚未保存)")

    def _cmd_switch(self, arg: str):
        if not arg:
            print("[用法]: /switch <会话id>")
            return
        try:
            self.session = self.session_manager.load(arg)
        except SessionNotFoundError as exc:
            print(f"[切换失败]: {exc}")
            return
        self.context = ContextManager(self.session.history)
        print(f"[已切换到会话]: {self.session.id}  ({len(self.session.history)} 条消息)  {self.session.preview()}")

    def _cmd_trace(self, arg: str):
        try:
            n = int(arg) if arg else 10
        except ValueError:
            print("[用法]: /trace [条数]")
            return
        entries = TRACER.recent(n)
        if not entries:
            print("[暂无工具调用记录]")
            return
        print(f"最近 {len(entries)} 条工具调用：")
        for entry in entries:
            print(" " + TRACER.format_entry(entry))

    def _handle_command(self, user_input: str) -> bool:
        """处理斜杠命令，返回 True 表示已处理。"""
        cmd, _, arg = user_input.partition(" ")
        cmd, arg = cmd.lower(), arg.strip()

        if cmd == "/new":
            self._cmd_new()
        elif cmd == "/list":
            self._cmd_list()
        elif cmd == "/switch":
            self._cmd_switch(arg)
        elif cmd == "/trace":
            self._cmd_trace(arg)
        elif cmd == "/help":
            print(_HELP)
        elif cmd == "/exit":
            print("[已退出]")
            return True
        else:
            print(f"[未知命令]: {cmd}（输入 /help 查看可用命令）")
        return cmd != "/exit"  # /exit 时返回 False 让上层退出

    # ---- 主循环 ----

    def run(self):
        print(f"[当前会话]: {self.session.id}（输入 /help 查看会话命令）")
        while True:
            # ── Step 1：接收用户输入（空输入跳过，Ctrl+D/Ctrl+C 优雅退出）
            try:
                user_input = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[已退出]")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    break  # /exit
                continue

            # 用户输入写入上下文后，进入 loop.py 的 Step 2-4 循环
            turn_start = len(self.context)  # 记录本轮起点，供失败时回滚
            user_message = {"role": "user", "content": user_input}
            self.context.add_user_message(user_input)
            MEMORY.append_history(user_message)

            try:
                agent_turn(self.context)
            except KeyboardInterrupt:
                print("\n[本轮已中断，已回滚未完成的记录]")
                self.context.rollback(turn_start)
                continue
            except Exception as exc:
                print(f"[本轮对话出错，已回滚未完成的记录]: {exc}")
                self.context.rollback(turn_start)
                continue

            # LLM 压缩可能整体替换消息列表，同步回会话后持久化
            self.session.history = self.context.messages
            try:
                self.session_manager.save(self.session)
            except Exception as exc:
                # 保存失败（磁盘满/权限等）只告警，对话本身已成功，不中断 REPL
                print(f"[会话保存失败，本轮记录未持久化]: {exc}")
