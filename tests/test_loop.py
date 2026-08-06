"""场景 2.1：Loop 基本步骤（输入→模型判断→工具→继续/返回）。"""
import unittest
from unittest.mock import patch

from lemons_agents.core import ContextManager
from lemons_agents.core import loop as loop_module
from lemons_agents.core.loop import agent_turn
from .helpers import (
    FakeClient, MemoryStub, fake_message, text_block, tool_use_block,
)


class TestAgentTurn(unittest.TestCase):
    def _run(self, responses):
        ctx = ContextManager()
        ctx.add_user_message("测试输入")
        with patch.object(loop_module, "client", FakeClient(responses)), \
             patch.object(loop_module, "MEMORY", MemoryStub()):
            agent_turn(ctx)
        return ctx

    def test_direct_reply_end_turn(self):
        """模型直接回复（end_turn）：一轮结束，user+assistant 两条消息。"""
        ctx = self._run([fake_message([text_block("直接回复")], "end_turn")])
        self.assertEqual(len(ctx.messages), 2)
        self.assertEqual(ctx.messages[-1]["role"], "assistant")

    def test_tool_use_then_reply(self):
        """模型先调工具（tool_use）再给最终回复：loop 执行两轮模型调用，
        且上下文中有完整的 tool_use/tool_result 配对。"""
        responses = [
            fake_message([tool_use_block("calculator", {"expression": "1+2"})], "tool_use"),
            fake_message([text_block("结果是3")], "end_turn"),
        ]
        ctx = self._run(responses)
        # user → assistant(tool_use) → user(tool_result) → assistant(text)
        self.assertEqual(len(ctx.messages), 4)
        tool_result_msg = ctx.messages[2]
        self.assertEqual(tool_result_msg["role"], "user")
        self.assertEqual(tool_result_msg["content"][0]["type"], "tool_result")
        # calculator 真实执行了：1+2 = 3
        self.assertIn("1+2 = 3", tool_result_msg["content"][0]["content"])

    def test_tool_pair_integrity(self):
        """工具调用后，tool_result 的 tool_use_id 必须与 tool_use 的 id 一致（API 配对约束）。"""
        responses = [
            fake_message([tool_use_block("calculator", {"expression": "2*3"}, "abc123")], "tool_use"),
            fake_message([text_block("ok")], "end_turn"),
        ]
        ctx = self._run(responses)
        tool_use = ctx.messages[1]["content"][0]
        tool_result = ctx.messages[2]["content"][0]
        self.assertEqual(tool_result["tool_use_id"], tool_use.id)


if __name__ == "__main__":
    unittest.main()
