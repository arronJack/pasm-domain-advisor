"""PASM 接入层。

提供两层：
  1. ``DomainAdvisorAgent`` —— **纯引擎包装**，不依赖 pasm-framework，永远可用
     （这是技能的可移植核心，也是本会话冒烟测试用的对象）。
  2. ``PasmDomainAdvisorAgent`` —— 框架存在时**自动可用**，继承 ``BaseApplication``，
     接上资料库 / 持久化 / MCP / Web（与 pasm-customer-service 同一套接入面）。

设计原则（与客服产品一致）：框架不替你选模型、不替你接 LLM；
``llm`` 是普通配置字典，``tools`` 是 web_search/code_run/file_io 的注入。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .domain_profile import DomainProfile
from .engine import AdvisoryReport, DomainAdvisor
from .tools_contract import ToolSet
from .tools_impl import build_default_tools
from . import profiles as P

try:                                                    # pragma: no cover
    from pasm_framework import BaseApplication
    _HAS_FRAMEWORK = True
except Exception:                                        # pragma: no cover
    BaseApplication = object                             # type: ignore
    _HAS_FRAMEWORK = False


class DomainAdvisorAgent:
    """纯引擎包装（无框架依赖，可独立 import / 测试）。"""

    def __init__(self, agent_id: str, *, profile_id: Optional[str] = None,
                 profile: Optional[DomainProfile] = None,
                 llm: Optional[Dict[str, Any]] = None,
                 tools: Optional[Any] = None,
                 out_dir: Optional[str] = None) -> None:
        self.agent_id = agent_id
        self.profile = profile or (P.get(profile_id) if profile_id else None)
        if self.profile is None:
            raise ValueError("必须提供 profile（profile_id 或 profile 对象）")
        # 默认注入真实工具（离线安全：web_search 需 env 打开）；部署时传 tools 可覆盖。
        if tools is None:
            tools = build_default_tools()
        self.engine = DomainAdvisor(llm=llm, tools=tools, profile=self.profile)
        self.out_dir = out_dir

    def advise(self, text: str) -> AdvisoryReport:
        return self.engine.advise(text, self.profile, out_dir=self.out_dir)

    def render(self, text: str) -> str:
        return self.advise(text).markdown

    def snapshot_local(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "profile_id": self.profile.id,
            "profile_name": self.profile.name_zh,
            "framework_available": _HAS_FRAMEWORK,
        }


if _HAS_FRAMEWORK:                                       # pragma: no cover
    class PasmDomainAdvisorAgent(BaseApplication):
        """框架接入版：资料库 + 持久化 + MCP/Web。

        与 CustomerServiceAgent 同源的构造风格；LLM 与工具通过 engine 注入。
        """

        def __init__(self, agent_id: str, *, profile_id: Optional[str] = None,
                     profile: Optional[DomainProfile] = None,
                     llm: Optional[Dict[str, Any]] = None,
                     tools: Optional[Dict[str, Any]] = None,
                     serve_port: int = 8080, enable_gateway: bool = False,
                     persist_dir: Optional[str] = None) -> None:
            self._serve_port = serve_port
            self.profile = profile or (P.get(profile_id) if profile_id else None)
            if self.profile is None:
                raise ValueError("必须提供 profile")
            self.engine = DomainAdvisor(llm=llm, tools=tools, profile=self.profile)
            cfg = {
                "safety": {"enabled": True, "config": {"mode": "warn"}},
                "sessions": {"enabled": True, "config": {"max_history": 20}},
                "knowledge_base": {"enabled": True, "config": {}},
                "warmth": {"enabled": True, "config": {}},
                "observability": {"enabled": True, "config": {}},
                "llm_responder": {"enabled": bool(llm), "config": llm or {}},
                "web_gateway": {"enabled": bool(enable_gateway),
                                "config": {"port": serve_port, "allowed_origins": "*"}},
            }
            p = {"name": "小U·参谋", "role": "领域顾问", "temper": 0.6, "energy": 0.5, "play": 0.3}
            super().__init__(agent_id, p, persist_dir=persist_dir, backend_config=cfg)
            # 把 profile 的已核验知识灌进资料库（带 source，作为闸门事实基准）。
            if not self.state.notes.get("da_seeded"):
                try:
                    self.ingest([
                        {"title": k.get("title", ""), "content": k.get("content", ""),
                         "source": "profile:%s" % self.profile.id, "tags": list(self.profile.compliance_matrix.keys())}
                        for k in self.profile.knowledge
                    ])
                    self.state.notes["da_seeded"] = len(self.profile.knowledge)
                    self.save()
                except Exception:
                    self.state.notes["da_seeded"] = "skipped(no knowledge_base)"

        def action_pool(self) -> list:
            return ["advise"]

        def answer(self, text: str, session_id: str = "default",
                   user_id: Optional[str] = None) -> str:
            report = self.engine.advise(text, self.profile)
            return report.markdown

        def snapshot(self) -> Dict[str, Any]:
            return {
                "agent_id": self.agent_id,
                "profile_id": self.profile.id,
                "tier": self.tier,
                "interactions": self.state.total_interactions,
                "seeded": self.state.notes.get("da_seeded"),
            }


def build_advisor_agent(agent_id: str, *, profile_id: Optional[str] = None,
                        profile: Optional[DomainProfile] = None,
                        llm: Optional[Dict[str, Any]] = None,
                        tools: Optional[Dict[str, Any]] = None,
                        out_dir: Optional[str] = None):
    """统一入口：框架可用返回 PasmDomainAdvisorAgent，否则返回纯引擎包装。"""
    if _HAS_FRAMEWORK:                                   # pragma: no cover
        return PasmDomainAdvisorAgent(agent_id, profile_id=profile_id, profile=profile,
                                     llm=llm, tools=tools)
    return DomainAdvisorAgent(agent_id, profile_id=profile_id, profile=profile,
                              llm=llm, tools=tools, out_dir=out_dir)


__all__ = [
    "DomainAdvisorAgent",
    "PasmDomainAdvisorAgent" if _HAS_FRAMEWORK else "DomainAdvisorAgent",
    "build_advisor_agent",
]
