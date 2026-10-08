# SEO 架构师

> **出海独立站"调研→写作→发布→监控"的 SEO 全链路闭环助理**

![SEO 架构师 · 动态演示](docs/assets/hero.gif)

*▲ 实时演示（自动循环）· [▶ 观看完整版合集视频](docs/demo.mp4)*


[![Stage](https://img.shields.io/badge/stage-P1-orange)](https://github.com/bangwozuo)
[![Asset](https://img.shields.io/badge/asset-prompt--only-blueviolet)](#资产形态)
[![NoKey](https://img.shields.io/badge/API%20Key-not%20required-success)](#资产形态)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

---

## 它是谁

面向 **OPC** 的数字员工资产包。

| 项目 | 内容 |
|------|------|
| 目标用户 | 依赖 Google SEO 获客的出海工具站/SaaS 开发者（约占群体 1/3） |
| 交付物 | 月均产出 SEO 文章 ≥8 篇；目标词 90 天内进入 Top20 比例；自然搜索流量环比 |
| 技能数 | 7 |
| 工作流数 | 6 |
| 旧名存档 | `SEO 内容矩阵助理（独立站增长助理）` |

---

## 资产形态

**纯提示词资产** —— 这是理解本仓库的关键：

| 特性 | 说明 |
|------|------|
| ✅ 无需 API Key | 一个 Key 都不需要 |
| ✅ 无需部署 | 没有服务端，没有脚本 |
| ✅ 无需依赖 | 克隆后用文本编辑器就能看 |
| ✅ 平台无关 | 粘贴到任何 AI 工具即可使用 |
| ✅ 用户自备算力 | 模型来自你自己的订阅 |

---

## 快速开始

```text
1. 打开 skills/keyword-cluster/prompt.txt
2. 全文复制
3. 粘贴到你常用的 AI 工具（Coze / WorkBuddy / Dify / Claude / ChatGPT）
4. 按 SKILL.md 的输入规格提供数据
```

就这四步。完整指引见 [使用手册](docs/04-usage.md)。

---

## 仓库结构

```text
seo-matrix-zh/
├── README.md / employee.md / package.yaml     # 入口与 12 字段定义卡
├── docs/01~07                                 # 员工级文档（架构/流程/场景/手册/示例/录像/测试）
├── skills/                                    # 7 个原子技能
│   └── <skill>/
│       ├── README.md  SKILL.md  prompt.txt  schema.json  examples/
│       └── docs/                              # 该技能自己的 10 项文档 + 配图
├── workflows/                                 # 6 条工作流（复合技能）
│   └── <workflow>/
│       ├── README.md  SKILL.md  prompt.txt  schema.json  examples/
│       └── docs/                              # 该工作流自己的 10 项文档 + 配图
├── knowledge/                                 # RAG wiki 知识库
│   ├── README.md  RAG-接入指南.md  template.md
│   └── wiki/(index.md, _template.md, entries/)
├── connectors/                                # 连接器说明 + 合规红线
├── quality/                                   # 效果基线与追踪日志
└── tests/                                     # 资产校验测试（离线，无需密钥）
```

### 每个技能 / 工作流自带的 docs

| 文档 | 内容 |
|------|------|
| `README.md` | 资产速览与快速开始 |
| `docs/01-usage-manual.md` | 安装使用手册 |
| `docs/02-architecture.md` | 业务架构图 |
| `docs/03-flow.md` | 流程图（Mermaid + 配图） |
| `docs/04-examples.md` | 使用示例 |
| `docs/05-media.md` | 截图和录屏（清单 + 分镜脚本） |
| `docs/06-scenarios.md` | 使用场景（适用 / 不适用） |
| `docs/07-audience.md` | 用户群体 |
| `docs/08-value.md` | 解决问题与价值 |
| `docs/09-test-report.md` | 测试报告 |
| `docs/assets/overview.svg` | 自动生成的流程示意图 |

---

## 交付物导航

| 文档 | 内容 |
|------|------|
| [业务架构](docs/01-architecture.md) | 四层架构 + 数据流 + 能力边界 |
| [工作流流程](docs/02-workflow.md) | 6 条工作流的 DAG 可视化 |
| [使用场景](docs/03-scenarios.md) | 3 个真实场景（含前后对比） |
| [使用手册](docs/04-usage.md) | 各平台导入指引 + 常见问题 |
| [示例库](docs/05-examples.md) | 7 组输入输出示例 |
| [录像脚本](docs/06-recording-script.md) | 7 镜头分镜 + 旁白稿 |
| [校验报告](docs/07-test-report.md) | 资产质量校验结果 |

---

## 技能清单（7 个）

| # | 技能 | 能力族 | 复杂度 | 提示词 | 文档 |
|---|------|--------|--------|--------|------|
| 1 | 关键词聚类 | 摘要提炼 | `M` | [prompt.txt](skills/keyword-cluster/prompt.txt) | [docs](skills/keyword-cluster/docs/) |
| 2 | SERP 竞争分析 | 摘要提炼 | `M` | [prompt.txt](skills/serp-competition-analysis/prompt.txt) | [docs](skills/serp-competition-analysis/docs/) |
| 3 | 内容大纲生成 | — | `S` | [prompt.txt](skills/content-outline-generate/prompt.txt) | [docs](skills/content-outline-generate/docs/) |
| 4 | 程序化页面生成 | — | `L` | [prompt.txt](skills/programmatic-page-generate/prompt.txt) | [docs](skills/programmatic-page-generate/docs/) |
| 5 | 多语言写作 | 多语言 | `S` | [prompt.txt](skills/multilingual-writing/prompt.txt) | [docs](skills/multilingual-writing/docs/) |
| 6 | 内链智能配对 | — | `M` | [prompt.txt](skills/internal-link-matching/prompt.txt) | [docs](skills/internal-link-matching/docs/) |
| 7 | 排名波动预警 | — | `M` | [prompt.txt](skills/rank-volatility-alert/prompt.txt) | [docs](skills/rank-volatility-alert/docs/) |

## 工作流清单（6 条）

| # | 工作流 | 阶段 | 复杂度 | 触发 | 定义 | 文档 |
|---|--------|------|--------|------|------|------|
| 1 | 关键词调研 | `P1` | `M` | 人工（每月） | [SKILL.md](workflows/keyword-research-flow/SKILL.md) | [docs](workflows/keyword-research-flow/docs/) |
| 2 | 竞品内容差距分析 | `P1` | `M` | 事件（调研后） | [SKILL.md](workflows/content-gap-analysis-flow/SKILL.md) | [docs](workflows/content-gap-analysis-flow/docs/) |
| 3 | 文章大纲生成 | `P1` | `S` | 人工 | [SKILL.md](workflows/article-outline-flow/SKILL.md) | [docs](workflows/article-outline-flow/docs/) |
| 4 | 多语言文章产出 | `P1` | `M` | 事件（大纲确认后） | [SKILL.md](workflows/multilingual-article-flow/SKILL.md) | [docs](workflows/multilingual-article-flow/docs/) |
| 5 | 内链建议 | `P2` | `M` | 定时（每周） | [SKILL.md](workflows/internal-link-advice-flow/SKILL.md) | [docs](workflows/internal-link-advice-flow/docs/) |
| 6 | 收录与排名监控 | `P2` | `M` | 定时（每周） | [SKILL.md](workflows/indexing-rank-monitor-flow/SKILL.md) | [docs](workflows/indexing-rank-monitor-flow/docs/) |

---

## 知识库与连接器

| 目录 | 说明 |
|------|------|
| [`knowledge/`](knowledge/README.md) | RAG wiki 知识库：填入业务信息可显著提升输出质量 |
| [`connectors/`](connectors/README.md) | 连接器说明：数据从哪来、怎么合规地来 |

---

## 资产校验

```bash
pip install -r requirements.txt
pytest tests/ -v
```

校验技能完整性、提示词结构、契约一致性、工作流 DAG、技能级与工作流级 docs 完整性、知识库 wiki 与连接器结构。
**不需要任何 API Key。**

---

## 合规声明

- ✅ 所有输出为 **AI 辅助生成**，交付前须人工审核
- ✅ 提示词内置**违禁词禁止清单**，符合《广告法》要求
- ✅ 遵循《人工智能生成合成内容标识办法》
- ✅ 连接器只走**官方 API** 或**用户导出数据**
- ✅ 所有对外发布动作**保留人工确认环节**

---

## 许可

[Apache-2.0](LICENSE) — 可自由使用、修改、商用

---

*由 bangwozuo 业务库自动生成 · 2026-09-29*
