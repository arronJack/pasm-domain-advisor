"""发布前自检：引擎 + MCP 适配器 + 版本一致性。

跑法：python tools/selfcheck.py
退出码 0 = 全绿；否则失败。CI / 发布前必跑。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ok: bool = True


def check(cond: bool, msg: str) -> None:
    global ok
    print("  %s %s" % ("v" if cond else "x", msg))
    if not cond:
        ok = False


def main() -> int:
    print("pasm-domain-advisor selfcheck")

    # 1) 版本一致性：pyproject.version == pasm_da/__init__.__version__
    pp = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ini = (ROOT / "pasm_da" / "__init__.py").read_text(encoding="utf-8")
    a = re.search(r'^version\s*=\s*"([^"]+)"', pp, re.M).group(1)
    b = re.search(r'__version__\s*=\s*"([^"]+)"', ini).group(1)
    check(a == b, "版本号一致（pyproject=%s, __init__=%s）" % (a, b))

    from pasm_da import profiles as P
    from pasm_da import DomainAdvisorAgent
    from pasm_da import gate as G

    # 2) 三个 profile 正确流都应「矛盾 0 / 无依据 0」
    good = {
        "douyin_pet_store": "我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店卖猫砂和冻干。",
        "cross_border_ecom": "我有海关注册登记和品牌授权，想做跨境电商出口到欧美。",
        "food_business_license": "我打算开个小店，只卖预包装食品，有固定门面。",
    }
    out = ROOT / "examples" / "out"
    out.mkdir(parents=True, exist_ok=True)
    for pid, txt in good.items():
        r = DomainAdvisorAgent("t", profile_id=pid, out_dir=str(out)).advise(txt)
        con = len(r.gate.contradictions()) if r.gate else -1
        ung = len(r.gate.ungrounded()) if r.gate else -1
        check(con == 0 and ung == 0,
              "%s 正确流 矛盾=%d 无依据=%d" % (pid, con, ung))

    # 3) 三个领域各自的错误流都应被闸门拦截
    bad = [
        ("douyin_pet_store", "新手可以先开个人店试水，跑通了再升级。",
         {"has_individual_business_license": True}),
        ("cross_border_ecom", "走个人代购不报关直接发货最省事。",
         {"has_customs_registration": True}),
        ("food_business_license", "你这种情况得先办食品经营许可证才能上架卖。",
         {"only_prepackaged": True}),
    ]
    for pid, reco, prem in bad:
        rep = G.verify_advice([reco], prem, P.get(pid), [])
        check(len(rep.contradictions()) >= 1,
              "%s 错误流被拦截（矛盾=%d）" % (pid, len(rep.contradictions())))

    # 4) MCP 适配器 selftest
    from pasm_da.adapters import mcp as mcpmod
    r = mcpmod.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = [t["name"] for t in r["result"]["tools"]]
    check(set(["da_list_profiles", "da_advise"]).issubset(set(names)),
          "MCP tools/list 含 da_* 工具")
    r = mcpmod.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "da_advise",
                                          "arguments": {"profile_id": "douyin_pet_store",
                                                        "text": "我已有个体户执照"}}})
    check(r["result"]["structuredContent"]["ok"], "MCP da_advise 正常产出")

    print("selfcheck:", "通过" if ok else "失败")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
