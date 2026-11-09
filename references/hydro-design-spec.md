---
version: 2.0
name: changjiang-power-eight-dimension-report-design
description: 水文纸本 / HYDRO PAPER。暖纸底编辑式研报，宋体大标题 + 无衬线正文，钴蓝单一强调色，等高线流域图为签名元素；替换 v1 的深空蓝 Hero 与紫金配色。
status: 取代 v1.0；v1 的「深空蓝 Hero + Stripe 紫 + 琥珀金」整体作废
---

> **v3 固化说明（2026-11-09）**：本规格已升级为 skill 的**默认视觉**，不再是外部注入层。
> 落点：`assets/hydro-skin.css`（样式）+ `scripts/html_helpers.py` 的 `HERO()`（签名结构）
> + `scripts/render_report.py`（自动注入 + Hero 升级 + 旧色映射）。
> 生成链路：`render_report.py --data x.json --out y.html` 一步到位，**不再需要 apply_skin.py 之类的后处理脚本**。
> 门禁 `P0-12` 会检查 `id="hydro-skin"` 与 Hero 签名元素是否齐全；`P0-13` 检查入场动效不含 opacity；`P1-7` 提示旧三色残留。
> 手工改样式时只改 `hydro-skin.css`，不要回写 `template.html`；需要对照旧版用 `--legacy-skin`（会被门禁阻断）。

## Overview

单文件 HTML 行业研报，读者是做决策的投资者。目标质感：编辑式研究刊物（editorial research journal），不是后台仪表盘。
v1 的深空蓝渐变 Hero、金色描边标题、紫色渐变卡、巨型实心水印是「模板默认值」，被用户判定为 low；v2 整体换成暖纸底 + 墨色 + 一个强调色。
首屏给结论，正文可复算，来源可点开。全部覆盖规则集中在 `assets/hydro-skin.css` 一处，由生成器自动注入 `<head>` 末尾。

**签名元素（signature）**：右侧 `720×520` 等高线流域 SVG（9 条 1px 曲线 + 1 条 2px 主河道 + 3 个站点圆点），叠加 96px 网格底纹；章节头部改用 132px **描边空心数字**（透明填充 + 1px 描边），取代 v1 的 180px 实心淡紫水印。

## Colors

| Token | 值 | 角色 |
|---|---|---|
| `--p-paper` | `#f3f0e8` | 页面底、Hero 底 |
| `--p-surface` | `#ffffff` | 卡片面 |
| `--p-surface-2` | `#faf8f3` | 次级面（方法卡、结论框、表头） |
| `--p-surface-3` | `#efebe0` |  hover / 轨道底 |
| `--p-ink` | `#12181c` | 标题、正文强调 |
| `--p-ink-2` | `#4f5a60` | 正文 |
| `--p-ink-3` | `#8b9295` | 标签、角标、辅助 |
| `--p-line` | `#e2ddd1` | 1px 分隔线 |
| `--p-line-2` | `#c9c2b3` | 外框、强分隔 |
| `--p-accent` | `#2a4bd7` | 唯一强调色：章节竖线、链接、图表主序列、主河道 |
| `--p-accent-soft` | `#e9ecfa` | 强调色浅底 |
| `--p-risk` | `#c0442c` | 风险/谨慎/涨（A 股语义） |
| `--p-warn` | `#b7852a` | 中性 |
| `--p-good` | `#12684a` | 看好/跌（A 股语义） |
| `--p-shadow` | `0 1px 2px rgba(18,24,28,.035)` | 全站唯一阴影，仅 1 级 |

暗色模式（`[data-theme="dark"]`）：paper `#0e1215` / surface `#161b1f` / ink `#ece9e1` / line `#2a3236` / accent `#8fa6ff`，同一套 11 个 token 反相，不新增色。

### Do
- 全站仅 `--p-accent` 一种强调色；红/绿只承担评级与 A 股涨跌语义。
- 数字统一 `font-variant-numeric:tabular-nums`，英文标签用 `--font-mono` + `letter-spacing:.18em` 大写。
- 分隔一律 1px `--p-line`，禁止 2px 以上粗线和渐变描边。

### Don't
- 禁止深空蓝 `#0a1628`、Stripe 紫 `#635bff`、琥珀金 `#c8943b` 出现在任何可见表面。
- 禁止任何 `linear-gradient` 彩色渐变（图表断轴斜纹除外）、发光阴影、文字阴影、毛玻璃。
- 禁止彩虹配色、渐变徽章、实心巨型数字、emoji 作图标。
- 禁止圆角 >16px，禁止纯黑 `#000000`。

## Typography

`--font-serif: "Songti SC","STSong","Noto Serif CJK SC","Source Han Serif SC",Georgia,serif`
`--font-sans: "PingFang SC","Inter","SF Pro Display","Microsoft YaHei",sans-serif`
`--font-mono: "SFMono-Regular","JetBrains Mono",ui-monospace,monospace`

| 档名 | 字号 | 字重 | 行高 | 字族 | 用途 |
|---|---|---|---|---|---|
| hero | 64px | 600 | 1.14 | serif | Hero 主标题，`letter-spacing:-.025em` |
| step-title | 30px | 600 | 1.25 | serif | 章节标题 |
| h3 | 20px | 600 | 1.4 | serif | 章内小节 |
| exec-h2 | 26px | 600 | 1.3 | serif | 执行摘要 |
| body | 14.5px | 400 | 1.9 | sans | 正文 |
| caption | 13px | 500 | 1.7 | sans | 卡片说明 |
| label | 10.5px | 500 | 1.4 | mono | 全大写 overline / 表头 / KPI 标签 |
| numeral | 34px | 700 | 1.1 | sans | KPI 数值，`tabular-nums` |

### Don't
- 字号 <10px；中文斜体；同层级混用两种字重；标题用无衬线黑体加粗到 800。

## Layout

- 间距基频 8px：`4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 96`，只用这十值。
- 内容宽度 `1180px`；`.main-wrap` 左右 `48px`；≥1200px 时左留 `248px` 给侧栏。
- Hero 内容 `padding:34px 48px 0`；Hero 顶部 masthead `18px` 下边距 + 1px 底线。
- 章节卡间距 `40px`；卡片内边距 `32px 40px 40px`；章节头 `36px 40px 28px`。
- 网格：Hero 元信息 4 列（列间 1px 竖线，无 gap）；KPI 3 列；目录卡 2 列；风险卡 3 列等高；SWOT 2 列。
- 所有宽表包 `.table-wrap`，`overflow-x:auto`，禁止横向溢出。
- **结构硬约束**：任何插入片段必须标签闭合；综合结论章的 3 张风险卡不得嵌套，数据来源汇总必须是 `.main-wrap` 的顶层兄弟节点。

## Elevation

只用 `--p-shadow` 一级；卡片靠 1px `--p-line` 描边和留白分层。`.side-nav` / `.theme-toggle` 无阴影。禁止 `box-shadow` 浓度 > 0.05。

## Shapes

| Token | 值 | 用途 |
|---|---|---|
| sm | `6px` | 徽章、指引方块 |
| md | `12px` | 卡片、表格容器、图表卡 |
| lg | `16px` | 章节卡、目录卡、执行摘要 |
| pill | `9999px` | 评级徽章 |

## Components

**Hero**：暖纸底 + 96px 双向 1px 网格；右侧等高线流域 SVG（`z-index:0`，文字 `z-index:2`）；顶部 masthead 显示 `RESEARCH NOTE · NO. {note_no}` 与 `数据截至 {as_of}`，大标题挂同一编号上标——两者都由数据 JSON 的 `hero.note_no` / `meta.note_no` 与 `meta.as_of` 注入（`h1[data-note]` + CSS `attr()`），**禁止把某份报告的期号或日期写死在 CSS / 生成器里**；元信息 4 列以 1px 竖线分隔；底部 2px `--p-accent` 线。
**`.step-head`**：白底、1px 底线、左上 48px×2px `--p-accent` 短线；`.step-num` 为 mono 10.5px 大写；`.step-num-watermark` 为 132px 空心描边数字（`color:transparent; -webkit-text-stroke:1px rgba(42,75,215,.18)`），右 `28px`，不裁切。
**`.risk-card`**：白底 + 1px 线，顶部 2px 严重度色（红/琥珀/钴蓝），卡内 `risk-idx` mono 序号 + `risk-sev` 标签 + serif 17px 标题 + 13px 说明；三卡 `align-items:stretch` 等高，禁止 emoji 圆点、禁止彩色渐变底、禁止左粗边。
**`.swot-cell`**：白底 + 1px 线 + 顶部 2px 分类色，`h4` 14px，正文 13px。
**表格**：表头 `--p-surface-2` + 11px mono 大写 + 1px 底线；无斑马纹、无深色块；表体 13.5px，行 1px 线。
**`a.ref`**：`↗` 上标，`--p-accent`，`opacity:.55`；hover 到 1。
**图表**：C1 双序列柱 / C2 横条 / C3 雷达，主序列 `--p-accent`，次序列 `#a8a293`；断轴斜纹用 `--p-accent`；不硬编码 `<rect>` 坐标。
**侧栏**：透明无卡片，左侧 1px 竖线，`top:50%` 垂直居中；当前章用 6px `--p-accent` 圆点 + 墨色文字。
**主题按钮**：38px 圆，1px `--p-line-2`，`font-size:0` + `::before{content:"◐"}`，不显示 emoji。

## Motion

- 仅 Hero 元素入场：`hydroRise`（纯 `translateY(14px)` → 0），`cubic-bezier(.2,.7,.2,1)`，时长 `.7s–.8s`，6 段延迟 `.05/.14/.22/.34/.42/.52s`；等高线 `hydroArt` 1.2s 纯 `translateX(20px)` → 0。
- **不动画 opacity**：截图工具/无头浏览器在 t=0 抓帧时，`animation-fill-mode:both` 会把 `opacity:0` 当成静态初始态，导致首屏整块文字消失。纯 transform 保证任意抓帧时刻都可读。
- 全部包在 `@media (prefers-reduced-motion:no-preference)`；无 JS 也可见，禁止 `opacity:0` 作为静态初始态。
- hover：`translateX(4px)` / `translateY(-2px)`，`.2s`。顶部 2px 阅读进度条由模板 JS 驱动 `--p` 变量。

## Do's and Don'ts

### Do
- 首屏结论先行；每个关键数字 120 字符窗口内有可点击来源。
- 并列信息分行，每段 ≤150 字；数字用 `tabular-nums`。
- 交付前跑 `node --check`、P0/P1 门禁、链接验活、`capture.py --all` + 首屏截图。

### Don't（No-Fly Zone）
- 不改 skill 的 `assets/template.html`；覆盖只在注入层。
- 不把 `.reveal` 初始透明度设 0 且依赖 JS 才显示。
- 不用纯域名首页当来源链接；不编造 URL；不在 `<script>` / `<style>` / 注释内插角标。
- 不用两种以上强调色、大圆角、又黑又重的阴影、无意义渐变。
- 不允许任何未闭合 `<div>` 进入 `conclusion_html`（v1 排版事故根因）。

## Responsive

| 断点 | 宽度 | 变化 |
|---|---|---|
| desktop | ≥1200px | 侧栏固定，`.main-wrap` 左留 248px，Hero 标题 64px |
| tablet | 768–1199px | 侧栏隐藏，Hero 标题 52px，等高线 opacity .35，元信息 4 列保持 |
| mobile | <768px | Hero 标题 38px、元信息 2 列、KPI 2 列、风险/SWOT 1 列、等高线隐藏 |
| small | <560px | Hero 标题 30px、KPI 1 列、章节水印 88px |

- 触控目标 ≥40×40px；打印：隐藏导航/等高线/进度条，强制亮色，卡片去阴影。

## Known Gaps

- 等高线 SVG 是装饰性示意，不代表真实流域地理坐标（已在 Hero 标注 `SCHEMATIC`）。
- 暗色模式靠 11 个 token 反相；模板自带的 `[data-theme="dark"]` 硬编码规则由注入层以 `html[data-theme="dark"]` 更高优先级覆盖。
- 宋体标题依赖本机 `Songti SC`；无该字族时回落 Georgia/系统衬线，版心不塌陷。
