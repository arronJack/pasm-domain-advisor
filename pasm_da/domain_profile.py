"""泛例领域顾问 · 声明式规格（DomainProfile）。

为什么需要它
------------
「抖音宠物店开店」只是**一个领域**。真正可复用的是这套**规格**：
任何一个需要"结合现行规则 + 用户真实资源 + 多维度剖析 + 自检纠错"的顾问场景
（开店 / 资质办理 / 跨境合规 / 财税筹划 / 医美合规 / 留学申请 …），
只要 drop 一个 ``DomainProfile`` 实例进来，``DomainAdvisor`` 引擎就能直接产出
专业、不过时、带自检的清单 —— 不用改引擎一行代码。

这就是"泛例"：引擎固定，领域用声明式 profile 注入。
开店内容被沉淀成 ``profiles/douyin_pet_store.py`` 这个**示例实例**，证明它是可复制的，
而不是把开店写死在引擎里。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PremiseSignal:
    """从用户原话里抽取"你**已经**有什么"的信号（决定一切的前提）。

    示例：用户说"我已经有个体户营业执照"，就应直接推**个体店**而非个人店。
    不抽这个前提，任何模型都会掉进"小白先个人店试水"的默认套路里。
    """

    key: str                       # 内部键，如 "has_individual_business_license"
    label_zh: str                  # 人读标签，如 "已持有个体工商户营业执照"
    patterns: List[str] = field(default_factory=list)        # 出现即判定为真
    negate_patterns: List[str] = field(default_factory=list)  # 出现即判定为假
    default: bool = False          # 抽不到时的默认值


@dataclass
class PremiseConstraint:
    """前提一致性闸门规则（自检的核心）。

    当某条建议命中 ``forbid_reco_contains`` 里的词，而前提 ``if_premise`` 为真时，
    判定为**自相矛盾**并报警 —— 这正是把"已有执照却推荐个人店"这类硬伤挡下的机制。
    """

    if_premise: str                # 对应 PremiseSignal.key
    forbid_reco_contains: List[str] = field(default_factory=list)
    warn_zh: str = ""              # 触发时给用户的纠正话术


@dataclass
class DomainProfile:
    """一个领域的完整声明。引擎只认这个结构，不认具体业务词。"""

    id: str                        # 全局唯一，如 "douyin_pet_store"
    name_zh: str                   # "抖音电商 · 宠物店开店"
    domain: str                    # 领域大类，如 "ecommerce_opening"
    description: str = ""

    premise_signals: List[PremiseSignal] = field(default_factory=list)
    premise_constraints: List[PremiseConstraint] = field(default_factory=list)

    # 现行规则检索：每个 query 用于核验该领域**最新**政策（联网或资料库）。
    # 没有联网时，引擎退化为使用 ``knowledge`` 里固化的已核验条目。
    rule_queries: List[str] = field(default_factory=list)

    # 合规清单矩阵：维度 -> 该维度下的要点。多维剖析与交付清单都基于它。
    compliance_matrix: Dict[str, List[str]] = field(default_factory=dict)

    # 多维剖析维度（展示给用户看的剖析框架）。
    analysis_dimensions: List[str] = field(default_factory=list)

    # 风险维度。
    risk_dimensions: List[str] = field(default_factory=list)

    # 交付物：从 {"checklist", "pricing_spreadsheet", "compliance_doc"} 中选。
    deliverables: List[str] = field(default_factory=lambda: ["checklist"])

    # 已核验知识（固化的最新规则/要点）。联网缺失时的兜底，也作为闸门的事实基准。
    knowledge: List[Dict[str, object]] = field(default_factory=list)

    # 触发词：宿主（聊天壳/客服/MCP 客户端）用它判断"这轮对话是否落在本领域"。
    # 声明在 profile 里而不是硬编码在宿主——新增领域时宿主一行不用改（泛例铁律）。
    match_keywords: List[str] = field(default_factory=list)

    def premise_signal(self, key: str) -> "PremiseSignal":
        for s in self.premise_signals:
            if s.key == key:
                return s
        raise KeyError("profile %s 没有 premise_signal: %s" % (self.id, key))

    def as_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name_zh": self.name_zh,
            "domain": self.domain,
            "description": self.description,
            "premise_signals": [vars(s) for s in self.premise_signals],
            "premise_constraints": [vars(c) for c in self.premise_constraints],
            "rule_queries": self.rule_queries,
            "compliance_matrix": self.compliance_matrix,
            "analysis_dimensions": self.analysis_dimensions,
            "risk_dimensions": self.risk_dimensions,
            "deliverables": self.deliverables,
            "knowledge": self.knowledge,
        }


__all__ = ["DomainProfile", "PremiseSignal", "PremiseConstraint"]
