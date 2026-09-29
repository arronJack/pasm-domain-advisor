"""工具契约（Tool Contract）。

这是小U 缺的那一层：让顾问引擎**能调用工具**，而不只是"生成文字"。
引擎只依赖下面这三个抽象方法；具体实现交给部署层（Web / 本地 / MCP / PASM 工具路由）。

对照 WorkBuddy：联网检索 = web_search，算账/读写 = code_run + file_io。
对照 PASM：这些对应认知层的工具路由 / MCP——引擎不关心底层怎么落地。
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class ToolSet:
    """引擎默认使用的空工具集（不接任何工具时，走纯模板分支）。"""

    def web_search(self, query: str) -> str:       # pragma: no cover - 默认无联网
        return ""

    def code_run(self, code: str, *, run_in: str = "python") -> str:
        return ""

    def file_write(self, path: str, content: str) -> bool:
        return False


def resolve_tools(tools: Optional[Dict[str, Any]]) -> ToolSet:
    """把部署层给的 dict（方法名 -> callable）包成 ToolSet。

    部署层只需传 {"web_search": fn, "code_run": fn, "file_write": fn}，
    引擎统一按接口调用，缺哪个就退化为空实现。
    """
    ts = ToolSet()
    if not tools:
        return ts
    for name in ("web_search", "code_run", "file_write"):
        fn = tools.get(name)
        if callable(fn):
            setattr(ts, name, fn)
    return ts


__all__ = ["ToolSet", "resolve_tools"]
