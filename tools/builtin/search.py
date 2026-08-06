import json
import os
import urllib.request
import urllib.error

TAVILY_API_URL = "https://api.tavily.com/search"
_TIMEOUT = 15  # 秒


class TavilyConfigError(Exception):
    """Tavily 未配置或配置无效（调用方应转换为 Error 字符串）。"""


def tavily_request(payload: dict) -> dict:
    """发送一次 Tavily /search 请求，返回解析后的 JSON。

    失败时抛出异常（TavilyConfigError / PermissionError / 其他网络异常），
    由调用方决定如何转换为对用户友好的错误信息。
    payload 中无需包含 api_key，本函数自动注入。
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key or api_key == "your_tavily_api_key_here":
        raise TavilyConfigError(
            "未配置 TAVILY_API_KEY。请到 https://app.tavily.com 注册获取 Key，"
            "并填入 lemons_agents/.env 的 TAVILY_API_KEY 后重试。"
        )

    body = json.dumps({"api_key": api_key, **payload}).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise PermissionError("Tavily API Key 无效或无权限，请检查 .env 中的 TAVILY_API_KEY。") from e
        raise RuntimeError(f"Tavily 请求失败（HTTP {e.code}）") from e


def web_search(query: str, max_results: int = 5) -> str:
    """用 Tavily 执行搜索，返回格式化的纯文本结果。"""
    query = (query or "").strip()
    if not query:
        return "Error: 搜索关键词为空"

    try:
        data = tavily_request({
            "query": query,
            "max_results": max(1, min(int(max_results), 10)),
        })
    except Exception as e:
        return f"Error: {e}"

    results = data.get("results", [])
    if not results:
        return f"未找到与「{query}」相关的结果。"

    lines = [f"搜索关键词: {query}（共 {len(results)} 条）"]
    for i, item in enumerate(results, 1):
        title = item.get("title", "(无标题)")
        url = item.get("url", "")
        snippet = item.get("content", "").strip()
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return "\n".join(lines)
