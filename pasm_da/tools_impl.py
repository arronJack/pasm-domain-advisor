"""真实工具实现（小U 当年缺的那一层，现在真正落地）。

对照 WorkBuddy / PASM 工具路由：
  - web_search  = 联网检索领域最新政策（默认离线安全，env 打开）
  - code_run    = 在子进程里跑 Python，生成定价表/算账等计算型交付物
  - file_write  = 把清单/表格写进文件，交给工作流或后台

设计原则（与客服/框架一致）：
  - 零强制第三方依赖；``requests`` 可用就快一点，不可用就 urllib 兜底。
  - 所有方法**永不抛异常**：失败返回 "" / False，让引擎优雅降级到模板 + 固化知识，
    保证「永远有专业回答，而不是报错」。
  - 默认 web_search 离线（``PASM_DA_LIVE_WEB=1`` 才真联网），避免 CI / 离线环境卡住；
    部署时打开即可让小U 真正「联网核验最新政策」。
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from .tools_contract import ToolSet


def _have_requests() -> bool:
    try:
        import requests  # noqa: F401
        return True
    except Exception:  # pragma: no cover
        return False


# ----------------------------------------------------------- web_search
_DDG_LITE = "https://html.duckduckgo.com/html/"


def web_search_impl(query: str, *, timeout: float = 8.0, limit: int = 5) -> str:
    """真实联网检索（DuckDuckGo HTML 版），返回若干条标题+摘要拼接的文本。

    离线 / 被墙 / 超时都返回 ""，由引擎退化为 profile.knowledge 兜底。
    生产环境若想更稳，可在部署层用同一签名替换成 Bing / SerpAPI / 自研检索。
    """
    try:
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            _DDG_LITE, data=data,
            headers={"User-Agent": "Mozilla/5.0 (compatible; pasm-da/0.1)"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", "replace")
        # 极简抽取：result__a（标题）与 result__snippet（摘要）。
        import re
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.S)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
        clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()  # noqa: E731
        out = []
        for i in range(min(limit, len(titles))):
            t = clean(titles[i])
            s = clean(snips[i]) if i < len(snips) else ""
            if t:
                out.append("%s：%s" % (t, s))
        return "\n".join(out)[:600]
    except Exception:  # 网络/解析失败一律降级
        return ""


# ----------------------------------------------------------- code_run
def code_run_impl(code: str, *, run_in: str = "python", timeout: float = 30.0) -> str:
    """在子进程里执行 Python 代码，返回 stdout（出错返回 stderr 片段）。

    用途：生成定价 Excel / 跑算账模型 / 任意可复现的计算型交付物。
    用 ``sys.executable`` 跑，保证与当前解释器同环境（含 openpyxl 等已装依赖）。
    """
    exe = sys.executable
    try:
        proc = subprocess.run(
            [exe, "-c", code], capture_output=True, text=True,
            timeout=timeout, cwd=os.getcwd(),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip()[:4000]
    except subprocess.TimeoutExpired:
        return "code_run 超时（%ss）" % int(timeout)
    except Exception as exc:  # pragma: no cover
        return "code_run 失败：%s" % exc


# ----------------------------------------------------------- file_write
def file_write_impl(path: str, content: str) -> bool:
    """把内容写到文件（自动建父目录），成功返回 True。"""
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return True
    except Exception:  # pragma: no cover
        return False


class RealToolSet(ToolSet):
    """真实工具集：覆盖默认空实现，但每个方法都内置降级。"""

    def __init__(self, *, enable_web: bool = False) -> None:
        self._enable_web = enable_web

    def web_search(self, query: str) -> str:
        if not self._enable_web:
            return ""  # 离线安全：交给 profile.knowledge 兜底
        return web_search_impl(query)

    def code_run(self, code: str, *, run_in: str = "python") -> str:
        return code_run_impl(code, run_in=run_in)

    def file_write(self, path: str, content: str) -> bool:
        return file_write_impl(path, content)


def build_default_tools(*, enable_web: Optional[bool] = None) -> ToolSet:
    """构造默认工具集。

    ``enable_web`` 不传时由环境变量 ``PASM_DA_LIVE_WEB=1`` 决定；
    便于「开发/CI 默认离线，部署时真正联网」。
    """
    if enable_web is None:
        enable_web = os.environ.get("PASM_DA_LIVE_WEB") == "1"
    return RealToolSet(enable_web=enable_web)


__all__ = [
    "RealToolSet", "build_default_tools",
    "web_search_impl", "code_run_impl", "file_write_impl",
]
