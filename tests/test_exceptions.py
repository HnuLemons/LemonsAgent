"""场景 2.6：基本异常处理（配置校验、工具兜底、降级策略）。"""
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lemons_agents.core import config as config_module
from lemons_agents.core.exceptions import ConfigError
from lemons_agents.core.memory import MemoryStore
from lemons_agents.core.skill import SkillLoader
from lemons_agents.tools import execute_tool
from lemons_agents.tools.builtin import calculate


class TestConfigErrors(unittest.TestCase):
    def test_missing_env_var_raises_config_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ConfigError):
                config_module._require_env("ANTHROPIC_API_KEY")

    def test_placeholder_key_raises_config_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "your_api_key_here"}):
            with self.assertRaises(ConfigError):
                config_module._require_env("ANTHROPIC_API_KEY")

    def test_missing_env_file_raises_config_error(self, ):
        with patch.object(config_module, "ENV_PATH", Path("/nonexistent/.env")):
            with self.assertRaises(ConfigError) as cm:
                config_module.create_client()
            self.assertIn("配置文件不存在", str(cm.exception))


class TestToolFallbacks(unittest.TestCase):
    def test_tool_internal_exception_caught(self):
        """工具内部异常（缺入参）被 execute_tool 兜底为错误字符串，不抛出。"""
        result = execute_tool(SimpleNamespace(name="run_command", input={}))
        self.assertIn("执行失败", result)

    def test_unknown_tool(self):
        result = execute_tool(SimpleNamespace(name="ghost", input={}))
        self.assertIn("Unknown tool", result)

    def test_calculator_injection_rejected(self):
        self.assertTrue(calculate('__import__("os").system("ls")').startswith("Error"))

    def test_run_command_timeout(self):
        from lemons_agents.tools.builtin import run_shell_command
        result = run_shell_command("sleep 5", timeout=1)
        self.assertIn("超时", result)


class TestGracefulDegradation(unittest.TestCase):
    def test_memory_degrades_on_unwritable_path(self):
        """记忆系统：文件系统不可用时降级（读返回空、写跳过），不崩溃。"""
        tmp = Path(tempfile.mkdtemp())
        try:
            blocker = tmp / "blocker"
            blocker.write_text("x")  # 以文件占位，mkdir 必然失败
            ms = MemoryStore(blocker / "memory", blocker / "templates")
            ms.append_history({"role": "user", "content": "t"})  # 不应抛出
            self.assertEqual(ms.read_memory(), "")
            self.assertEqual(ms.read_today_episode(), "")
            ms.write_memory("x")  # 不应抛出
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skill_loader_skips_corrupt_file(self):
        """技能加载：单个损坏文件跳过，不影响其他技能。"""
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "good").mkdir()
            (tmp / "good" / "SKILL.md").write_text(
                "---\nname: good\ndescription: 正常\n---\n内容", encoding="utf-8")
            (tmp / "bad").mkdir()
            (tmp / "bad" / "SKILL.md").write_bytes(b"\xff\xfe invalid \x80\x81")
            loader = SkillLoader(tmp)
            self.assertEqual(list(loader.skills.keys()), ["good"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_soul_fallback(self):
        """人设文件缺失时 build_system_prompt 回退默认人设，不崩溃。"""
        from lemons_agents.core import loop as loop_module
        with patch.object(loop_module, "SOUL_PATH", Path("/nonexistent/SOUL.md")):
            prompt = loop_module.build_system_prompt()
        self.assertIn("乐于助人的 AI 助手", prompt)


if __name__ == "__main__":
    unittest.main()
