"""可选的 LLM 客户端（OpenAI 兼容 / DeepSeek）。

纯标准库实现（urllib），不强制依赖 ``requests``。``pasm-framework`` 的
``llm_responder`` 插件也能用同一个 ``llm`` 字典；本模块是**引擎自带的最小实现**，
保证即使不装框架也能跑 LLM 分支。

设计原则（与 PASM 一致）：框架不替你选模型，``llm`` 是普通配置字典，接哪家由你定。
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List, Optional


class LLMClient:
    """极简 OpenAI 兼容聊天客户端。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.base_url = str(cfg.get("base_url") or "https://api.deepseek.com/v1").rstrip("/")
        self.model = str(cfg.get("model") or "deepseek-chat")
        self.api_key = str(cfg.get("api_key") or "")
        self.timeout = float(cfg.get("timeout") or 60.0)

    def chat(self, messages: List[Dict[str, str]], *,
             temperature: float = 0.3, max_tokens: int = 1500) -> str:
        if not self.api_key:
            raise RuntimeError("LLM 未配置 api_key")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer %s" % self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # 网络/鉴权失败都回落到上层模板分支
            raise RuntimeError("LLM 调用失败: %s" % exc)
        return data["choices"][0]["message"]["content"].strip()


def build_llm(config: Optional[Dict[str, Any]]) -> Optional[LLMClient]:
    if not config:
        return None
    return LLMClient(config)


__all__ = ["LLMClient", "build_llm"]
