"""泛例顾问 · 提示词模板（参数化，按 DomainProfile 注入）。

这些模板是"专业度"的来源：它们强制 LLM 做**前提感知 + 现行规则核验 + 多维剖析 +
自检纠错**，而不是张嘴就按训练里的默认套路答。
没有 LLM 时引擎走模板分支，同样遵循同一套纪律（见 engine.py）。
"""
from __future__ import annotations

from typing import Dict, List

from .domain_profile import DomainProfile


def _fmt_premises(premises: Dict[str, bool]) -> str:
    if not premises:
        return "（未抽取到明确前提）"
    lines = ["- %s = %s" % (k, v) for k, v in premises.items()]
    return "\n".join(lines)


def _fmt_knowledge(profile: DomainProfile) -> str:
    if not profile.knowledge:
        return "（无固化的已核验知识，请依赖下面 rule_queries 去联网核验）"
    out = []
    for i, k in enumerate(profile.knowledge, 1):
        title = k.get("title") or k.get("content") or str(k)
        out.append("%d. %s" % (i, title))
    return "\n".join(out)


def premise_extraction_prompt(text: str, profile: DomainProfile) -> str:
    """第一步：让用户已声明的前提显式化。"""
    signals = "\n".join(
        "- key=%s | %s | 命中词=%s | 否定词=%s"
        % (s.key, s.label_zh, s.patterns, s.negate_patterns)
        for s in profile.premise_signals
    )
    return (
        "你是「%s」领域的合规参谋。请从用户原话中抽取下列前提信号（只输出 JSON 键值对）：\n"
        "%s\n\n用户原话：\n\"%s\"\n\n"
        "输出 JSON，例如 {\"has_individual_business_license\": true}。"
        "抽不到就给默认值 false。不要编造。"
    ) % (profile.name_zh, signals, text)


def analysis_prompt(text: str, profile: DomainProfile,
                    premises: Dict[str, bool], verified_rules: List[str]) -> str:
    """第三步：在前提与已核验规则约束下做多维剖析。"""
    dims = "\n".join("- %s" % d for d in profile.analysis_dimensions)
    risks = "\n".join("- %s" % r for r in profile.risk_dimensions)
    matrix = "\n".join(
        "## %s\n%s" % (dim, "\n".join("  - %s" % p for p in pts))
        for dim, pts in profile.compliance_matrix.items()
    )
    rules = "\n".join("- %s" % r for r in verified_rules) or "（未提供）"
    return (
        "你是「%s」领域专业参谋，请基于以下约束产出结构化建议。\n\n"
        "【已抽取前提】\n%s\n\n"
        "【已核验的现行规则（2025–2026）】\n%s\n\n"
        "【合规清单矩阵——必须逐条覆盖】\n%s\n\n"
        "【必须剖析的维度】\n%s\n\n"
        "【必须提示的风险维度】\n%s\n\n"
        "用户诉求：\n\"%s\"\n\n"
        "要求：① 每条建议都标注它对应哪条已核验规则或前提（无依据不许写）；"
        "② 若用户已有某资质，优先给出「直接用该资质拿满权益」的路径，不要降级建议；"
        "③ 明确区分「你作为卖家要办的」与「供应商/厂家持有的资质」。"
        "输出 Markdown 清单。"
    ) % (
        profile.name_zh,
        _fmt_premises(premises),
        rules,
        matrix,
        dims,
        risks,
        text,
    )


def selfcheck_prompt(text: str, profile: DomainProfile,
                     premises: Dict[str, bool], draft: str) -> str:
    """第四步：自检闸门（让 LLM 自己挑自己的矛盾）。"""
    constraints = "\n".join(
        "- 若前提 %s=true，则建议里**禁止**出现 %s（否则自相矛盾）。纠正话术：%s"
        % (c.if_premise, c.forbid_reco_contains, c.warn_zh)
        for c in profile.premise_constraints
    ) or "（无）"
    return (
        "请作为严格审校，检查下面这份「%s」建议草稿是否自相矛盾或给出过时/错误建议。\n\n"
        "【用户前提】\n%s\n\n【自相矛盾红线】\n%s\n\n【草稿】\n%s\n\n"
        "输出：若有问题，逐条列出\"问题+修正\"；若无误，输出\"PASS\"。"
    ) % (profile.name_zh, _fmt_premises(premises), constraints, draft)


__all__ = [
    "premise_extraction_prompt",
    "analysis_prompt",
    "selfcheck_prompt",
]
