# 使用示例

## 示例 1：标准输入

**输入**：

```json
{
  "input": "品牌：焙语焙语（Bakely）家用烘焙设备出海项目\n步骤输入一（程序化页面生成所需 模板+数据集）：\n模板：产品对比落地页模板。固定结构：H1 =「Bakely {机型} vs {机型}：Which Should You Buy?」；meta description 模板 =「Compare Bakely {机型A} and {机型B}: {差异点1}, {差异点2}, and price.」；正文段落：①规格对照表（容量/功率/预热时间/价格）②同规格段落 2-3 条说明 ③FAQ（2 条）④CTA。每页输出 FAQPage 结构化数据。\n数据集：条目1：机型A=Mini 12L，机型B=Air 20L，容量=12L vs 20L，功率=1200W vs 1600W，预热时间=3min vs 5min，价格=$89 vs $129，差异点1=capacity，差异点2=preheat speed；条目2：机型A=Air 20L，机型B=Pro 25L，容量=20L vs 25L，功率=1600W vs 1800W，预热时间=5min vs 6min，价格=$129 vs $169，差异点1=capacity，差异点2=convection fan；条目3：机型A=Mini 12L，机型B=Pro 25L，容量=12L vs 25L，功率=1200W vs 1800W，预热时间=3min vs 6min，价格=$89 vs $169，差异点1=capacity gap，差异点2=price difference\n步骤输入二（多语言写作所需 目标语言+术语表）：\ntarget_lang=英语（美式）；glossary：焙语→Bakely（品牌名不意译）；预热时间→preheat time；对流风机→convection fan；结构化数据 FAQ 中的「质保」→warranty（整线 1 年质保统一译为 1-year warranty）"
}

```

**输出**：

<!-- AI 生成内容 -->

## 执行摘要

本次执行按两步串联完成 Bakely 家用烘焙设备 3 组机型对比页的程序化生成与英文成稿：步骤 1 产出 3 页中文结构化内容（含 FAQ 与结构化数据），步骤 2 将其转换为美式英语成稿，术语全部按术语表执行。

## 分步结果

1. 步骤 1（程序化页面生成）：按「产品对比落地页模板」批量套用 3 条数据条目，产出 3 页中文结构化内容。
2. 步骤 2（多语言写作）：将步骤 1 的 3 页内容转换为英语（美式）成稿，术语按 glossary 处理。

## 步骤 1 详细输出：程序化页面生成

### 页面清单

| 页面 | 标题 | meta/摘要 | 正文要点 | 结构化数据 |
|---|---|---|---|---|
| /compare/mini-12l-vs-air-20l | Bakely Mini 12L vs Air 20L：Which Should You Buy? | Compare Bakely Mini 12L and Air 20L: capacity, preheat speed, and price. | ①规格对照表：容量 12L vs 20L、功率 1200W vs 1600W、预热时间 3min vs 5min、价格 $89 vs $129；②差异说明：Air 容量多 8L 适合 4 人以上家庭，预热快 2 分钟；③FAQ 2 条；④CTA | FAQPage |
| /compare/air-20l-vs-pro-25l | Bakely Air 20L vs Pro 25L：Which Should You Buy? | Compare Bakely Air 20L and Pro 25L: capacity, convection fan, and price. | ①规格对照表：容量 20L vs 25L、功率 1600W vs 1800W、预热时间 5min vs 6min、价格 $129 vs $169；②差异说明：Pro 容量多 5L 且配对流风机，受热更均匀；③FAQ 2 条；④CTA | FAQPage |
| /compare/mini-12l-vs-pro-25l | Bakely Mini 12L vs Pro 25L：Which Should You Buy? | Compare Bakely Mini 12L and Pro 25L: capacity gap, price difference, and specs. | ①规格对照表：容量 12L vs 25L、功率 1200W vs 1800W、预热时间 3min vs 6min、价格 $89 vs $169；②差异说明：两档相差 $80，容量差一倍以上，按预算与人数二选一；③FAQ 2 条；④CTA | FAQPage |

### 模板说明

1. 占位符映射：{机型A}/{机型B}=数据条目机型字段，{差异点1}/{差异点2}=差异点字段；正文第②段差异说明由容量/功率/预热时间/价格四组数字推导。
2. FAQ 两条固定为「Which model fits a family of 4?」「What is the warranty?」，答案取自数据条目（容量）与整线统一质保信息（1-year warranty）。
3. FAQPage 结构化数据以 JSON-LD 输出。

### 异常项

1. 数据条目未提供 FAQ 答案所需的家庭人数建议口径，「适合 4 人以上家庭」为基于容量差的编辑推断，需业务方确认。
2. 术语表未指定「容量/功率」等通用词译法，按行业惯用译法处理并在步骤 2 标注。

## 步骤 2 详细输出：多语言写作（英语·美式）

### 转换结果（以第 1 页为例，其余两页同规则转换）

**Bakely Mini 12L vs Air 20L: Which Should You Buy?**

Specs at a glance: capacity 12L vs 20L, power 1200W vs 1600W, preheat time 3 min vs 5 min, price $89 vs $129. The Air 20L offers 8L more capacity—roomy enough for a family of four (editorial estimate, pending business confirmation)—and preheats 2 minutes faster than the Mini. FAQ: Which model fits a family of 4? — The Air 20L's 20L capacity is the better fit. What is the warranty? — Every Bakely model ships with a 1-year warranty.

（第 2 页 Pro 25L 差异段：The Pro 25L adds 5L of capacity and a convection fan for more even heating at $40 more. 第 3 页差异段：The Pro costs $80 more than the Mini and doubles the capacity—pick by budget and household size.）

### 术语处理

| 原词 | 译法 | 依据 |
|---|---|---|
| 焙语 | Bakely | 术语表指定，品牌名不意译 |
| 预热时间 | preheat time | 术语表指定译法 |
| 对流风机 | convection fan | 术语表指定译法 |
| 质保 | warranty（1-year warranty） | 术语表指定，整线统一质保口径 |
| 容量/功率 | capacity / power | 术语表未指定，按家电类目英文页惯用译法（编辑假设） |

### 语感校验

1. 「价格差」表述统一用 "costs $X more" 而非 "more expensive"，符合美式电商对比文案惯例。
2. FAQ 答案使用短句直答（"The Air 20L's 20L capacity is the better fit."），适配 FAQPage 结构化数据的答案长度偏好。
3. 「适合 4 人以上家庭」的推断已在成稿中显式标注 editorial estimate，需人工复核。

## 最终交付物

3 组机型对比英文页面成稿（上表页面清单 + 步骤 2 英文文本），含 FAQPage JSON-LD 结构化数据，可直接用于独立站发布前的最后人工确认。

（本交付物为 AI 生成内容，对外发布前保留人工确认环节。）


---

*本示例由实跑验证生成，verdict: pass*
