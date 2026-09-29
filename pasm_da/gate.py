"""自检闸门（反幻觉 / 前提一致性 / 事实接地）。

复用 pasm-customer-service 的 ``touches_surface`` 检索面技术，并扩展到"顾问场景"：
顾问的硬伤不是客服式的"答非所问"，而是**自相矛盾**（已有执照却让开个人店）
和**无依据断言**（凭训练默认套路瞎给）。这两类在闸门里被显式拦截。

与客服闸门同源的设计哲学：主判据**与分数/时间无关**（命中必须落在事实面上），
避免"资料放旧了就开始失忆"的固定阈值陷阱。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from .domain_profile import DomainProfile

#: 与 pasm-customer-service 同口径的分词：英文/数字词（≥2 字符）+ 中文 bigram。
_WORD_RE = re.compile(r"[A-Za-z0-9_]+|[一-鿿]+")

#: 引擎给建议打的前缀标签（【合规·X】/【剖析·X】/【风险·X】/【成本·已核验】等）。
#: 这些属于"信息陈列"，不参与"前提一致性"判错（否则会误伤正确科普）；
#: 只有"决策/执行/推荐"类（含 LLM 无前缀输出）才过前提一致性闸门。
_INFO_PREFIX_ROOTS = ("合规", "剖析", "风险", "成本")
_PREFIX_RE = re.compile(r"^【([^】]+)】")


def _reco_kind(reco: str) -> str:
    m = _PREFIX_RE.match(reco or "")
    return m.group(1) if m else ""


def _is_directive(reco: str) -> bool:
    label = _reco_kind(reco)
    if not label:
        return True  # 无前缀（LLM 原始输出）= 视为直接建议，必过闸门
    return not any(label.startswith(r) for r in _INFO_PREFIX_ROOTS)


def semantic_tokens(text: str) -> set:
    out: set = set()
    for seg in _WORD_RE.findall(text or ""):
        if seg[0].isascii():
            if len(seg) >= 2:
                out.add(seg.lower())
        elif len(seg) >= 2:
            for i in range(len(seg) - 1):
                out.add(seg[i:i + 2])
    return out


def touches_surface(query_tokens: set, surface: str) -> bool:
    """这条建议的关键词是否落在"事实面"（已核验规则/合规矩阵/前提）上。"""
    return bool(query_tokens & semantic_tokens(surface))


def extract_premises(text: str, profile: DomainProfile) -> Dict[str, bool]:
    """从用户原话抽取前提（规则命中，无需 LLM）。"""
    t = text or ""
    result: Dict[str, bool] = {}
    for s in profile.premise_signals:
        hit_pos = any(p in t for p in s.patterns)
        hit_neg = any(p in t for p in s.negate_patterns)
        if hit_neg:
            result[s.key] = False
        elif hit_pos:
            result[s.key] = True
        else:
            result[s.key] = s.default
    return result


def _build_fact_surface(profile: DomainProfile,
                        verified_rules: List[str]) -> str:
    """把所有"事实面"拼成一段文本：已核验规则 + 合规矩阵要点 + 前提标签。"""
    parts: List[str] = []
    parts += verified_rules
    for pts in profile.compliance_matrix.values():
        parts += pts
    for s in profile.premise_signals:
        parts.append(s.label_zh)
    return " ".join(parts)


@dataclass
class GateFlag:
    level: str            # "contradiction" | "ungrounded"
    reco_index: int
    message: str


@dataclass
class GateReport:
    flags: List[GateFlag] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.flags

    def contradictions(self) -> List[GateFlag]:
        return [f for f in self.flags if f.level == "contradiction"]

    def ungrounded(self) -> List[GateFlag]:
        return [f for f in self.flags if f.level == "ungrounded"]


def verify_advice(recos: List[str], premises: Dict[str, bool],
                  profile: DomainProfile,
                  verified_rules: List[str]) -> GateReport:
    """对每条建议做两道闸门。

    ① 前提一致性：若前提为真，且建议在**推荐**该动作（而非"警告/对比"它）
       → contradiction（硬伤，必须改）。
    ② 事实接地：建议关键词没落在任何事实面上 → ungrounded（无依据，需补来源）。
    """
    # 否定词：出现即视为"在劝退/对比"，不是真的推荐，不算自相矛盾。
    NEG = ("不要", "无需", "别", "而非", "避免", "不建议", "不应", "降级开")
    report = GateReport()
    surface = _build_fact_surface(profile, verified_rules)

    for i, reco in enumerate(recos):
        # ① 前提一致性（只在"直接建议"上查禁止词；信息陈列类不过此闸，避免误伤科普）
        if not _is_directive(reco):
            continue
        for c in profile.premise_constraints:
            if premises.get(c.if_premise):
                for bad in c.forbid_reco_contains:
                    if bad in reco and not any(n in reco for n in NEG):
                        report.flags.append(GateFlag(
                            "contradiction", i,
                            "前提 %s=true 却推荐「%s」：%s"
                            % (c.if_premise, bad, c.warn_zh or "自相矛盾")))
        # ② 事实接地（与分数/时间无关的检索面判据）
        if not touches_surface(semantic_tokens(reco), surface):
            report.flags.append(GateFlag(
                "ungrounded", i,
                "建议「%s…」未落到任何已核验规则/合规要点/前提上，疑似凭默认套路给出"
                % reco[:24]))
    return report


__all__ = [
    "semantic_tokens",
    "touches_surface",
    "extract_premises",
    "verify_advice",
    "GateReport",
    "GateFlag",
]
