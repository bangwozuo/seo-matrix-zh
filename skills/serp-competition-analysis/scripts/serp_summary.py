# -*- coding: utf-8 -*-
"""
SERP 竞争分析 —— SERP Top10 内容结构与覆盖点的确定性摘要。

职责边界：
  本脚本只做确定性计算：条目解析、内容类型判别、覆盖点提取与频次统计、落盘。
  竞争策略、差距机会的业务判断由模型按 prompt.txt 完成。

内容类型规则（按命中关键词判别，与 prompt.txt 一致）：
  榜单型（排名/十大/TOP）、方法论文（维度/怎么选/框架）、评测型（实测/对比/Demo）、
  问答型（靠谱吗/知乎/值得吗）、工具下载型（模板/下载/免费）、产品官网型（官网/试用/表单）

覆盖点提取：标题与结构摘要里的「（）/／、」分隔特征词 + 内容类型词，
频次 ≥2 即计为共性覆盖点。

用法：
  python serp_summary.py --input ../examples/input.json --outdir out
  python serp_summary.py --demo --outdir out

产物：
  out/竞争格局.csv    每条 SERP 结果的类型与覆盖点
  out/serp.json       机器可读结果（分组/洞察素材/证据索引）
  out/竞争分析报告.md Markdown 分组结果
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
ASSET_DIR = os.path.dirname(HERE)

TYPE_RULES = [
    ("榜单型", ["排名", "十大", "TOP", "top", "榜单", "十佳"]),
    ("评测型", ["实测", "对比", "Demo", "demo", "评测", "横评", "测试"]),
    ("问答型", ["靠谱吗", "知乎", "值得吗", "怎么样", "避坑", "翻车"]),
    ("工具下载型", ["模板", "下载", "免费", "工具", "资源"]),
    ("方法论文", ["维度", "怎么选", "如何", "方法论", "框架", "看懂", "入门", "指南"]),
    ("产品官网型", ["官网", "试用", "表单", "报价", "预约", "咨询"]),
]
FEATURE_PAT = re.compile(r"[（(]([^）)]{2,40})[）)]")


def parse_entries(raw):
    """解析「N. 站点（类型）：标题「…」；正文…」条目；首行查询词单独返回。"""
    query, entries = "", []
    for ln in str(raw).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if not query and ("查询词" in ln or "目标查询词" in ln):
            query = ln.split("：", 1)[-1].strip()
            query = re.sub(r"[（(].*?[）)]\s*$", "", query).strip()  # 去掉「（百度 SERP 抓取摘要）」类尾巴
            continue
        m = re.match(r"^(\d+)[.、)\]]\s*(.+)$", ln)
        if m:
            entries.append({"idx": int(m.group(1)), "text": m.group(2)})
    return query, entries


def split_entry(text):
    site, title, body = "", "", text
    m = re.match(r"^([^：（):]+)", text)
    if m:
        site = m.group(1).strip()
    tm = re.search(r"标题[「『]?(.+?)[」』]?", text)
    title = tm.group(1).strip() if tm else ""
    if title and title in text:
        tail = text.split(title, 1)[-1]
        body = tail.lstrip("；;：:」』").strip()
    return site, title, body


def classify(text):
    for name, kws in TYPE_RULES:
        for kw in kws:
            if kw in text:
                return name, kw
    return "其他", ""


def features(title, body, ctype):
    """覆盖点：括号特征 + 类型词 + 标题实词（2-4 字中文片段简化）。"""
    feats = set()
    for seg in FEATURE_PAT.findall(title + "；" + body):
        for piece in re.split(r"[/／、，,]", seg):
            piece = piece.strip()
            if 2 <= len(piece) <= 12:
                feats.add(piece)
    if ctype != "其他":
        feats.add(ctype)
    return feats


def analyze(raw):
    query, entries = parse_entries(raw)
    rows = []
    for e in entries:
        site, title, body = split_entry(e["text"])
        ctype, hit = classify(e["text"])
        rows.append({"idx": e["idx"], "站点": site, "标题": title, "类型": ctype,
                     "命中词": hit, "覆盖点": features(title, body, ctype)})
    return query, rows


def cluster(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r["类型"], []).append(r)
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    out = []
    for i, (ctype, rs) in enumerate(ordered, 1):
        out.append({"cluster_id": i, "主题": ctype, "频次": len(rs),
                    "条目": [f"{r['idx']}. {r['站点']}" for r in rs],
                    "覆盖点": sorted(set().union(*[r["覆盖点"] for r in rs])) if rs else []})
    return out


def insights(query, rows, clusters):
    n = len(rows)
    if not n:
        return []
    freq = Counter()
    for r in rows:
        freq |= Counter(r["覆盖点"])
    common = [(k, v) for k, v in freq.most_common(8) if v >= 2]
    lines = [
        f"查询词「{query or '未标注'}」SERP 共 {n} 条结果，分为 {len(clusters)} 类内容形态",
        "主导形态：" + f"「{clusters[0]['主题']}」{clusters[0]['频次']} 条，占 {round(clusters[0]['频次'] / n * 100)}%",
    ]
    if common:
        lines.append("共性覆盖点（频次 ≥2）：" + "；".join(f"{k}×{v}" for k, v in common))
    singleton = [k for k, v in freq.items() if v == 1]
    if singleton:
        lines.append("独有覆盖点（仅 1 家覆盖，即差异化机会）：" + "、".join(singleton[:8]))
    return lines


def evidence(rows):
    return [f"条目{r['idx']}（{r['站点']}）类型={r['类型']}，覆盖点 {'、'.join(sorted(r['覆盖点'])) or '—'}"
            for r in rows]


def write_outputs(query, rows, clusters, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "竞争格局.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["序号", "站点", "标题", "类型", "覆盖点"])
        w.writeheader()
        for r in rows:
            w.writerow({"序号": r["idx"], "站点": r["站点"], "标题": r["标题"],
                        "类型": r["类型"], "覆盖点": "、".join(sorted(r["覆盖点"]))})
    files.append(p)

    js = {"query": query,
          "summary": {"结果数": len(rows), "内容类型数": len(clusters)},
          "clusters": clusters, "insights": insights(query, rows, clusters),
          "evidence": evidence(rows),
          "note": "类型判别/覆盖点频次由本脚本计算；竞争策略由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "serp.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "",
          f"查询词：{query or '（未标注）'}", "", "## 分组结果", "",
          "| # | 主题 | 包含条目 | 频次 |", "|---|---|---|---|"]
    for c in clusters:
        md.append(f"| {c['cluster_id']} | {c['主题']} | {'；'.join(c['条目'])} | {c['频次']} |")
    md += ["", "## 共性洞察", ""] + [f"{i}. {s}" for i, s in enumerate(insights(query, rows, clusters), 1)]
    md += ["", "## 证据索引", ""] + [f"{i}. {s}" for i, s in enumerate(evidence(rows), 1)]
    p = os.path.join(outdir, "竞争分析报告.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="SERP 竞争分析（类型判别 + 覆盖点频次，确定性）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()

    src = os.path.join(ASSET_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    with open(src, encoding="utf-8") as f:
        cur = json.load(f)
    query, rows = analyze(cur.get("items", ""))
    if not rows:
        print("[错误] 未解析到 SERP 条目：缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    clusters = cluster(rows)
    files = write_outputs(query, rows, clusters, a.outdir)
    print(f"查询词「{query}」| 结果 {len(rows)} | 类型 {len(clusters)}")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
