# 多语言写作

## 元信息

| 字段 | 值 |
|------|-----|
| ID | `de_dev_03_sk05` |
| 类型 | **`atomic`（原子技能）** |
| 所属员工 | SEO 架构师 |
| 能力族 | — |
| 复杂度 | `S` |
| 阶段 | `P1` |
| 复用度 | 高（出海通用） |
| 资产形态 | 纯提示词（无运行时依赖） |

## 能力描述

中英等多语言 SEO 成稿

## 输入规格

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | ✅ | 待处理的原始内容 |
| `target_lang` | string | ✅ | 目标语言 |

## 输出规格

多语言转换

- `translated`：目标语言的完整文本
- `glossary_used`：专有名词的处理方式
- `tone_check`：文化差异与语感调整说明

## 使用步骤

### 方式一：直接使用（最快）

1. 打开任意支持自定义提示词的 AI 工具
2. 复制 `prompt.txt` 的**全部内容**作为系统提示词
3. 按上方「输入规格」提供数据
4. 得到符合「输出规格」的结果

### 方式二：在主流平台导入

| 平台 | 导入方式 |
|------|---------|
| **Coze / 扣子** | 新建 Bot → 人设与回复逻辑 → 粘贴 `prompt.txt` |
| **WorkBuddy** | 新建 Skill → 填入 `prompt.txt` 内容 |
| **Dify** | 新建应用 → 提示词编排 → 粘贴 `prompt.txt` |
| **Claude** | 新建 Project → Instructions → 粘贴 `prompt.txt` |
| **ChatGPT** | 新建 GPT → Instructions → 粘贴 `prompt.txt` |

## 边界（不做的事）

- ❌ 编造数据、案例或效果承诺
- ❌ 使用违反《广告法》的极限词
- ❌ 生成诱导好评、刷量、删差评等违规内容
- ❌ 执行或建议任何绕过平台规则的操作
- ❌ 涉及资金操作或代替用户做最终决策
- ❌ 处理超出本职能力范围的请求（应明确说明并建议转其他技能）

## 调用示例

**输入**：

```json
{
  "content": "云饮智能保温杯 Pro 采用 316L 医用级不锈钢内胆，真空锁温层可实现 12 小时保温、24 小时保冷。杯盖内置温度显示屏，轻触即可读取当前水温，避免儿童烫伤。配套的云饮 App 支持每日饮水目标设定与提醒，并通过蓝牙同步饮水记录。整机 IPX7 防水，续航 30 天，建议零售价 299 元，提供 1 年质保。",
  "target_lang": "英语（美式）",
  "glossary": "云饮→CloudSip（品牌名，注册商标不意译）；云饮智能保温杯 Pro→CloudSip Smart Thermal Bottle Pro；316L 医用级不锈钢→316L medical-grade stainless steel；IPX7 防水→IPX7 water resistance"
}

```

**输出**：

```markdown
<!-- AI 生成内容 -->

## 转换结果

The CloudSip Smart Thermal Bottle Pro features a 316L medical-grade stainless steel inner wall, with a vacuum insulation layer that keeps drinks hot for 12 hours and cold for 24 hours. The lid has a built-in temperature display—just a light touch shows the current water temperature, helping prevent scald injuries to children. The companion CloudSip app lets users set daily hydration goals and reminders, and syncs hydration records over Bluetooth. The bottle carries an IPX7 water resistance rating, with a 30-day battery life. Suggested retail price is $42 (RMB 299), and it comes with a 1-year warranty.

## 术语处理

| 原词 | 译法 | 依据 |
|---|---|---|
| 云饮 | CloudSip | 术语表指定译法，注册商标不意译 |
| 云饮智能保温杯 Pro | CloudSip Smart Thermal Bottle Pro | 术语表指定 + 产品线命名惯例（Pro 保留原文） |
| 316L 医用级不锈钢 | 316L medical-grade stainless steel | 术语表指定译法，行业标准材质表述 |
| IPX7 防水 | IPX7 water resistance | 术语表指定，IP 等级为国际通用代码 |
| 299 元 | $42 (RMB 299) | 目标市场为美式英语读者，按 1 USD ≈ 7.1 CMB 换算并保留原币标注；此为编辑假设，需人工复核汇率 |

## 语感校验

1. 原文「轻触即可读取」译为 "just a light touch shows"，避免直译 "read the temperature" 造成的生硬感；美式消费电子文案惯用动作导向表述。
2. 「儿童烫伤」在美式语境下处理为 "scald injuries to children"，比直译 "burn children" 更贴合产品安全类文案的措辞习惯。
3. 价格换算属于编辑假设（原文未给美元价），正式发布前需由业务方确认官方美元定价。
4. 「1 年质保」译为 "comes with a 1-year warranty"，采用美式电商文案常见搭配，未使用生造的 "quality guarantee" 表述。


```


## 所属工作流

- 多语言文章产出

## 合规声明

- 本技能输出为 **AI 辅助生成内容**，交付前必须经人工审核
- 请按所在平台要求完成 AI 生成内容标识
- 涉及专业领域（法律 / 税务 / 医疗）的内容仅作参考，不构成专业意见

---

*本技能遵循 [bangwozuo 数字员工资产规范](https://github.com/bangwozuo/digital-employee-spec) v3.0*
