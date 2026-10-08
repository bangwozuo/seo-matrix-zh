# -*- coding: utf-8 -*-
"""
内链智能配对 —— 源/目标页面语义配对的确定性实现。

职责边界：
  本脚本只做确定性计算：条目解析、中文 2-gram 相似度、阈值分级、未匹配识别、落盘。
  锚文本措辞、插入位置的业务建议由模型按 prompt.txt 完成。

配对规则（与 prompt.txt 一致）：
  R1 相似度 = 共享 2-gram 数 ÷ 较短侧 2-gram 数
  R2 置信度：≥0.50 高 / ≥0.25 中 / ≥0.15 低（低于 0.15 不配对）
  R3 每个源条目只配 1 个最优目标；无达标目标进「未匹配项」

用法：
  python match_links.py --input ../examples/input.json --outdir out
  python match_links.py --demo --outdir out

产物：
  out/配对结果.csv    源/目标/匹配依据/置信度
  out/matching.json   机器可读结果
  out/配对报告.md     Markdown 映射表
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.dirname(HERE)

STOP_GRAM = {"怎么", "入门", "指南", "实战", "详解", "一文", "读懂", "附", "含"}


def parse_source(raw):
    """源集合：A1.《标题》 或编号行。"""
    entries = []
    for ln in str(raw).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r"^([A-Za-z]\d+)[.、:：]?\s*《(.+?)》", ln)
        if m:
            entries.append({"id": m.group(1), "title": m.group(2), "meta": ""})
            continue
        m = re.match(r"^([A-Za-z]\d+)[.、:：]?\s*(.+)$", ln)
        if m:
            entries.append({"id": m.group(1), "title": m.group(2).strip("《》"), "meta": ""})
    return entries


def parse_target(raw):
    """目标集合：B1. /path —— 描述 或 B1.《标题》——描述。"""
    entries = []
    for ln in str(raw).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r"^([A-Za-z]\d+)[.、:：]?\s*(.+)$", ln)
        if not m:
            continue
        rest = m.group(2)
        pm = re.match(r"(\S+)\s*[—–-]{1,2}\s*(.+)", rest)
        if pm and ("/" in pm.group(1) or "《" in pm.group(1)):
            path, desc = pm.group(1), pm.group(2)
        else:
            path, desc = "", rest
        title = desc
        tm = re.search(r"《(.+?)》", desc)
        if tm:
            title = tm.group(1)
        entries.append({"id": m.group(1), "path": path, "desc": desc, "title": title})
    return entries


def grams(text):
    """中文 2-gram + 英文单词小写。"""
    text = re.sub(r"[，。：；！？、（）()《》\s\-—,/]", "", str(text))
    zh = re.findall(r"[\u4e00-\u9fff]", text)
    g = {zh[i] + zh[i + 1] for i in range(len(zh) - 1)}
    g |= {w.lower() for w in re.findall(r"[A-Za-z]{2,}", text)}
    return {x for x in g if x not in STOP_GRAM}


def score(a_grams, b_grams):
    if not a_grams or not b_grams:
        return 0.0
    inter = a_grams & b_grams
    return len(inter) / min(len(a_grams), len(b_grams))


def level(s):
    if s >= 0.50:
        return "高"
    if s >= 0.25:
        return "中"
    if s >= 0.15:
        return "低"
    return ""


def match(sources, targets):
    rows, unmatched = [], []
    for s in sources:
        sg = grams(s["title"])
        best, best_sc = None, 0.0
        for t in targets:
            sc = score(sg, grams(t["title"] + " " + t["desc"]))
            if sc > best_sc:
                best, best_sc = t, sc
        lv = level(best_sc)
        if best is None or not lv:
            unmatched.append(f"{s['id']}.《{s['title']}》")
            continue
        inter = sg & grams(best["title"] + " " + best["desc"])
        rows.append({
            "源条目": f"{s['id']}.《{s['title']}》",
            "目标条目": f"{best['id']}. {best['path'] or best['title']}",
            "匹配依据": "共享词元：" + "、".join(sorted(inter)[:5]),
            "置信度": f"{lv}（{best_sc:.2f}，阈值 高≥0.50/中≥0.25/低≥0.15）",
            "_score": round(best_sc, 2),
        })
    rows.sort(key=lambda r: -r["_score"])
    for r in rows:
        r.pop("_score")
    return rows, unmatched


def suggestions(unmatched, targets):
    sug = []
    if unmatched:
        sug.append(f"未匹配 {len(unmatched)} 条：源标题与全部目标页 2-gram 相似度均 < 0.15，"
                   f"不要强行插入不相关链接（会拉低主题相关性）")
        sug.append("处置顺序：先为目标集合补 1 篇对应的支柱页（pillar page），再回填内链；"
                   "或把该源条目降级到站内搜索/标签聚合页")
    else:
        sug.append("全部源条目均已配对；建议每页内链出链 2-5 条，避免单页堆砌超过 100 条")
    sug.append(f"目标侧共 {len(targets)} 个可承接页；若某目标页被配对 ≥3 次，考虑分散到同主题次级页面")
    return sug


def write_outputs(sources, targets, rows, unmatched, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "配对结果.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["源条目", "目标条目", "匹配依据", "置信度"])
        w.writeheader()
        w.writerows(rows)
    files.append(p)

    js = {
        "summary": {"源条目": len(sources), "目标条目": len(targets),
                    "已配对": len(rows), "未匹配": len(unmatched)},
        "mapping": rows, "unmatched": unmatched,
        "suggestions": suggestions(unmatched, targets),
        "note": "配对与置信度由本脚本 2-gram 相似度计算；锚文本措辞由模型按 prompt.txt 完成",
    }
    p = os.path.join(outdir, "matching.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 映射结果", "",
          "| 源条目 | 目标条目 | 匹配依据 | 置信度 |", "|---|---|---|---|"]
    md += [f"| {r['源条目']} | {r['目标条目']} | {r['匹配依据']} | {r['置信度']} |" for r in rows]
    md += ["", "## 未匹配项", ""] + ([f"- {u}" for u in unmatched] or ["- （无）"])
    md += ["", "## 处理建议", ""] + [f"{i}. {s}" for i, s in enumerate(suggestions(unmatched, targets), 1)]
    p = os.path.join(outdir, "配对报告.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="内链智能配对（2-gram 相似度，确定性）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()

    src = os.path.join(ASSET_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    with open(src, encoding="utf-8") as f:
        cur = json.load(f)
    sources = parse_source(cur.get("source_set", ""))
    targets = parse_target(cur.get("target_set", ""))
    if not sources or not targets:
        print("[错误] source_set / target_set 解析为空：缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    rows, unmatched = match(sources, targets)
    files = write_outputs(sources, targets, rows, unmatched, a.outdir)
    print(f"源 {len(sources)} | 目标 {len(targets)} | 配对 {len(rows)} | 未匹配 {len(unmatched)}")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
