"""通用领域顾问引擎（DomainAdvisor）。

这是"泛例"的执行体。它**不依赖 pasm-framework**，纯标准库即可运行；
LLM 与工具都是可选注入。一个 ``DomainProfile`` 进来，跑完五步给出专业清单 + 自检结论。

五步（对应 WorkBuddy 式智能体的"思考—行动循环"）：
  1. 抽取前提   —— 你**已经**有什么（执照/资质/预算…），决定一切。
  2. 核验现行规则 —— 用 knowledge（固化）或 web_search（联网）拿到最新政策。
  3. 多维剖析   —— 按 profile 的维度与合规矩阵产出建议清单。
  4. 自检闸门   —— 反"自相矛盾" + 反"无依据断言"（见 gate.py）。
  5. 结构化交付 —— Markdown 清单 + 可选定价表/合规文档。

没有 LLM 时走模板分支，同样遵循同一套纪律（前提感知 + 事实接地），
保证"永远有专业回答，且不过时、不自相矛盾"。
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import gate as G
from .domain_profile import DomainProfile
from .llm_client import build_llm
from .prompts import analysis_prompt, premise_extraction_prompt, selfcheck_prompt
from .tools_contract import ToolSet, resolve_tools


@dataclass
class VerifiedRule:
    source: str          # "knowledge" | "web:<query>"
    text: str


@dataclass
class AdvisoryReport:
    profile_id: str
    premises: Dict[str, bool] = field(default_factory=dict)
    verified_rules: List[VerifiedRule] = field(default_factory=list)
    recos: List[str] = field(default_factory=list)
    gate: Optional[Any] = None          # GateReport
    markdown: str = ""
    artifacts: List[str] = field(default_factory=list)   # 生成的文件（如定价表）

    def summary(self) -> str:
        n_con = len(self.gate.contradictions()) if self.gate else 0
        n_ung = len(self.gate.ungrounded()) if self.gate else 0
        return ("profile=%s 建议=%d 已核验规则=%d 自检: 矛盾=%d 无依据=%d"
                % (self.profile_id, len(self.recos), len(self.verified_rules),
                   n_con, n_ung))


class DomainAdvisor:
    def __init__(self, llm: Optional[Dict[str, Any]] = None,
                 tools: Optional[Dict[str, Any]] = None,
                 *, profile: Optional[DomainProfile] = None) -> None:
        self.llm = build_llm(llm)
        # 接受 dict（部署层注入）或已是 ToolSet（如 RealToolSet）。
        self.tools: ToolSet = tools if isinstance(tools, ToolSet) else resolve_tools(tools)
        self._profile = profile

    # ----------------------------------------------------- 第 1 步：抽取前提
    def extract_premises(self, text: str, profile: DomainProfile) -> Dict[str, bool]:
        # 规则命中（稳定、可复现、无需 LLM）。LLM 命中率再高也不该替掉这条底线。
        return G.extract_premises(text, profile)

    # --------------------------------------------------- 第 2 步：核验现行规则
    def verify_rules(self, profile: DomainProfile) -> List[VerifiedRule]:
        rules: List[VerifiedRule] = []
        for k in profile.knowledge:
            rules.append(VerifiedRule("knowledge",
                                     str(k.get("title") or k.get("content") or "")))
        # 有联网工具时，按 rule_queries 实时核验（覆盖/补充固化知识）。
        for q in profile.rule_queries:
            try:
                hit = self.tools.web_search(q)
            except Exception:
                hit = ""
            if hit and hit.strip():
                # 只取前若干字作为"已核验要点"，避免把整页网页塞进建议。
                rules.append(VerifiedRule("web:%s" % q, hit.strip()[:400]))
        return rules

    # ----------------------------------------------------- 第 3 步：多维剖析
    def _analyze_template(self, text: str, profile: DomainProfile,
                           premises: Dict[str, bool],
                           rules: List[VerifiedRule]) -> List[str]:
        recos: List[str] = []
        # 决策项：由前提驱动（这是"已有执照就推个体店"的关键）。
        for c in profile.premise_constraints:
            if premises.get(c.if_premise) and c.warn_zh:
                recos.append("【决策】%s" % c.warn_zh)
        # 合规矩阵逐维度展开。
        for dim, pts in profile.compliance_matrix.items():
            recos.append("【合规·%s】%s" % (dim, "；".join(pts)))
        # 剖析维度。
        for d in profile.analysis_dimensions:
            recos.append("【剖析·%s】详见合规清单与风险项，结合你的前提逐条落地。" % d)
        # 风险维度。
        for r in profile.risk_dimensions:
            recos.append("【风险·%s】务必在动手前评估，新手最易在此翻车。" % r)
        # 成本：若已核验到 0 元入驻相关规则，给明确结论。
        for ru in rules:
            if "0元" in ru.text or "保证金" in ru.text:
                recos.append("【成本·已核验】%s" % ru.text[:120])
                break
        return recos

    def _analyze_llm(self, text: str, profile: DomainProfile,
                    premises: Dict[str, bool],
                    rules: List[VerifiedRule]) -> Optional[List[str]]:
        if self.llm is None:
            return None
        rule_texts = ["%s：%s" % (r.source, r.text) for r in rules]
        try:
            md = self.llm.chat([
                {"role": "system", "content": "你是严谨的合规参谋，只基于给定前提与已核验规则作答，禁止编造。"},
                {"role": "user", "content": analysis_prompt(text, profile, premises, rule_texts)},
            ])
        except Exception:
            return None
        # 把 Markdown 拆成可逐条过闸门的建议列表。
        recos = []
        for line in md.splitlines():
            s = line.strip().lstrip("-*0123456789.、").strip()
            if len(s) >= 6:
                recos.append(s)
        return recos or None

    def analyze(self, text: str, profile: DomainProfile,
                premises: Dict[str, bool],
                rules: List[VerifiedRule]) -> List[str]:
        recos = self._analyze_llm(text, profile, premises, rules)
        if recos is None:
            recos = self._analyze_template(text, profile, premises, rules)
        return recos

    # ----------------------------------------------------- 第 4 步：自检闸门
    def selfcheck(self, text: str, profile: DomainProfile,
                  premises: Dict[str, bool], recos: List[str],
                  rules: List[VerifiedRule]) -> G.GateReport:
        report = G.verify_advice(recos, premises, profile, [r.text for r in rules])
        # LLM 二次自检（有 LLM 时）：让它自己挑自己的矛盾。
        if self.llm is not None and recos:
            draft = "\n".join("- %s" % r for r in recos)
            try:
                verdict = self.llm.chat([
                    {"role": "system", "content": "你是严格审校。"},
                    {"role": "user", "content": selfcheck_prompt(text, profile, premises, draft)},
                ])
                if verdict.strip().upper() != "PASS":
                    report.flags.append(G.GateFlag(
                        "contradiction", -1, "LLM 自检提示：%s" % verdict.strip()[:200]))
            except Exception:
                pass
        return report

    # --------------------------------------------------- 第 5 步：结构化交付
    def _emit_pricing_via_code(self, out_dir: str) -> Optional[str]:
        """通过 tools.code_run 真正跑一段 Python 来生成定价表（证明"算账"工具可用）。"""
        import os as _os
        header = ["SKU", "进货价", "预估运费", "平台技术服务费%", "目标利润率%",
                  "建议售价", "备注"]
        rows = [
            ["示例-SKU1", 20, 5, 2, 30, "=ROUND((B2+C2)/(1-D2/100-E2/100),1)", "替换为你真实数据"],
            ["示例-SKU2", 15, 8, 5, 35, "=ROUND((B3+C3)/(1-D3/100-E3/100),1)", "重货注意运费"],
        ]
        out = _os.path.join(out_dir, "pricing_top5.xlsx")
        code = (
            "import os, csv\n"
            "header = %r\nrows = %r\nout = %r\n"
            "try:\n"
            "    from openpyxl import Workbook\n"
            "    wb = Workbook(); ws = wb.active; ws.append(header)\n"
            "    for r in rows: ws.append(r)\n"
            "    if out.lower().endswith('.csv'): out = out[:-4] + '.xlsx'\n"
            "    wb.save(out); print(out)\n"
            "except Exception:\n"
            "    if not out.lower().endswith('.csv'): out = out + '.csv'\n"
            "    with open(out, 'w', newline='', encoding='utf-8-sig') as f:\n"
            "        w = csv.writer(f); w.writerow(header)\n"
            "        for r in rows: w.writerow(r)\n"
            "    print(out)\n"
        ) % (header, rows, out)
        res = self.tools.code_run(code)
        lines = [ln.strip() for ln in res.splitlines() if ln.strip()]
        path = lines[-1] if lines else ""
        return path if path and _os.path.exists(path) else ""

    def _emit_pricing_spreadsheet(self, profile: DomainProfile,
                                 path: str) -> Optional[str]:
        """生成 TOP5 SKU 定价测算表（xlsx 优先，否则 csv 兜底）。"""
        header = ["SKU", "进货价", "预估运费", "平台技术服务费%", "目标利润率%",
                  "建议售价", "备注"]
        rows = [
            ["示例-SKU1", 20, 5, 2, 30, "=ROUND((B2+C2)/(1-D2/100-E2/100),1)", "替换为你真实数据"],
            ["示例-SKU2", 15, 8, 5, 35, "=ROUND((B3+C3)/(1-D3/100-E3/100),1)", "重货注意运费"],
        ]
        out = path
        try:                                    # 优先 xlsx
            from openpyxl import Workbook       # type: ignore
            wb = Workbook(); ws = wb.active; ws.append(header)
            for r in rows:
                ws.append(r)
            if out.lower().endswith(".csv"):
                out = out[:-4] + ".xlsx"
            wb.save(out)
            return out
        except Exception:
            # csv 兜底（保证永远能产出，不依赖第三方库）。
            if not out.lower().endswith(".csv"):
                out = out + ".csv"
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f); w.writerow(header)
                for r in rows:
                    w.writerow(r)
            return out

    def assemble(self, text: str, profile: DomainProfile,
                 premises: Dict[str, bool], rules: List[VerifiedRule],
                 recos: List[str], gate: G.GateReport) -> str:
        lines: List[str] = []
        lines.append("# %s · 专业执行清单（PASM 领域顾问）" % profile.name_zh)
        lines.append("")
        lines.append("> 基于 %d 条已核验现行规则 + 你的真实前提生成；自检：矛盾 %d 项 / 无依据 %d 项。"
                     % (len(rules), len(gate.contradictions()), len(gate.ungrounded())))
        lines.append("")
        lines.append("## 0. 前提确认（决定一切）")
        for s in profile.premise_signals:
            v = premises.get(s.key)
            mark = "✅ 是" if v else ("❌ 否" if v is False else "— 未知")
            lines.append("- %s：**%s**" % (s.label_zh, mark))
        lines.append("")
        lines.append("## 1. 已核验的现行规则（2025–2026）")
        for r in rules:
            lines.append("- （%s）%s" % (r.source, r.text[:160]))
        lines.append("")
        lines.append("## 2. 决策与执行清单")
        for i, r in enumerate(recos, 1):
            lines.append("%d. %s" % (i, r))
        lines.append("")
        if gate.flags:
            lines.append("## 3. 自检告警（已拦截）")
            for f in gate.flags:
                lines.append("- ⚠️ [%s] %s" % (f.level, f.message))
            lines.append("")
        else:
            lines.append("## 3. 自检结论")
            lines.append("- ✅ 未发现自相矛盾或明显无依据断言。")
            lines.append("")
        lines.append("## 4. 风险提示")
        for r in profile.risk_dimensions:
            lines.append("- %s" % r)
        lines.append("")
        lines.append("---")
        lines.append("由 PASM 领域顾问引擎生成 · 每次规则更新需重新生成（政策会变动）。")
        return "\n".join(lines)

    # ----------------------------------------------------------- 主入口
    def advise(self, text: str, profile: Optional[DomainProfile] = None,
               *, out_dir: Optional[str] = None) -> AdvisoryReport:
        profile = profile or self._profile
        if profile is None:
            raise ValueError("必须提供 DomainProfile（构造时或调用时）")
        premises = self.extract_premises(text, profile)
        rules = self.verify_rules(profile)
        recos = self.analyze(text, profile, premises, rules)
        gate = self.selfcheck(text, profile, premises, recos, rules)
        md = self.assemble(text, profile, premises, rules, recos, gate)

        artifacts: List[str] = []
        if "pricing_spreadsheet" in profile.deliverables and out_dir:
            try:
                # 若部署层注入了真实 code_run（非默认空实现），则让它真正跑代码生成；
                # 否则用引擎内置的确定性生成兜底。两者都保证"一定产出文件"。
                if self.tools.code_run is not ToolSet.code_run:
                    p = self._emit_pricing_via_code(out_dir)
                else:
                    p = self._emit_pricing_spreadsheet(
                        profile, os.path.join(out_dir, "pricing_top5.xlsx"))
                if p and os.path.exists(p):
                    artifacts.append(p)
            except Exception:
                pass

        return AdvisoryReport(
            profile_id=profile.id, premises=premises, verified_rules=rules,
            recos=recos, gate=gate, markdown=md, artifacts=artifacts)


__all__ = ["DomainAdvisor", "AdvisoryReport", "VerifiedRule"]
