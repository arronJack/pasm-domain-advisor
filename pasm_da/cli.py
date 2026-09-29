"""pasm-da 命令行入口（python -m pasm_da.cli / pasm-da 脚本）。"""
from __future__ import annotations

import argparse
import sys

from .agent import DomainAdvisorAgent
from . import profiles as P


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pasm-da", description="泛例 PASM 领域顾问")
    sub = ap.add_subparsers(dest="cmd", required=False)

    run = sub.add_parser("run", help="对一段文本产出顾问清单")
    run.add_argument("--profile", default="douyin_pet_store")
    run.add_argument("--text", required=True)
    run.add_argument("--out-dir", default=None)

    sub.add_parser("list", help="列出已注册领域 profile")
    sub.add_parser("demo", help="运行预置剧本（抖音宠物店）")

    args = ap.parse_args(argv)
    if args.cmd == "list" or args.cmd is None:
        print("已注册 profile：")
        for pid in P.list_ids():
            print("  -", pid)
        return 0
    if args.cmd == "demo":
        from .quickstart import main as demo
        demo()
        return 0
    if args.cmd == "run":
        agent = DomainAdvisorAgent("cli", profile_id=args.profile, out_dir=args.out_dir)
        report = agent.advise(args.text)
        print(report.markdown)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
