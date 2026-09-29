"""pasm-da 预置剧本：抖音宠物店（纯引擎，无需框架 / LLM / 联网）。

演示"泛例"如何落地：一个 profile + 引擎 = 专业清单 + 自检。
运行：python -m pasm_da.quickstart
"""
from __future__ import annotations

from .agent import DomainAdvisorAgent
from . import gate as G
from . import profiles as P


def scenario_correct() -> None:
    print("=" * 64)
    print("场景 A：用户已有个体户执照（应直接推个体店）")
    print("=" * 64)
    agent = DomainAdvisorAgent("demo", profile=P.get("douyin_pet_store"))
    text = "我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店卖猫砂和冻干。"
    report = agent.advise(text)
    print(report.markdown)
    print("\n--- 自检摘要 ---")
    print(report.summary())


def scenario_gate_demo() -> None:
    print("\n" + "=" * 64)
    print("场景 B：自检闸门演示（拦截「已有执照却推个人店」的自相矛盾）")
    print("=" * 64)
    premises = {"has_individual_business_license": True}
    # 一条"坏建议"：明明有执照，却让"先个人店试水"。
    bad_recos = ["新手可以先开个人店试水，跑通了再升级。"]
    report = G.verify_advice(bad_recos, premises, P.get("douyin_pet_store"), [])
    for f in report.flags:
        print("  ⚠️ [%s] %s" % (f.level, f.message))
    print("  结论：", "PASS（无误）" if report.ok else "已拦截自相矛盾 ✅")


def main() -> None:
    scenario_correct()
    scenario_gate_demo()


if __name__ == "__main__":
    main()
