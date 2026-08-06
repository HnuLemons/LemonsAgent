"""场景 2.3：工具注册机制（每个工具包含名称、描述、参数 Schema，
LLM 基于 Schema 自主决策调用——Schema 的完整性与可分发性是决策的前提）。"""
import unittest
from types import SimpleNamespace

from lemons_agents.tools import TOOLS, execute_tool
from lemons_agents.tools.base import BaseTool
from lemons_agents.tools.registry import REGISTERED_TOOLS, _DISPATCH


class TestToolContracts(unittest.TestCase):
    def test_all_tools_are_basetool_instances(self):
        for tool in REGISTERED_TOOLS:
            self.assertIsInstance(tool, BaseTool)

    def test_every_tool_has_complete_metadata(self):
        """每个工具必须有非空的名称、描述、参数 Schema。"""
        for tool in REGISTERED_TOOLS:
            with self.subTest(tool=tool.name):
                self.assertTrue(tool.name, "工具名不能为空")
                # description 是模型选择工具的唯一依据，必须是有意义的长度
                self.assertGreaterEqual(len(tool.description), 10,
                                        "description 过短，模型无法据此做出调用决策")
                self.assertEqual(tool.input_schema.get("type"), "object")
                self.assertIn("properties", tool.input_schema)
                self.assertIn("required", tool.input_schema)

    def test_required_params_exist_in_properties(self):
        """required 中的参数必须在 properties 中有定义，否则 Schema 自相矛盾。"""
        for tool in REGISTERED_TOOLS:
            with self.subTest(tool=tool.name):
                props = set(tool.input_schema["properties"].keys())
                for req in tool.input_schema["required"]:
                    self.assertIn(req, props)

    def test_tools_list_matches_registered(self):
        """发给 LLM 的 TOOLS 列表必须由注册表生成且一一对应。"""
        self.assertEqual(len(TOOLS), len(REGISTERED_TOOLS))
        self.assertEqual(
            {t["name"] for t in TOOLS},
            {t.name for t in REGISTERED_TOOLS},
        )
        for schema in TOOLS:
            self.assertEqual(set(schema.keys()), {"name", "description", "input_schema"})

    def test_dispatch_covers_all_tools(self):
        """分发表必须覆盖所有注册工具——LLM 能看到的工具都必须可执行。"""
        self.assertEqual(set(_DISPATCH.keys()), {t.name for t in REGISTERED_TOOLS})

    def test_unknown_tool_returns_error(self):
        result = execute_tool(SimpleNamespace(name="no_such_tool", input={}))
        self.assertIn("Unknown tool", result)

    def test_basetool_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseTool()


if __name__ == "__main__":
    unittest.main()
