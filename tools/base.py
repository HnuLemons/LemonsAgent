from abc import ABC, abstractmethod


class BaseTool(ABC):
    """工具抽象基类。子类需定义 name/description/input_schema 并实现 run()。"""

    name: str = ""
    description: str = ""
    input_schema: dict = {}

    @abstractmethod
    def run(self, tool_input: dict) -> str:
        """执行工具，返回字符串结果；失败返回 "Error: " 前缀字符串，不抛异常。"""
        ...

    def to_schema(self) -> dict:
        """转换为 Anthropic tool_use 接口所需的工具描述。"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def __init_subclass__(cls, **kwargs):
        """防御性子类校验：漏写元信息在定义阶段就暴露（开发期即时反馈）。"""
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("run") is None:
            return  # 仍是抽象中间层，不检查
        for attr in ("name", "description", "input_schema"):
            if not getattr(cls, attr, None):
                raise TypeError(f"工具类 {cls.__name__} 必须定义类属性 {attr}")
