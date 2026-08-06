"""场景 2.2：三个工具调用是否正常（calculator / search / weather）。"""
import unittest
from unittest.mock import patch

from lemons_agents.tools.builtin import calculate, get_weather, web_search
from lemons_agents.tools.builtin.search import TavilyConfigError


class TestCalculator(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(calculate("(3+5)*2"), "(3+5)*2 = 16")
        self.assertEqual(calculate("2**10"), "2**10 = 1024")
        self.assertEqual(calculate("10/4"), "10/4 = 2.5")

    def test_division_by_zero_returns_error(self):
        self.assertTrue(calculate("10/0").startswith("Error"))

    def test_injection_rejected(self):
        result = calculate('__import__("os")')
        self.assertTrue(result.startswith("Error"))


_FAKE_TAVILY = {
    "answer": "北京今天晴，35°C",
    "results": [
        {"title": "示例结果", "url": "https://example.com", "content": "摘要内容"},
    ],
}


class TestWebSearch(unittest.TestCase):
    def test_success_format(self):
        with patch("lemons_agents.tools.builtin.search.tavily_request", return_value=_FAKE_TAVILY):
            result = web_search("AI 新闻", max_results=1)
        self.assertIn("搜索关键词: AI 新闻", result)
        self.assertIn("示例结果", result)
        self.assertIn("https://example.com", result)

    def test_api_failure_returns_error(self):
        with patch("lemons_agents.tools.builtin.search.tavily_request",
                   side_effect=TavilyConfigError("未配置")):
            result = web_search("test")
        self.assertTrue(result.startswith("Error"))

    def test_empty_query(self):
        self.assertTrue(web_search("  ").startswith("Error"))


class TestWeather(unittest.TestCase):
    def test_success_format(self):
        with patch("lemons_agents.tools.builtin.weather.tavily_request", return_value=_FAKE_TAVILY):
            result = get_weather("北京")
        self.assertIn("北京天气查询结果", result)
        self.assertIn("北京今天晴，35°C", result)
        self.assertIn("参考来源", result)

    def test_api_failure_returns_error(self):
        with patch("lemons_agents.tools.builtin.weather.tavily_request",
                   side_effect=RuntimeError("网络错误")):
            result = get_weather("北京")
        self.assertTrue(result.startswith("Error"))

    def test_empty_city(self):
        self.assertTrue(get_weather("").startswith("Error"))


if __name__ == "__main__":
    unittest.main()
