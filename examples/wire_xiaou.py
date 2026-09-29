"""完整接线示例：把 domain_advisor 当成小U 的"参谋内核"，真注入
三件套工具 + DeepSeek，跑出一份真实清单与定价表。

这就是 Phase A「小U 升级方案」的可运行落地版——证明小U 不再只是单轮壳：
  - 联网核验现行政策（web_search，需 PASM_DA_LIVE_WEB=1）
  - 算账（code_run 真跑 Python 生成定价表）
  - 读写（file_write 写盘）
  - DeepSeek 驱动多维剖析（缺则自动回落模板 + 固化知识）

用法：
    DEEPSEEK_API_KEY=sk-xxx python examples/wire_xiaou.py
    PASM_DA_LIVE_WEB=1 DEEPSEEK_API_KEY=sk-xxx python examples/wire_xiaou.py
"""
from __future__ import annotations

import os
import sys

from pasm_da import DomainAdvisorAgent
from pasm_da.tools_impl import build_default_tools, web_search_impl, code_run_impl, file_write_impl


def main() -> int:
    profile_id = sys.argv[1] if len(sys.argv) > 1 else "douyin_pet_store"
    user_text = (sys.argv[2] if len(sys.argv) > 2 else
                "我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店卖猫砂和冻干。")

    # 1) 真实工具：默认 web 离线安全；想真联网核验政策就打开 PASM_DA_LIVE_WEB。
    enable_web = os.environ.get("PASM_DA_LIVE_WEB") == "1"
    tools = build_default_tools(enable_web=enable_web)

    # 2) DeepSeek：从环境变量读 key；没有就回落模板版（不报错、不空白）。
    llm = None
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        llm = {"base_url": "https://api.deepseek.com/v1",
               "model": "deepseek-chat", "api_key": key}

    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)

    agent = DomainAdvisorAgent("xiaou", profile_id=profile_id, llm=llm,
                               tools=tools, out_dir=out_dir)
    report = agent.advise(user_text)

    print(report.markdown)
    print("\n--- 自检摘要 ---")
    print(report.summary())
    if report.artifacts:
        print("--- 生成的交付物 ---")
        for a in report.artifacts:
            print("  ", a)

    # 3) 演示 file_write 真写盘（把清单落文件，交给工作流）。
    md_path = os.path.join(out_dir, "%s_checklist.md" % profile_id)
    if file_write_impl(md_path, report.markdown):
        print("--- file_write 演示：清单已写至", md_path)

    # 4) 演示 code_run 真算账（算一个示例 SKU 的建议售价）。
    calc = code_run_impl(
        "import json\n"
        "cost, ship, fee, margin = 20, 5, 0.05, 0.30\n"
        "price = round((cost+ship)/(1-fee-margin), 1)\n"
        "print(json.dumps({'进货价':cost,'运费':ship,'建议售价':price}))\n"
    )
    print("--- code_run 演示：", calc)

    # 5) 演示 web_search（仅在 PASM_DA_LIVE_WEB=1 时返回真实摘要）。
    if enable_web:
        print("--- web_search 演示：", web_search_impl("抖音小店 0元入驻 2025")[:120])
    else:
        print("--- web_search 演示：离线（设 PASM_DA_LIVE_WEB=1 可真联网核验）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
