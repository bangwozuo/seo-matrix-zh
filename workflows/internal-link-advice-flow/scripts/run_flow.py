# -*- coding: utf-8 -*-
"""
内链建议工作流 —— 端到端编排脚本（与 SKILL.md 步骤链路一致）。

  S1 页面清单解析   解析源集合 A1.《标题》与目标集合 B1. 路径 —— 描述（确定性）
  S2 内链机会配对   中文 2-gram 相似度，阈值 高≥0.50 / 中≥0.25 / 低≥0.15（确定性）
  S3 建议清单落盘   配对建议.csv + 建议清单.md + flow.json

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

STOP_GRAM = {"怎么", "入门", "指南", "实战", "详解", "一文", "读懂", "附", "含"}


def load_input(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def s1_parse(text):
    """从同一文本里切出源集合与目标集合。"""
    src_seg, tgt_seg = [], []
    mode = None
    for ln in str(text).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if re.search(r"源集合|待加内链|新增.*文章", ln):
            mode = "src"
            continue
        if re.search(r"目标集合|已有页面|站内页面", ln):
            mode = "tgt"
            continue
        if re.match(r"^[A-Z]\d+\s*[=＝]", ln):
            mode = None
        (src_seg if mode == "src" else tgt_seg if mode == "tgt" else []).append(ln)
    return parse_source("\n".join(src_seg)), parse_target("\n".join(tgt_seg))


def parse_source(raw):
    entries = []
    for ln in str(raw).splitlines():
        ln = ln.strip()
        m = re.match(r"^([A-Za-z]\d+)[.、:：]?\s*《(.+?)》", ln)
        if m:
            entries.append({"id": m.group(1), "title": m.group(2)})
            continue
        m = re.match(r"^([A-Za-z]\d+)[.、:：]?\s*(.+)$", ln)
        if m:
            entries.append({"id": m.group(1), "title": m.group(2).strip("《》")})
    return entries


def parse_target(raw):
    entries = []
    for ln in str(raw).splitlines():
        ln = ln.strip()
        m = re.match(r"^([A-Za-z]\d+)[.、:：]?\s*(.+)$", ln)
        if not m:
            continue
        rest = m.group(2)
        pm = re.match(r"(\S+)\s*[—–-]{1,2}\s*(.+)", rest)
        path, desc = (pm.group(1), pm.group(2)) if pm else ("", rest)
        tm = re.search(r"《(.+?)》", desc)
        entries.append({"id": m.group(1), "path": path, "desc": desc,
                        "title": tm.group(1) if tm else desc})
    return entries


def grams(text):
    text = re.sub(r"[，。：；！？、（）()《》\s\-—,/]", "", str(text))
    zh = re.findall(r"[\u4e00-\u9fff]", text)
    g = {zh[i] + zh[i + 1] for i in range(len(zh) - 1)}
    g |= {w.lower() for w in re.findall(r"[A-Za-z]{2,}", text)}
    return {x for x in g if x not in STOP_GRAM}


def s2_match(sources, targets):
    rows, unmatched = [], []
    for s in sources:
        sg = grams(s["title"])
        best, best_sc = None, 0.0
        for t in targets:
            tg = grams(t["title"] + " " + t["desc"])
            sc = len(sg & tg) / min(len(sg), len(tg)) if sg and tg else 0.0
            if sc > best_sc:
                best, best_sc = t, sc
        if best is None or best_sc < 0.15:
            unmatched.append(f"{s['id']}.《{s['title']}》")
            continue
        lv = "高" if best_sc >= 0.50 else ("中" if best_sc >= 0.25 else "低")
        inter = sg & grams(best["title"] + " " + best["desc"])
        rows.append({"源条目": f"{s['id']}.《{s['title']}》",
                     "目标条目": f"{best['id']}. {best['path'] or best['title']}",
                     "锚文本建议": "、".join(sorted(inter)[:2]) or s["title"][:8],
                     "匹配依据": "共享词元：" + "、".join(sorted(inter)[:5]),
                     "置信度": f"{lv}（{best_sc:.2f}）"})
    rows.sort(key=lambda r: -float(re.search(r"(\d\.\d+)", r["置信度"]).group(1)))
    return rows, unmatched


def s3_suggestions(rows, unmatched, targets):
    sug = []
    high = [r for r in rows if r["置信度"].startswith("高")]
    mid = [r for r in rows if r["置信度"].startswith("中")]
    sug.append(f"高置信 {len(high)} 对：正文内插入描述性锚文本即可，优先第 2~4 自然段")
    if mid:
        sug.append(f"中置信 {len(mid)} 对：插入前人工确认相关性，避免主题漂移")
    hot = Counter(r["目标条目"] for r in rows)
    over = [k for k, v in hot.items() if v >= 3]
    if over:
        sug.append(f"被指向 ≥3 次的目标页 {'、'.join(over)}：分散到同主题次级页面，避免权重过度集中")
    if unmatched:
        sug.append(f"未匹配 {len(unmatched)} 条：补 1 篇对应支柱页后回填，或降级到标签聚合页")
    return sug


def write_outputs(sources, targets, rows, unmatched, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "配对建议.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["源条目", "目标条目", "锚文本建议", "匹配依据", "置信度"])
        w.writeheader()
        w.writerows(rows)
    files.append(p)

    summary = (f"源 {len(sources)} 篇 × 目标 {len(targets)} 页，配对 {len(rows)} 对"
               f"（高置信 {len([r for r in rows if r['置信度'].startswith('高')])} 对），未匹配 {len(unmatched)} 条")
    steps = [f"S1 页面清单解析：源 {len(sources)} / 目标 {len(targets)}",
             f"S2 内链机会配对：阈值 0.50/0.25/0.15，配对 {len(rows)} 对",
             f"S3 建议清单落盘：配对建议.csv + 建议清单.md + flow.json"]
    js = {"summary": summary, "steps": steps,
          "deliverable": {"mapping": rows, "unmatched": unmatched,
                          "suggestions": s3_suggestions(rows, unmatched, targets)},
          "note": "相似度与置信度由本脚本计算；锚文本最终措辞由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 映射结果", "",
          "| 源条目 | 目标条目 | 锚文本建议 | 匹配依据 | 置信度 |", "|---|---|---|---|---|"]
    md += [f"| {r['源条目']} | {r['目标条目']} | {r['锚文本建议']} | {r['匹配依据']} | {r['置信度']} |"
           for r in rows] or ["| - | - | - | - | - |"]
    md += ["", "## 未匹配项", ""] + ([f"- {u}" for u in unmatched] or ["- （无）"])
    md += ["", "## 处理建议", ""] + [f"{i}. {s}" for i, s in enumerate(s3_suggestions(rows, unmatched, targets), 1)]
    p = os.path.join(outdir, "建议清单.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="内链建议工作流（解析 → 配对 → 建议落盘）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    src = os.path.join(WF_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    cur = load_input(src)
    sources, targets = s1_parse(cur.get("input", ""))
    if not sources or not targets:
        print("[错误] 源/目标集合解析为空，缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    rows, unmatched = s2_match(sources, targets)
    files = write_outputs(sources, targets, rows, unmatched, a.outdir)
    print(f"S1 源 {len(sources)} / 目标 {len(targets)} | S2 配对 {len(rows)} 对 | 未匹配 {len(unmatched)}")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
