# -*- coding: utf-8 -*-
"""
收录与排名监控工作流 —— 端到端编排脚本（与 SKILL.md 步骤链路一致）。

  S1 监测数据解析   排名 / 点击量 / 索引状态三行类指标（确定性）
  S2 阈值判定       下滑 ≥5 位 warning、≥10 位 critical；点击 ≥15%/25%；
                    已收录变未收录 critical（同 rank-volatility-alert 规则）
  S3 更新建议落盘   预警清单.csv + 更新建议.md + flow.json

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

META_PAT = re.compile(r"监测日期|基线日期|站点[：:]|业务背景|对比基线")


def load_input(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_rules(raw):
    rules = {"rank_warn": 5, "rank_crit": 10, "click_warn": 15.0, "click_crit": 25.0}
    text = str(raw or "")
    m = re.search(r"下滑\s*[≥>=]+\s*(\d+)\s*位记\s*warning", text)
    if m:
        rules["rank_warn"] = int(m.group(1))
    m = re.search(r"[≥>=]+\s*(\d+)\s*位记\s*critical", text)
    if m:
        rules["rank_crit"] = int(m.group(1))
    m = re.search(r"周环比下滑\s*[≥>=]+\s*(\d+(?:\.\d+)?)", text)
    if m:
        rules["click_warn"] = float(m.group(1))
    m = re.search(r"[≥>=]+\s*(\d+(?:\.\d+)?)\s*%?\s*记\s*critical", text)
    if m:
        rules["click_crit"] = float(m.group(1))
    return rules


def s1_parse(cur):
    text = str(cur.get("input", ""))
    rules = parse_rules(cur.get("input", ""))
    metrics, baseline = [], ""
    seg = None
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if re.search(r"排名（当前 vs 基线）|关键词排名", ln):
            seg = "metrics"
            continue
        if ln.startswith("自然点击量") or "自然点击量" in ln and seg == "metrics":
            metrics.append(ln)
            seg = None
            continue
        if "对比基线日期" in ln:
            seg = None
        if seg == "metrics" and re.match(r"^\d+[.、)]", ln):
            metrics.append(ln)
        if "vs 第" in ln and "位" in ln and not re.match(r"^\d+[.、)]", ln):
            baseline = ln  # 基线内嵌在「当前 vs 基线」行
    # 本仓输入格式：每行「N. 「词」：第 X 位 vs 第 Y 位」
    rows = []
    for ln in metrics:
        m = re.match(r"^(\d+)[.、)]\s*[「『]([^」』]+)[」』][：:]?\s*第\s*(\d+)\s*位\s*vs\s*第\s*(\d+)\s*位", ln)
        if m:
            rows.append({"idx": int(m.group(1)), "kw": m.group(2),
                         "cur": int(m.group(3)), "base": int(m.group(4))})
    clicks = re.search(r"自然点击量[^\n]*?([\d,，]+)\s*次\s*vs\s*基线期[^\n]*?([\d,，]+)\s*次", text)
    lost = re.findall(r"(/[^\s（(]+)[^\n]*?当前显示未收录", text)
    return rows, clicks, lost, rules


def s2_detect(rows, clicks, lost, rules):
    alerts, records = [], []
    for r in rows:
        delta = r["cur"] - r["base"]
        if delta >= rules["rank_crit"]:
            alerts.append({"kw": r["kw"], "cur": r["cur"], "base": r["base"],
                           "delta": delta, "level": "critical",
                           "rule": f"下滑 ≥{rules['rank_crit']} 位记 critical"})
        elif delta >= rules["rank_warn"]:
            alerts.append({"kw": r["kw"], "cur": r["cur"], "base": r["base"],
                           "delta": delta, "level": "warning",
                           "rule": f"下滑 ≥{rules['rank_warn']} 位记 warning"})
        else:
            trend = f"下滑 {abs(delta)} 位，未达阈值" if delta > 0 else ("上升" if delta < 0 else "持平")
            records.append(f"「{r['kw']}」第 {r['base']} → {r['cur']} 位（{trend}，仅记录）")
    click_alert = None
    if clicks:
        cur, base = int(clicks.group(1).replace(",", "")), int(clicks.group(2).replace(",", ""))
        drop = (base - cur) / base * 100 if base else 0
        if drop >= rules["click_crit"]:
            click_alert = {"level": "critical", "drop": round(drop, 1), "cur": cur, "base": base}
        elif drop >= rules["click_warn"]:
            click_alert = {"level": "warning", "drop": round(drop, 1), "cur": cur, "base": base}
        else:
            records.append(f"自然点击量 {base:,} → {cur:,} 次（下滑 {drop:.1f}%，未达阈值）")
    return alerts, click_alert, [f"{u} 已收录变未收录" for u in lost], records


def suggest(alerts, click_alert, lost):
    sug = []
    for a in alerts:
        if a["level"] == "critical":
            sug.append(f"「{a['kw']}」下滑 {a['delta']} 位：核对站长平台算法公告时间线与该页面近期改动（标题/内链/外链）")
        else:
            sug.append(f"「{a['kw']}」下滑 {a['delta']} 位：检查 SERP 是否被新形态（精选摘要/视频）挤占，再决定是否改稿")
    if click_alert:
        sug.append(f"点击量周环比下滑 {click_alert['drop']}%：先核对收录量与曝光量是否同步下滑，定位是流量入口问题还是点击率问题")
    for u in lost:
        sug.append(f"{u}：立即排查 noindex/404/重定向链，恢复收录优先于改内容")
    return sug or ["全部指标未触发告警阈值，维持现有排产，下一监测周期（建议 7 天后）复扫"]


def write_outputs(alerts, click_alert, lost, records, rules, n_rows, has_clicks, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "预警清单.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["指标", "当前值", "基线", "偏离", "级别", "判定规则"])
        w.writeheader()
        for a in alerts:
            w.writerow({"指标": f"「{a['kw']}」自然排名", "当前值": f"第 {a['cur']} 位",
                        "基线": f"第 {a['base']} 位", "偏离": f"下滑 {a['delta']} 位",
                        "级别": a["level"], "判定规则": a["rule"]})
        if click_alert:
            w.writerow({"指标": "自然点击量（7 日）", "当前值": f"{click_alert['cur']:,} 次",
                        "基线": f"{click_alert['base']:,} 次", "偏离": f"下滑 {click_alert['drop']}%",
                        "级别": click_alert["level"],
                        "判定规则": f"周环比下滑 ≥{rules['click_warn']:.0f}% warning / ≥{rules['click_crit']:.0f}% critical"})
        for u in lost:
            w.writerow({"指标": u, "当前值": "未收录", "基线": "已收录", "偏离": "收录丢失",
                        "级别": "critical", "判定规则": "已收录变未收录记 critical"})
    files.append(p)

    n_crit = len([a for a in alerts if a["level"] == "critical"]) + len(lost) + \
             (1 if click_alert and click_alert["level"] == "critical" else 0)
    n_warn = len([a for a in alerts if a["level"] == "warning"]) + \
             (1 if click_alert and click_alert["level"] == "warning" else 0)
    summary = (f"预警 {n_crit + n_warn} 条（critical {n_crit} / warning {n_warn}），"
               f"未命中 {len(records)} 项；判定规则：下滑 ≥{rules['rank_warn']} 位 warning、"
               f"≥{rules['rank_crit']} 位 critical、点击 ≥{rules['click_warn']:.0f}%/{rules['click_crit']:.0f}%、收录丢失 critical")
    steps = [f"S1 监测数据解析：排名 {n_rows} 组、点击量 {'1 组' if has_clicks else '0 组'}、收录异常 {len(lost)} 处",
             f"S2 阈值判定：预警 {n_crit + n_warn} 条，未命中 {len(records)} 项",
             "S3 更新建议落盘：预警清单.csv + 更新建议.md + flow.json"]
    js = {"summary": summary, "steps": steps,
          "deliverable": {"alerts": alerts, "click_alert": click_alert,
                          "index_lost": lost, "no_alert": records,
                          "suggestions": suggest(alerts, click_alert, lost)},
          "note": "阈值判定由本脚本完成；归因与处置决策由模型按 prompt.txt 完成并经人工复核"}
    p = os.path.join(outdir, "flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 预警清单", "",
          "| 指标 | 当前值 | 基线 | 偏离 | 级别 | 判定规则 |", "|---|---|---|---|---|---|"]
    for a in alerts:
        md.append(f"| 「{a['kw']}」自然排名 | 第 {a['cur']} 位 | 第 {a['base']} 位 | "
                  f"下滑 {a['delta']} 位 | {a['level']} | {a['rule']} |")
    if click_alert:
        md.append(f"| 自然点击量（7 日） | {click_alert['cur']:,} 次 | {click_alert['base']:,} 次 | "
                  f"下滑 {click_alert['drop']}% | {click_alert['level']} | 周环比阈值 |")
    for u in lost:
        md.append(f"| {u} | 未收录 | 已收录 | 收录丢失 | critical | 收录丢失即 critical |")
    md += ["", "## 未命中项", ""] + [f"- {x}" for x in records] or ["- （无）"]
    md += ["", "## 内容更新建议", ""] + [f"{i}. {s}" for i, s in enumerate(suggest(alerts, click_alert, lost), 1)]
    p = os.path.join(outdir, "更新建议.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="收录与排名监控工作流（解析 → 阈值判定 → 建议落盘）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    src = os.path.join(WF_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    cur = load_input(src)
    rows, clicks, lost, rules = s1_parse(cur)
    if not rows and not clicks and not lost:
        print("[错误] 未解析到监测数据，缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    alerts, click_alert, lost_alerts, records = s2_detect(rows, clicks, lost, rules)
    files = write_outputs(alerts, click_alert, lost_alerts, records, rules, len(rows), bool(clicks), a.outdir)
    print(f"S1 排名 {len(rows)} 组 | S2 预警 {len(alerts) + len(lost_alerts) + (1 if click_alert else 0)} 条")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
