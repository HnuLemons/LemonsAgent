from .search import tavily_request


def get_weather(city: str) -> str:
    """查询城市天气，返回格式化的纯文本；失败返回错误说明而不是抛出。"""
    city = (city or "").strip()
    if not city:
        return "Error: 城市名为空"

    try:
        data = tavily_request({
            "query": f"{city}今天天气 气温 湿度 风力（请用中文回答）",
            "max_results": 3,
            "include_answer": True,
        })
    except Exception as e:
        return f"Error: {e}"

    answer = (data.get("answer") or "").strip()
    results = data.get("results", [])

    if not answer and not results:
        return f"未查询到「{city}」的天气信息，请检查城市名是否正确。"

    lines = [f"{city}天气查询结果"]
    if answer:
        lines.append(answer)
    if results:
        lines.append("参考来源：")
        for i, item in enumerate(results, 1):
            lines.append(f"{i}. {item.get('title', '(无标题)')}  {item.get('url', '')}")
    return "\n".join(lines)
