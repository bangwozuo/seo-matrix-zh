# -*- coding: utf-8 -*-
"""
关键词聚类 —— 按搜索意图 + 共享核心词的确定性聚类。

职责边界：
  本脚本只做确定性计算：条目解析、意图分类（交易/比较/信息教程/导航）、
  核心词归并、频次统计、产物落盘。
  主题命名润色、共性洞察的业务解读由模型按 prompt.txt 完成。

意图分类规则（按优先级，与 prompt.txt 一致）：
  R1 交易型   含 免费/下载/价格/报价/多少钱/购买/开通/申请
  R2 比较型   含 对比/vs/排名/推荐/哪个好/怎么选/排行榜
  R3 教程型   含 教程/怎么/如何/入门/指南/步骤/方法
  R4 信息型   其余（问答/定义/含金量类疑问词也归此）

用法：
  python cluster.py --input ../examples/input.json --outdir out
  python cluster.py --demo --outdir out      # 读取 examples/input.json 演示

产物：
  out/聚类结果.csv    每条关键词的簇归属与意图
  out/cluster.json    机器可读结果（簇/洞察素材/证据索引）
  out/聚类报告.md     Markdown 汇总表（对话内交付同款结构）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.dirname(HERE)

INTENT_RULES = [
    ("交易型", ["免费", "下载", "价格", "报价", "多少钱", "购买", "开通", "申请", "优惠"]),
    ("比较型", ["对比", "vs", "VS", "排名", "推荐", "哪个好", "怎么选", "排行榜", "测评"]),
    ("教程型", ["教程", "怎么", "如何", "入门", "指南", "步骤", "方法", "设置"]),
]

STOP_TOKENS = {"在线", "工具", "软件", "免费", "推荐", "下载", "企业版", "网页版"}


def parse_items(raw):
    """把 items（字符串编号清单 / 换行清单 / 数组）解析成 [{idx, text}]。"""
    if isinstance(raw, list):
        return [{"idx": i + 1, "text": str(t).strip()} for i, t in enumerate(raw) if str(t).strip()]
    lines = [ln.strip() for ln in str(raw).splitlines() if ln.strip()]
    items = []
    for ln in lines:
        m = re.match(r"^(\d+)[.、)\]]\s*(.+)$", ln)
        if m:
            items.append({"idx": int(m.group(1)), "text": m.group(2).strip()})
        else:
            items.append({"idx": len(items) + 1, "text": ln})
    return items


def classify_intent(text):
    low = text.lower()
    for name, kws in INTENT_RULES:
        for kw in kws:
            if kw.lower() in low:
                return name, kw
    return "信息型", ""


def core_token(text):
    """共享核心词：取分词后最早出现的高频实词（长度 ≥2 且不在停用表）。"""
    toks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text)
    for t in toks:
        if len(t) >= 2 and t not in STOP_TOKENS:
            return t
    return toks[0] if toks else text


def cluster(items):
    """先按核心词归并，再叠加意图标签；簇间按条目数降序。"""
    groups = OrderedDict()
    for it in items:
        intent, hit = classify_intent(it["text"])
        core = core_token(it["text"])
        key = f"{core}"
        groups.setdefault(key, []).append({**it, "意图": intent, "命中词": hit, "核心词": core})
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    clusters = []
    for i, (core, rows) in enumerate(ordered, 1):
        intents = Counter(r["意图"] for r in rows)
        main_intent = intents.most_common(1)[0][0]
        clusters.append({
            "cluster_id": i,
            "核心词": core,
            "意图": main_intent,
            "条目数": len(rows),
            "条目": [f"{r['idx']}. {r['text']}" for r in rows],
            "意图分布": dict(intents),
        })
    return clusters


def insights(clusters, items):
    """确定性洞察素材：覆盖率、最大簇、意图分布（业务解读交给模型）。"""
    n = len(items)
    intent_all = Counter(c["意图"] for c in clusters)
    top = clusters[0] if clusters else None
    out = [
        f"共 {n} 条关键词，归并为 {len(clusters)} 个主题簇，平均每簇 {round(n / max(len(clusters), 1), 1)} 条",
        f"最大簇「{top['核心词']}」{top['条目数']} 条，占 {round(top['条目数'] / n * 100)}%（{top['意图']}为主）",
        "簇级意图分布：" + "；".join(f"{k} {v} 簇" for k, v in intent_all.most_common()),
    ]
    return out


def evidence(clusters):
    ev = []
    for c in clusters:
        ev.append(f"簇{c['cluster_id']}（{c['核心词']}）← 条目 {'、'.join(x.split('.')[0] for x in c['条目'])}")
    return ev


def write_outputs(items, clusters, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    rows = []
    for c in clusters:
        for t in c["条目"]:
            idx, text = t.split(". ", 1)
            rows.append({"序号": idx, "关键词": text, "主题簇": f"簇{c['cluster_id']} {c['核心词']}",
                         "意图": c["意图"], "条目数": c["条目数"]})
    p = os.path.join(outdir, "聚类结果.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["序号", "关键词", "主题簇", "意图", "条目数"])
        w.writeheader()
        w.writerows(rows)
    files.append(p)

    js = {
        "summary": {
            "总条目": len(items), "主题簇数": len(clusters),
            "意图分布": dict(Counter(c["意图"] for c in clusters)),
        },
        "clusters": clusters,
        "insights": insights(clusters, items),
        "evidence": evidence(clusters),
        "note": "簇归属/意图/频次由本脚本判定；主题命名润色与业务解读由模型按 prompt.txt 完成",
    }
    p = os.path.join(outdir, "cluster.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 分组结果", "",
          "| # | 主题（核心词） | 意图 | 包含条目 | 频次 |", "|---|---|---|---|---|"]
    for c in clusters:
        md.append(f"| {c['cluster_id']} | {c['核心词']} | {c['意图']} | {'；'.join(c['条目'])} | {c['条目数']} |")
    md += ["", "## 共性洞察", ""] + [f"{i}. {s}" for i, s in enumerate(insights(clusters, items), 1)]
    md += ["", "## 证据索引", ""] + [f"{i}. {s}" for i, s in enumerate(evidence(clusters), 1)]
    p = os.path.join(outdir, "聚类报告.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="关键词聚类（意图 + 核心词，确定性）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true", help="用 examples/input.json 演示")
    a = ap.parse_args()

    src = os.path.join(ASSET_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo（examples/input.json 存在）")
    with open(src, encoding="utf-8") as f:
        cur = json.load(f)
    items = parse_items(cur.get("items", ""))
    if not items:
        print("[错误] items 为空：缺数据不补造，请先提供关键词清单。", file=sys.stderr)
        sys.exit(3)
    clusters = cluster(items)
    files = write_outputs(items, clusters, a.outdir)
    print(f"条目 {len(items)} | 主题簇 {len(clusters)} | 意图分布 "
          f"{dict(Counter(c['意图'] for c in clusters))}")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
