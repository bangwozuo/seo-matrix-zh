# -*- coding: utf-8 -*-
"""
竞品内容差距分析工作流 —— 端到端编排脚本（与 SKILL.md 步骤链路一致）。

  S1 SERP 条目解析  解析「N. 站点（类型）：标题「…」；正文结构摘要」（确定性）
  S2 覆盖矩阵构建   内容形态六分法 + 覆盖点频次统计（确定性，同 serp-competition-analysis）
  S3 差距清单落盘   频次 =1 的覆盖点即差异化机会 → 覆盖矩阵.csv + 差距清单.md + flow.json

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
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WF_DIR = os.path.dirname(HERE)

TYPE_RULES = [
    ("榜单型", ["排名", "十大", "TOP", "top", "榜单"]),
    ("评测型", ["实测", "对比", "Demo", "demo", "评测", "横评"]),
    ("问答型", ["靠谱吗", "知乎", "值得吗", "怎么样", "避坑", "翻车"]),
    ("工具下载型", ["模板", "下载", "免费", "工具", "资源"]),
    ("方法论文", ["维度", "怎么选", "如何", "方法论", "框架", "看懂", "入门", "指南"]),
    ("产品官网型", ["官网", "试用", "表单", "报价", "预约", "咨询"]),
]
FEATURE_PAT = re.compile(r"[（(「]([^）)」]{2,40})[）)」]")


def load_input(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def s1_parse(text):
    """支持两种条目格式：竖线表格式「N. 站点 | 标题 | 摘要」与「N. 站点（类型）：标题「…」；正文…」。"""
    query, entries = "", []
    for ln in str(text).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if not query and "查询词" in ln:
            query = re.sub(r"[（(].*?[）)]\s*$", "", ln.split("：", 1)[-1]).strip()
            continue
        m = re.match(r"^(\d+)[.、)\]]\s*(.+)$", ln)
        if not m:
            continue
        body = m.group(2)
        idx = int(m.group(1))
        if "|" in body:  # 竖线表格式
            parts = [p.strip() for p in body.split("|")]
            site = parts[0] if parts else ""
            title = parts[1] if len(parts) > 1 else ""
            summary = parts[2] if len(parts) > 2 else ""
        else:  # 冒号描述式
            sm = re.match(r"^([^：（):]+)", body)
            site = sm.group(1).strip() if sm else ""
            tm = re.search(r"标题[「『]?(.+?)[」』]?", body)
            title = tm.group(1).strip() if tm else ""
            summary = body.split(title, 1)[-1].lstrip("；;：:」』").strip() if title and title in body else body
        entries.append({"idx": idx, "site": site, "title": title, "body": summary})
    return query, entries


def s2_matrix(entries):
    for e in entries:
        full = e["title"] + "；" + e["body"]
        e["type"] = next((n for n, kws in TYPE_RULES if any(k in full for k in kws)), "其他")
        feats = set()
        for seg in FEATURE_PAT.findall(full):
            for piece in re.split(r"[/／、，,]", seg):
                piece = piece.strip()
                if 2 <= len(piece) <= 12:
                    feats.add(piece)
        if e["type"] != "其他":
            feats.add(e["type"])
        e["features"] = feats
    freq = Counter()
    for e in entries:
        freq |= Counter(e["features"])
    return freq


def s3_gaps(freq, entries):
    common = sorted([k for k, v in freq.items() if v >= 2], key=lambda k: -freq[k])
    gaps = sorted([k for k, v in freq.items() if v == 1])
    return common, gaps


def write_outputs(query, entries, freq, common, gaps, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "覆盖矩阵.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["序号", "站点", "类型", "标题", "覆盖点"])
        for e in entries:
            w.writerow([e["idx"], e["site"], e["type"], e["title"], "、".join(sorted(e["features"]))])
    files.append(p)

    types = Counter(e["type"] for e in entries)
    real = [(t, c) for t, c in types.most_common() if t != "其他"]
    lead_t, lead_c = real[0] if real else ("其他", types["其他"])
    summary = (f"查询词「{query}」共 {len(entries)} 条 SERP 结果，{len(types)} 类内容形态"
               f"（主导：{lead_t} {lead_c} 条，占 {round(lead_c / len(entries) * 100)}%）；"
               f"共性覆盖点 {len(common)} 个、独有覆盖点（差距机会）{len(gaps)} 个")
    steps = [f"S1 SERP 条目解析：{len(entries)} 条，查询词「{query}」",
             f"S2 覆盖矩阵：形态分布 {dict(types)}；覆盖点 {len(freq)} 个（共性 {len(common)} / 独有 {len(gaps)}）",
             f"S3 差距清单：{len(gaps)} 个机会点落盘 覆盖矩阵.csv + 差距清单.md + flow.json"]
    deliverable = {"common_points": {k: freq[k] for k in common},
                   "gap_points": gaps,
                   "type_dist": dict(types)}
    js = {"summary": summary, "steps": steps, "deliverable": deliverable,
          "note": "解析/频次统计由本脚本完成；差距点的大纲化由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 执行摘要", "", summary, "",
          "## 共性覆盖点（频次 ≥2，不覆盖难进第一梯队）", ""]
    md += [f"- {k}（×{freq[k]}）" for k in common] or ["- （无）"]
    md += ["", "## 差距机会清单（频次 =1，竞品未覆盖）", ""]
    md += [f"{i}. {g}" for i, g in enumerate(gaps, 1)] or ["1. （无）"]
    p = os.path.join(outdir, "差距清单.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="竞品内容差距分析工作流（解析 → 覆盖矩阵 → 差距清单）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    src = os.path.join(WF_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    cur = load_input(src)
    query, entries = s1_parse(cur.get("input", ""))
    if not entries:
        print("[错误] 未解析到 SERP 条目，缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    freq = s2_matrix(entries)
    common, gaps = s3_gaps(freq, entries)
    files = write_outputs(query, entries, freq, common, gaps, a.outdir)
    print(f"S1 {len(entries)} 条 | S2 覆盖点 {len(freq)} 个 | S3 差距机会 {len(gaps)} 个")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
