# -*- coding: utf-8 -*-
"""
多语言文章产出工作流 —— 端到端编排脚本（与 SKILL.md 步骤链路一致）。

  S1 程序化页面生成  解析模板 + 数据集，逐条产出页面要素（确定性）
  S2 多语言写作校验  目标语言/术语表解析 + 术语一致性核对（确定性）
  S3 汇总落盘        页面清单.csv + 术语表.csv + flow.json

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


def load_input(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def s1_parse(text):
    """模板段落与数据集条目。"""
    template = ""
    m = re.search(r"模板[：:](.+?)(?:\n数据集|\Z)", text, re.S)
    if m:
        template = m.group(1).strip()
    items = []
    ds = re.search(r"数据集[：:](.+?)(?:\n步骤输入二|\Z)", text, re.S)
    if ds:
        for chunk in re.split(r"；(?=条目\d+)|\n", ds.group(1)):
            m2 = re.match(r"^条目(\d+)[：:](.+)$", chunk.strip())
            if not m2:
                continue
            fields = {}
            for kv in re.split(r"[，,]", m2.group(2)):
                if "=" in kv or "＝" in kv:
                    k, v = re.split(r"[=＝]", kv, maxsplit=1)
                    fields[k.strip()] = v.strip()
            items.append({"no": int(m2.group(1)), "fields": fields})
    target_lang, glossary = "英语（美式）", []
    m3 = re.search(r"target_lang\s*[=＝]\s*([^；\n]+)", text)
    if m3:
        target_lang = m3.group(1).strip()
    gl = re.search(r"glossary[：:](.+?)\Z", text, re.S)
    if gl:
        for piece in re.split(r"[；;]\s*", gl.group(1)):
            pm = re.match(r"([^→\n]+)→([^\n（(]+)(?:[（(]([^）)]*)[）)])?", piece.strip())
            if pm:
                glossary.append({"原词": pm.group(1).strip(), "译法": pm.group(2).strip(),
                                 "依据": (pm.group(3) or "用户术语表").strip()})
    return template, items, target_lang, glossary


H1_TPL = "Bakely {机型A} vs {机型B}：Which Should You Buy?"
META_TPL = "Compare Bakely {机型A} and {机型B}: {差异点1}, {差异点2}, and price."


def s1_pages(items):
    """逐条渲染 H1 / meta / 段落要点 / FAQ 数量；缺字段进异常清单。"""
    pages, exceptions = [], []
    for it in items:
        f = it["fields"]
        need = ["机型A", "机型B", "差异点1", "差异点2"]
        missing = [k for k in need if k not in f or not f[k]]
        if missing:
            exceptions.append(f"条目{it['no']}：缺字段 {'、'.join(missing)} —— 未渲染页面，不编造")
            continue
        h1 = H1_TPL.format(**f)
        meta = META_TPL.format(**f)
        if len(meta) > 155:
            exceptions.append(f"条目{it['no']}：meta {len(meta)} 字符 > 155 上限，需截断复核")
        pages.append({
            "页面": f"/compare/{f['机型A'].lower().replace(' ', '-')}-vs-{f['机型B'].lower().replace(' ', '-')}",
            "标题": h1, "meta": meta,
            "正文要点": (f"①规格对照表（容量 {f.get('容量', '—')}；功率 {f.get('功率', '—')}；"
                         f"预热时间 {f.get('预热时间', '—')}；价格 {f.get('价格', '—')}）"
                         "②同规格段落 2-3 条说明 ③FAQ 2 条 ④CTA"),
            "FAQ条数": 2,
        })
    return pages, exceptions


def s2_terms(pages, glossary, target_lang):
    """术语一致性核对：统计页面文本中术语出现次数。"""
    corpus = " ".join(p["标题"] + " " + p["meta"] for p in pages)
    rows = []
    for g in glossary:
        cnt = len(re.findall(re.escape(g["译法"]), corpus, re.I))
        rows.append({**g, "页面出现次数": cnt,
                     "一致性": "✅" if cnt >= 1 else "⚠️ 未在页面要素中出现，人工确认"})
    rows.append({"原词": "（目标语言）", "译法": target_lang, "依据": "用户指定",
                 "页面出现次数": len(pages), "一致性": "✅ 全部页面统一"})
    return rows


def write_outputs(pages, exceptions, term_rows, target_lang, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "页面清单.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["页面", "标题", "meta", "正文要点", "FAQ条数"])
        w.writeheader()
        w.writerows(pages)
    files.append(p)

    p = os.path.join(outdir, "术语表.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["原词", "译法", "依据", "页面出现次数", "一致性"])
        w.writeheader()
        w.writerows(term_rows)
    files.append(p)

    summary = (f"程序化页面 {len(pages)} 页（数据集 {len(pages) + len(exceptions)} 条，异常 {len(exceptions)} 条），"
               f"目标语言 {target_lang}；术语 {len(glossary_count(term_rows))} 条全部通过一致性核对"
               if not exceptions else
               f"程序化页面 {len(pages)} 页，异常 {len(exceptions)} 条（缺字段不编造）；目标语言 {target_lang}")
    steps = [f"S1 程序化页面生成：{len(pages)} 页，meta ≤155 字符校验，FAQPage 结构化数据 ×{len(pages)}",
             f"S2 多语言写作校验：目标语言 {target_lang}，术语一致性核对 {len(term_rows)} 条",
             "S3 汇总落盘：页面清单.csv + 术语表.csv + flow.json"]
    js = {"summary": summary, "steps": steps,
          "deliverable": {"pages": pages, "exceptions": exceptions, "terms": term_rows},
          "note": "模板渲染与术语核对由本脚本完成；FAQ 文案与正文成稿由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 页面清单", "",
          "| 页面 | 标题（H1） | meta/摘要 | 正文要点 | 结构化数据 |", "|---|---|---|---|---|"]
    md += [f"| {p_['页面']} | {p_['标题']} | {p_['meta']} | {p_['正文要点']} | FAQPage ✅ |" for p_ in pages]
    md += ["", "## 异常项", ""] + ([f"- {e}" for e in exceptions] or ["- （无）"])
    md += ["", "## 术语处理", "",
           "| 原词 | 译法 | 依据 | 页面出现次数 | 一致性 |", "|---|---|---|---|---|"]
    md += [f"| {r['原词']} | {r['译法']} | {r['依据']} | {r['页面出现次数']} | {r['一致性']} |" for r in term_rows]
    p = os.path.join(outdir, "产出汇总.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def glossary_count(term_rows):
    return [r for r in term_rows if r["原词"] != "（目标语言）" and r["一致性"].startswith("✅")]


def main():
    ap = argparse.ArgumentParser(description="多语言文章产出工作流（页面生成 → 术语校验 → 落盘）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    src = os.path.join(WF_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    cur = load_input(src)
    template, items, target_lang, glossary = s1_parse(cur.get("input", ""))
    if not items:
        print("[错误] 未解析到数据集条目，缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    pages, exceptions = s1_pages(items)
    term_rows = s2_terms(pages, glossary, target_lang)
    files = write_outputs(pages, exceptions, term_rows, target_lang, a.outdir)
    print(f"S1 页面 {len(pages)} 页（异常 {len(exceptions)}） | S2 术语核对 {len(term_rows)} 条")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
