"""pasm-domain-advisor —— 泛例领域顾问智能体（PASM 技能）。

一个**通用**顾问引擎：把任意领域写成 DomainProfile，就能产出结合现行规则、
用户真实前提、多维剖析与自检纠错的清单。抖音宠物店只是其中一个示例实例。

快速开始（纯引擎，无需框架）：

    from pasm_da import DomainAdvisorAgent
    agent = DomainAdvisorAgent("xiaou", profile_id="douyin_pet_store")
    print(agent.render("我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店"))

接框架 / MCP / Web（框架可用时）：

    from pasm_da import build_advisor_agent
    a = build_advisor_agent("xiaou", profile_id="douyin_pet_store", llm={...})
    print(a.answer("..."))
"""
from __future__ import annotations

from .agent import DomainAdvisorAgent, build_advisor_agent
from .domain_profile import DomainProfile, PremiseConstraint, PremiseSignal
from .engine import AdvisoryReport, DomainAdvisor, VerifiedRule
from . import profiles as profiles

__version__ = "0.1.0"

__all__ = [
    "DomainAdvisorAgent",
    "build_advisor_agent",
    "DomainAdvisor",
    "AdvisoryReport",
    "VerifiedRule",
    "DomainProfile",
    "PremiseSignal",
    "PremiseConstraint",
    "profiles",
    "__version__",
]
