"""TOP5 SKU 定价测算表生成器（独立可跑）。

用法：
    python examples/pricing_spreadsheet.py --out pricing_top5.xlsx

公式：建议售价 = (进货价 + 运费) / (1 - 平台技术服务费% - 目标利润率%)
优先生成 .xlsx（需 openpyxl），否则退回 .csv（UTF-8-SIG，Excel 可直接打开）。
"""
from __future__ import annotations

import argparse
import csv
import os


def _rows():
    # 示例 TOP5：宠物店常见轻/重货。替换为你真实数据即可。
    return [
        # SKU, 进货价, 预估运费, 平台技术服务费%, 目标利润率%, 备注
        ["除臭喷雾 300ml", 12.0, 3.0, 2.0, 40.0, "轻货利润款"],
        ["逗宠漏食球", 6.0, 2.0, 2.0, 45.0, "轻货好玩好拍"],
        ["颜值牵引绳", 18.0, 3.5, 5.0, 35.0, "客单适中易出图"],
        ["猫砂 6L", 25.0, 12.0, 5.0, 25.0, "重货引流款·就近仓发"],
        ["冻干零食 50g", 20.0, 4.0, 5.0, 38.0, "需供应商饲料资质"],
    ]


def build_xlsx(path: str) -> bool:
    try:
        from openpyxl import Workbook
    except Exception:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "TOP5 SKU 定价测算"
    header = ["SKU", "进货价", "预估运费", "平台技术服务费%", "目标利润率%",
              "建议售价(公式)", "建议售价(值)", "备注"]
    ws.append(header)
    for sku, cost, ship, fee, margin, note in _rows():
        formula = "=ROUND((B{r}+C{r})/(1-D{r}/100-E{r}/100),1)".format(r=ws.max_row + 1)
        val = round((cost + ship) / (1 - fee / 100 - margin / 100), 1)
        ws.append([sku, cost, ship, fee, margin, formula, val, note])
    wb.save(path)
    return True


def build_csv(path: str) -> str:
    if not path.lower().endswith(".csv"):
        path = path + ".csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SKU", "进货价", "预估运费", "平台技术服务费%", "目标利润率%",
                    "建议售价", "备注"])
        for sku, cost, ship, fee, margin, note in _rows():
            val = round((cost + ship) / (1 - fee / 100 - margin / 100), 1)
            w.writerow([sku, cost, ship, fee, margin, val, note])
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="pricing_top5.xlsx")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    if build_xlsx(out):
        print("已生成 xlsx：", out)
        return 0
    csv_path = build_csv(out)
    print("openpyxl 未安装，已退回生成 csv：", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
