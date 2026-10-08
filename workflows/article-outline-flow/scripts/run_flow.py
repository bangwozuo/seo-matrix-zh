# -*- coding: utf-8 -*-
"""
文章大纲生成工作流 —— 端到端编排脚本（与 SKILL.md 步骤链路一致）。

  S1 输入解析      从输入文本拆出「主题 + 差距清单」（确定性）
  S2 大纲结构生成  差距点逐条落位 H2，按用途档位配字数预算（确定性）
  S3 预算校验落盘  总字数落在档位区间（误差 ≤10%）→ 大纲.md + flow.json

用法：
  python run_flow.py --input examples/input.json --outdir out
  python run_flow.py --demo
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WF_DIR = os.path.dirname(HERE)

BUDGET = {"博客长文": (2500, 4000), "帮助文档": (1200, 2000), "落地页": (800, 1200)}
LEAD_BUDGET, TAIL_BUDGET, GAP_BUDGET = 120, 400, 500


def load_input(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def s1_parse(cur):
    text = str(cur.get("input", ""))
    purpose = str(cur.get("purpose", "") or "")
    topic = ""
    m = re.search(r"主题[：:]\s*(.+)", text)
    if m:
        topic = m.group(1).strip()
    gaps = []
    for ln in text.splitlines():
        m = re.match(r"^(\d+)[.、)\]]\s*(.+)$", ln.strip())
        if m and len(m.group(2)) > 6:
            gaps.append({"no": int(m.group(1)), "text": m.group(2).strip()})
    return topic, gaps, purpose


def guess_purpose(purpose, n_gaps=0):
    if n_gaps >= 3 or "长文" in purpose or "指南" in purpose:
        return "博客长文"
    if "落地页" in purpose:
        return "落地页"
    if "帮助" in purpose or "文档" in purpose:
        return "帮助文档"
    return "博客长文"


def s2_outline(topic, gaps, purpose):
    """导语 + 差距点逐条成段 + 收尾，字数按档位预算。"""
    sections = [{"no": 0, "title": "导语（结论前置）", "role": "回答「值不值得读」，点明目标关键词",
                 "points": "预告下文覆盖的差距点；给出核心结论一句话", "budget": LEAD_BUDGET}]
    for g in gaps:
        title = g["text"]
        cut = re.split(r"[：;；。]", title)[0]
        sections.append({"no": g["no"], "title": f"H2：{cut[:24]}（差距点{g['no']}）",
                         "role": f"落地差距点{g['no']}，给出可执行建议",
                         "points": title[:60], "budget": GAP_BUDGET})
    sections.append({"no": 99, "title": "H2：选购建议与常见问题（FAQ）",
                     "role": "承接交易型意图，收口导流",
                     "points": "按预算档给取舍建议 + FAQ 3 条（每条 40~80 字）", "budget": TAIL_BUDGET})
    total = sum(s["budget"] for s in sections)
    return sections, total


def s3_check(sections, total, purpose):
    lo, hi = BUDGET[purpose]
    ok = lo * 0.9 <= total <= hi * 1.1
    note = (f"预算合计 {total} 字，档位 {purpose}（{lo}~{hi} 字，容差 ±10%）—— "
            + ("达标" if ok else f"未达标，建议{'增' if total < lo else '减'}配额"))
    return ok, note, (lo, hi)


def write_outputs(topic, gaps, sections, total, purpose, check, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "大纲段落预算.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["#", "段落", "功能定位", "要点提示", "字数建议"])
        w.writeheader()
        for s in sections:
            w.writerow({"#": s["no"], "段落": s["title"], "功能定位": s["role"],
                        "要点提示": s["points"], "字数建议": s["budget"]})
    files.append(p)

    summary = (f"主题「{topic[:30]}」解析出 {len(gaps)} 个差距点，生成 {len(sections)} 段大纲，"
               f"预算合计 {total} 字（{purpose} 档）。校验：{check[1]}")
    steps = [f"S1 输入解析：主题 1 条 + 差距点 {len(gaps)} 条；用途判定为「{purpose}」",
             f"S2 大纲结构生成：导语 120 字 + 差距段 {GAP_BUDGET} 字×{len(gaps)} + 收尾 {TAIL_BUDGET} 字",
             f"S3 预算校验：合计 {total} 字 → {'达标' if check[0] else '未达标'}，产物落盘 3 件"]
    js = {"summary": summary, "steps": steps,
          "deliverable": {"topic": topic, "gaps": [g["no"] for g in gaps],
                          "sections": sections, "total_budget": total, "purpose": purpose},
          "note": "差距点落位与字数预算由本脚本计算；段落标题润色由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", f"# 大纲：{topic}", "", "## 结构框架", "",
          "| # | 段落 | 功能定位 | 要点提示 | 字数建议 |", "|---|---|---|---|---|"]
    for s in sections:
        md.append(f"| {s['no']} | {s['title']} | {s['role']} | {s['points']} | {s['budget']} |")
    md += ["", "## 结构原理", "",
           f"1. 用途档位：{purpose}（{check[2][0]}~{check[2][1]} 字），预算合计 {total} 字",
           f"2. 差距覆盖：{len(gaps)} 个差距点逐条落位 H2，编号与差距清单一一对应",
           f"3. 校验结果：{check[1]}"]
    p = os.path.join(outdir, "大纲.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="文章大纲生成工作流（解析 → 结构生成 → 预算校验）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    src = os.path.join(WF_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    cur = load_input(src)
    topic, gaps, purpose = s1_parse(cur)
    if not topic or not gaps:
        print("[错误] 未解析到主题或差距清单，缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    purpose = guess_purpose(purpose, len(gaps))
    sections, total = s2_outline(topic, gaps, purpose)
    check = s3_check(sections, total, purpose)
    files = write_outputs(topic, gaps, sections, total, purpose, check, a.outdir)
    print(f"S1 主题+{len(gaps)} 差距点 | S2 大纲 {len(sections)} 段 | S3 合计 {total} 字 {'达标' if check[0] else '未达标'}")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
