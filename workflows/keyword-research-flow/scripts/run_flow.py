# -*- coding: utf-8 -*-
"""
关键词调研工作流 —— 端到端编排脚本（与 SKILL.md 步骤链路一致）。

  S1 关键词解析      从输入文本解析「关键词 | 月搜索量 | KD」清单（确定性）
  S2 关键词聚类      意图四分法 + 核心词归并（确定性，同 keyword-cluster 技能规则）
  S3 汇总落盘        主题簇 CSV + 执行摘要 MD + flow.json

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
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
WF_DIR = os.path.dirname(HERE)

INTENT_RULES = [
    ("交易型", ["免费", "下载", "价格", "报价", "多少钱", "购买", "开通", "申请"]),
    ("比较型", ["对比", "vs", "排名", "推荐", "哪个好", "怎么选", "排行榜", "网课", "机构"]),
    ("教程型", ["教程", "怎么", "如何", "入门", "指南", "步骤", "方法", "大纲"]),
]
STOP_TOKENS = set()  # 品类词由 _detect_generic 按出现率自动识别


def load_input(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def s1_parse(text):
    """解析「N. 关键词 | 搜索量 | KD」行；无搜索量时该列记 None。"""
    kws = []
    for ln in str(text).splitlines():
        ln = ln.strip()
        m = re.match(r"^(\d+)[.、)\]]\s*(.+)$", ln)
        if not m:
            continue
        parts = [p.strip() for p in m.group(2).split("|")]
        kw = parts[0]
        vol = int(re.sub(r"[,，]", "", parts[1])) if len(parts) > 1 and re.fullmatch(r"[\d,，]+", parts[1]) else None
        kd = int(parts[2]) if len(parts) > 2 and re.fullmatch(r"\d+", parts[2]) else None
        kws.append({"idx": int(m.group(1)), "kw": kw, "vol": vol, "kd": kd})
    return kws


def _intent(kw):
    for name, kws in INTENT_RULES:
        for t in kws:
            if t in kw:
                return name
    return "信息型"


def _core(kw):
    for t in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", kw):
        if t not in STOP_TOKENS and t not in {x for _, ks in INTENT_RULES for x in ks} and len(t) >= 2:
            return t
    return kw.split()[0] if kw.split() else kw


def _core(kw, generic=None):
    """核心词 = 差异词（跳过品类词/意图词/停用词）的前两字，同头关键词自然归并。"""
    generic = generic or set()
    rule_words = {x for _, ks in INTENT_RULES for x in ks}
    toks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", kw)
    for t in toks:
        if len(t) < 2 or t in generic or t in rule_words or t in STOP_TOKENS:
            continue
        return t[:2] if re.fullmatch(r"[\u4e00-\u9fff]+", t) and len(t) > 2 else t
    return toks[-1][:2] if toks else kw


def _detect_generic(kws):
    """品类词：出现在 ≥60% 条目中的 token。"""
    n = len(kws)
    freq = {}
    for k in kws:
        for t in set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", k["kw"])):
            freq[t] = freq.get(t, 0) + 1
    return {t for t, c in freq.items() if c >= max(2, n * 0.6)}


def s2_cluster(kws):
    generic = _detect_generic(kws)
    groups = OrderedDict()
    for k in kws:
        groups.setdefault(_core(k["kw"], generic), []).append({**k, "意图": _intent(k["kw"])})
    clusters = []
    for i, (core, rows) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])), 1):
        vols = [r["vol"] for r in rows if r["vol"] is not None]
        kds = [r["kd"] for r in rows if r["kd"] is not None]
        clusters.append({
            "cluster_id": i, "核心词": core,
            "意图": max((r["意图"] for r in rows), key=[r["意图"] for r in rows].count),
            "条目数": len(rows),
            "总搜索量": sum(vols) if vols else None,
            "平均KD": round(sum(kds) / len(kds), 1) if kds else None,
            "条目": [f"{r['idx']}. {r['kw']}" for r in rows],
        })
    return clusters


def write_outputs(kws, clusters, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "主题簇.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["簇", "核心词", "意图", "条目数", "总搜索量", "平均KD", "包含条目"])
        for c in clusters:
            w.writerow([c["cluster_id"], c["核心词"], c["意图"], c["条目数"],
                        c["总搜索量"] or "", c["平均KD"] if c["平均KD"] is not None else "",
                        "；".join(c["条目"])])
    files.append(p)

    total_vol = sum(c["总搜索量"] or 0 for c in clusters)
    high = [c for c in clusters if (c["平均KD"] or 0) <= 35]
    summary = (f"解析 {len(kws)} 个关键词，聚为 {len(clusters)} 个主题簇，"
               f"合计月搜索量 {total_vol:,}；低难度簇（平均KD≤35）{len(high)} 个，"
               f"建议优先排产：{'、'.join(c['核心词'] for c in high[:3])}")
    steps = [
        f"S1 关键词解析：{len(kws)} 条（含搜索量 {sum(1 for k in kws if k['vol'])} 条、KD {sum(1 for k in kws if k['kd'] is not None)} 条）",
        f"S2 关键词聚类：{len(clusters)} 簇，最大簇「{clusters[0]['核心词']}」{clusters[0]['条目数']} 条",
        f"S3 汇总落盘：主题簇.csv + 执行摘要.md + flow.json",
    ]
    deliverable = {"clusters": clusters, "summary_text": summary}

    js = {"summary": summary, "steps": steps, "deliverable": deliverable,
          "note": "解析/聚类/统计由本脚本完成；主题命名润色由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 执行摘要", "", summary, "", "## 主题簇", "",
          "| # | 核心词 | 意图 | 条目数 | 总搜索量 | 平均KD |", "|---|---|---|---|---|---|"]
    for c in clusters:
        md.append(f"| {c['cluster_id']} | {c['核心词']} | {c['意图']} | {c['条目数']} | "
                  f"{c['总搜索量'] or '—'} | {c['平均KD'] if c['平均KD'] is not None else '—'} |")
    p = os.path.join(outdir, "执行摘要.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="关键词调研工作流（S1 解析 → S2 聚类 → S3 落盘）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true", help="用 examples/input.json 演示")
    a = ap.parse_args()
    src = os.path.join(WF_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    cur = load_input(src)
    kws = s1_parse(cur.get("input", ""))
    if not kws:
        print("[错误] 未解析到关键词清单，缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    clusters = s2_cluster(kws)
    files = write_outputs(kws, clusters, a.outdir)
    print(f"S1 解析 {len(kws)} 条 | S2 聚类 {len(clusters)} 簇")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
