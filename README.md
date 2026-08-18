# 八维行业分析 (Eight-Dimension Industry Analysis)

> 多源投研数据驱动的八维行业分析引擎。输入一家公司名或一个行业名，自动产出覆盖**产业生命周期、商业模式、市场规模、护城河、竞争格局、估值、外部因素、景气度**八大维度的完整 HTML / Markdown / PDF 三份分析报告。

方法论改编自肖璟《如何快速了解一个行业》，按产业生命周期阶段自适应分配八维分析权重。

---

## ✨ 功能特性

- **八维框架**：以产业生命周期为轴心，八维度覆盖行业研究的"最低完备集"
- **生命周期自适应**：用渗透率划分法判定阶段，不同阶段的维度权重自动调整
- **多源数据并行采集**：`westock-data` + `neodata-financial-search` + `WebSearch/WebFetch` 并行获取结构化与定性数据
- **三件套输出**：HTML（Analytics Blue 科技金融风，含 CSS 图表/趋势箭头/竞品着色表）+ Markdown + PDF
- **防偏差机制**：Phase 0.5 假设前置 + 专家访谈准备、反共识检验、OIE 认知迭代待办、维度冲突检测
- **强约束**：数据来源强制可核查、投资禁区（不荐股/不给目标价）、异常处理 Fallback

---

## 🎯 触发词

```
八维行业分析 / 行业分析 / 分析XX行业 / 分析XX公司所在行业 / 八维分析 / 行业深度研究
```

**适用**：想快速了解或深度分析一个行业（求职/创业/投资/研究）。
**不适用**：个股实时行情、新闻汇总、荐股、K线技术分析。

---

## 🔧 数据源依赖

| 依赖 | 必需 | 说明 |
|------|------|------|
| `westock-data` | 核心（A股/港股） | 行业分类、成份股、财报、研报 |
| `neodata-financial-search` | 推荐 | 行业级金融语义搜索 |
| `WebSearch` / `WebFetch` | 必需 | 公开信息兜底（或经 `web-access` skill） |
| `wechat-article-search` | 可选 | 微信深度文章 |
| `competitive-analysis` | 可选 | 结构化竞争格局 |

> 非 A股 / 全球行业场景以 `WebSearch/WebFetch` 为主，`westock-data` 仅作参考，报告会标注覆盖面局限。

---

## 🚀 使用步骤

1. 对助手说：「分析 {行业名}」或「分析 {公司名} 所在行业」
2. 助手进入 **Phase 0**：确认行业颗粒度 + 地域范围 + 案例锚点公司
3. **Phase 0.5**：建立研究假设清单 +（可选）专家访谈提纲
4. **Phase 1**：多源数据并行采集（约 10-15 次调用）
5. **Phase 2**：八维度并行深度分析（按生命周期权重分配篇幅）
6. **Phase 3**：综合结论（信号快照 + 维度冲突 + 反共识检验 + OIE 迭代待办 + 跟踪指标）
7. 输出三份报告：`{行业}_八维分析报告.html` / `.md` / `.pdf`

---

## 📁 目录结构

```
八维行业分析/
├── SKILL.md                 # 主流程与规范（已瘦身，623 行）
├── assets/
│   └── template.html        # 完整 HTML 骨架 + CSS（生成时复制填充）
├── references/
│   ├── framework-detail.md  # 八维框架详解与书籍章节映射
│   └── data-sources.md      # 数据源配置与调用示例
├── test-prompts.json        # 触发/诱饵/边界 测试用例（13 条）
├── LICENSE                  # MIT（已并入 README 许可协议节）
├── README.md                # 本文件
└── 示例_八维分析报告.html     # 占位演示报告（非真实数据）
```

---

## ⚠️ 免责声明

本报告基于 AI 对公开信息的整理分析，所有内容仅供参考，**不构成任何投资建议或个股推荐**。投资有风险，决策需谨慎。

---

## 📝 版本

- v2.0（2026-07-31）：SKILL.md 瘦身（内联骨架抽至 `assets/template.html`）；新增 Phase 0.5 假设前置+专家访谈、维2 付费意愿判定、维5 产业地图/颠覆者、维1 一级市场资本动向、综合结论 OIE 迭代待办；修复死资源引用、工具命名一致性、description 触发式；扩充测试用例。
- v1.0：初版八维框架 + 三件套输出。

---

## 👤 作者

**松幽**

- 📱 公众号：**松幽舒苑**
- 🎬 视频号：**松幽Ai提效**

---

## 📄 许可协议（MIT License）

```
Copyright (c) 2026 松幽（公众号:松幽舒苑 | 视频号:松幽Ai提效）

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

> 方法论参考自肖璟《如何快速了解一个行业》（仅借鉴分析框架，未复制原文）。
