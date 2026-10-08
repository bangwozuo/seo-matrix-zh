# -*- coding: utf-8 -*-
"""
排名波动预警 —— 排名/点击/收录三项指标异动的确定性检测。

职责边界：
  本脚本只做确定性计算：指标解析、阈值判定、级别分级、落盘。
  归因方向（算法更新/内容过期/外链变动）由模型按 prompt.txt 完成。

默认判定规则（可用输入 rules 覆盖，与 prompt.txt 一致）：
  R1 关键词排名下滑 ≥5 位 → warning；≥10 位 → critical；上升不告警仅记录
  R2 自然点击量周环比下滑 ≥15% → warning；≥25% → critical
  R3 已收录页面变未收录 → critical
  R4 指标解析失败或规则未覆盖 → 进「需人工确认」

用法：
  python rank_alert.py --input ../examples/input.json --outdir out
  python rank_alert.py --demo --outdir out

产物：
  out/预警清单.csv    逐指标判定
  out/alerts.json     机器可读结果
  out/预警报告.md     Markdown 预警清单
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

DEFAULT_RULES = {"rank_drop_warn": 5, "rank_drop_crit": 10,
                 "click_drop_warn": 15.0, "click_drop_crit": 25.0}


def parse_rules(raw):
    rules = dict(DEFAULT_RULES)
    if not raw:
        return rules
    text = str(raw)
    m = re.search(r"下滑\s*[≥>=]+\s*(\d+)\s*位记\s*warning", text)
    if m:
        rules["rank_drop_warn"] = int(m.group(1))
    m = re.search(r"[≥>=]+\s*(\d+)\s*位记\s*critical", text)
    if m:
        rules["rank_drop_crit"] = int(m.group(1))
    m = re.search(r"周环比下滑\s*[≥>=]+\s*(\d+(?:\.\d+)?)\s*%?\s*记\s*warning", text)
    if m:
        rules["click_drop_warn"] = float(m.group(1))
    m = re.search(r"[≥>=]+\s*(\d+(?:\.\d+)?)\s*%?\s*记\s*critical", text)
    if m:
        rules["click_drop_crit"] = float(m.group(1))
    return rules


def _num(s):
    return float(str(s).replace(",", ""))


META_PAT = re.compile(r"监测日期|基线日期|站点[：:]|业务背景|对比基线")


def extract_lines(raw):
    """按「指标N：」或编号行切分指标文本，跳过元信息行。"""
    lines = []
    for ln in str(raw).splitlines():
        ln = ln.strip()
        if not ln or META_PAT.search(ln):
            continue
        m = re.match(r"^(指标\d+|\d+[.、)])\s*[：:]?\s*(.+)$", ln)
        if m:
            lines.append((m.group(1).rstrip("：:.、)"), m.group(2)))
        else:
            lines.append((f"行{len(lines) + 1}", ln))
    return lines


def parse_rank(text):
    m = re.search(r"第\s*(\d+)\s*位", text)
    return int(m.group(1)) if m else None


def keyword_of(text):
    m = re.search(r"[「『]([^」』]{1,30})[」』]", text)
    return m.group(1) if m else None


def baseline_rank_for(kw, baseline_text):
    """在基线全文里定位「关键词」后面的第一个名次。"""
    if not kw:
        return None
    m = re.search(re.escape(kw) + r"」?[^\n；;]{0,40}?第\s*(\d+)\s*位", baseline_text)
    return int(m.group(1)) if m else None


def baseline_count_for(baseline_text):
    """基线里的点击量：优先取含「点击」的片段，否则取最后一个「N 次」。"""
    seg = re.search(r"点击[^\n；;]{0,40}?([\d,，]+(?:\.\d+)?)\s*次", baseline_text)
    if seg:
        return _num(seg.group(1))
    all_counts = re.findall(r"([\d,，]+(?:\.\d+)?)\s*次", baseline_text)
    return _num(all_counts[-1]) if all_counts else None


def parse_count(text):
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*次", text)
    return _num(m.group(1)) if m else None


def parse_index_state(text):
    if "未收录" in text:
        return "未收录"
    if "已收录" in text or "收录" in text:
        return "已收录"
    return None


def detect(metrics_lines, baseline_text, rules):
    """逐指标判定：排名按关键词对齐基线；点击量/收录按全文定位。"""
    alerts, no_alert, need_confirm = [], [], []
    for name, mtext in metrics_lines:
        kw = keyword_of(mtext)
        cur_rank = parse_rank(mtext)
        base_rank = baseline_rank_for(kw, baseline_text) if cur_rank is not None else None
        if cur_rank is not None and base_rank is not None:
            delta = cur_rank - base_rank  # 正数=下滑
            label = kw or name
            if delta >= rules["rank_drop_crit"]:
                alerts.append({"指标": f"{label}（自然排名）", "当前值": f"第 {cur_rank} 位",
                               "基线": f"第 {base_rank} 位", "偏离": f"下滑 {delta} 位",
                               "级别": "critical", "判定规则": f"下滑 ≥{rules['rank_drop_crit']} 位记 critical"})
            elif delta >= rules["rank_drop_warn"]:
                alerts.append({"指标": f"{label}（自然排名）", "当前值": f"第 {cur_rank} 位",
                               "基线": f"第 {base_rank} 位", "偏离": f"下滑 {delta} 位",
                               "级别": "warning", "判定规则": f"下滑 ≥{rules['rank_drop_warn']} 位记 warning"})
            else:
                trend = f"上升 {abs(delta)} 位" if delta < 0 else "持平"
                no_alert.append(f"{label}：第 {base_rank} → {cur_rank} 位（{trend}，上升不告警仅记录）")
            continue

        if "点击" in mtext:
            cur_cnt = parse_count(mtext)
            base_cnt = baseline_count_for(baseline_text)
            if cur_cnt is not None and base_cnt is not None and base_cnt:
                drop = (base_cnt - cur_cnt) / base_cnt * 100
                label = kw or "自然搜索点击量"
                if drop >= rules["click_drop_crit"]:
                    alerts.append({"指标": f"{label}（自然点击量）", "当前值": f"{cur_cnt:,.0f} 次",
                                   "基线": f"{base_cnt:,.0f} 次", "偏离": f"下滑 {drop:.1f}%",
                                   "级别": "critical",
                                   "判定规则": f"周环比下滑 ≥{rules['click_drop_crit']:.0f}% 记 critical"})
                elif drop >= rules["click_drop_warn"]:
                    alerts.append({"指标": f"{label}（自然点击量）", "当前值": f"{cur_cnt:,.0f} 次",
                                   "基线": f"{base_cnt:,.0f} 次", "偏离": f"下滑 {drop:.1f}%",
                                   "级别": "warning",
                                   "判定规则": f"周环比下滑 ≥{rules['click_drop_warn']:.0f}% 记 warning"})
                else:
                    no_alert.append(f"{label}：{base_cnt:,.0f} → {cur_cnt:,.0f} 次"
                                    f"（{'上升' if drop < 0 else '下滑'} {abs(drop):.1f}%，未达阈值）")
                continue

        cur_idx = parse_index_state(mtext)
        if cur_idx:
            seg = baseline_text
            if kw:
                km = re.search(re.escape(kw) + r"」?[^\n]{0,60}", baseline_text)
                seg = km.group(0) if km else seg
            base_idx = parse_index_state(seg) or ("已收录" if "已收录" in baseline_text else None)
            if base_idx and cur_idx != base_idx:
                alerts.append({"指标": f"{kw or name}（索引状态）", "当前值": cur_idx, "基线": base_idx,
                               "偏离": f"{base_idx} → {cur_idx}", "级别": "critical",
                               "判定规则": "已收录变未收录记 critical"})
            elif base_idx:
                no_alert.append(f"{kw or name}：索引状态维持 {cur_idx}")
                continue

        need_confirm.append(f"{kw or name}：当前「{mtext[:40]}」—— 数值不完整或基线缺失，需人工确认")
    return alerts, no_alert, need_confirm


def write_outputs(alerts, no_alert, need_confirm, rules, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = []
    p = os.path.join(outdir, "预警清单.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["指标", "当前值", "基线", "偏离", "级别", "判定规则"])
        w.writeheader()
        if alerts:
            w.writerows(alerts)
        else:
            w.writerow({"指标": "（无告警）", "当前值": "", "基线": "", "偏离": "", "级别": "", "判定规则": ""})
    files.append(p)

    js = {"rules": rules, "alerts": alerts, "no_alert": no_alert, "need_confirm": need_confirm,
          "summary": {"预警条数": len(alerts),
                      "critical": len([x for x in alerts if x["级别"] == "critical"]),
                      "warning": len([x for x in alerts if x["级别"] == "warning"]),
                      "正常项": len(no_alert), "待确认项": len(need_confirm)},
          "note": "阈值判定由本脚本完成；归因方向与处置建议由模型按 prompt.txt 完成"}
    p = os.path.join(outdir, "alerts.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    files.append(p)

    md = ["<!-- AI 生成内容 -->", "", "## 预警清单", "",
          "| # | 指标 | 当前值 | 基线 | 偏离 | 级别 | 判定规则 |", "|---|---|---|---|---|---|---|"]
    md += [f"| {i} | {a['指标']} | {a['当前值']} | {a['基线']} | {a['偏离']} | {a['级别']} | {a['判定规则']} |"
           for i, a in enumerate(alerts, 1)] or ["| - | （无告警） | | | | | |"]
    md += ["", "## 未命中项", ""] + [f"- {x}" for x in no_alert]
    md += ["", "## 需人工确认", ""] + ([f"- {x}" for x in need_confirm] or ["- （无）"])
    p = os.path.join(outdir, "预警报告.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="排名波动预警（阈值判定，确定性）")
    ap.add_argument("--input", help="输入 JSON 路径")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()

    src = os.path.join(ASSET_DIR, "examples", "input.json") if a.demo else a.input
    if not src or not os.path.exists(src):
        ap.error("需提供 --input 或 --demo")
    with open(src, encoding="utf-8") as f:
        cur = json.load(f)
    if not cur.get("metrics"):
        print("[错误] metrics 为空：缺数据不补造。", file=sys.stderr)
        sys.exit(3)
    rules = parse_rules(cur.get("rules", ""))
    metrics_lines = extract_lines(cur["metrics"])
    baseline_text = str(cur.get("baseline", "") or "")
    alerts, no_alert, need_confirm = detect(metrics_lines, baseline_text, rules)
    files = write_outputs(alerts, no_alert, need_confirm, rules, a.outdir)
    print(f"指标 {len(metrics_lines)} | 预警 {len(alerts)}"
          f"（critical {len([x for x in alerts if x['级别'] == 'critical'])} / "
          f"warning {len([x for x in alerts if x['级别'] == 'warning'])}）｜正常 {len(no_alert)}｜待确认 {len(need_confirm)}")
    for fp in files:
        print(" 产物:", fp, f"({os.path.getsize(fp) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
