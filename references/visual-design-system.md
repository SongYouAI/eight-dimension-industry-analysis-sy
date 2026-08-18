# 八维行业分析报告 · 视觉设计系统 v2.0

> 本文件是报告 HTML 视觉的**唯一权威规范**。v2.0 起**放弃八皮肤行业自适应**，整体对齐「七步财报分析报告」的版式与质感。生成报告时复制 [`assets/template.html`](../assets/template.html) 填充 `{占位符}` 即可，所有组件与 token 已内置，无需重写 CSS。
>
> **视觉签名**：深空蓝 + Stripe 紫 + 琥珀金 三色体系 · 浅色主体 + 深色 Hero · 数字水印 step-head · 紫金渐变色条贯穿全篇。

---

## 1. 设计哲学与视觉基调

**定位**：买方研究级行业报告，专业数据分析感，不是营销落地页。

| 主张 | 含义 | 反面 |
|------|------|------|
| **数据是主角** | 视觉服务数据可读性，装饰只做层次引导 | 为炫技加特效 |
| **三色金融风** | 深空蓝沉稳 + Stripe 紫提神 + 琥珀金点睛，统一全篇 | 每个行业换一套色 |
| **克制的能量感** | 深色 Hero + 单一发光焦点 + 微动效 | 满屏渐变、多焦点争抢 |

**核心视觉特征关键词**：深空蓝 Hero、数字水印 step-head、紫金渐变条、深蓝表头数据表、金色结论框、卡片分层。

---

## 2. 三色令牌系统

### 2.1 主色

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--navy` | `#0a1628` | 主背景 / 标题 / 深色区块 |
| `--navy-mid` | `#152238` | 次级深蓝（渐变中段） |
| `--navy-deep` | `#1a2744` | 深蓝浅阶（渐变尾段） |
| `--purple` | `#635bff` | **Stripe 紫（强调）**：渐变色条、方法卡、洞察、图表主色 |
| `--purple-deep` | `#4f46e5` | 紫深阶 |
| `--gold` | `#c8943b` | **琥珀金（点睛）**：评级、分隔线、结论框、KPI 尾段 |
| `--gold-light` | `#d4a853` | 金浅阶 |

### 2.2 中性色

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--white` | `#ffffff` | 卡片面 |
| `--off-white` | `#f5f6fa` | 页面底色 / 次级面 |
| `--gray-light` | `#e2e5ec` | 边框 / 分割线 |
| `--gray-border` | `#c4c8ce` | 强边框 |
| `--text` | `#1a1a2e` | 正文 |
| `--text-secondary` | `#5a6178` | 次级文字 |
| `--text-muted` | `#6b7280` | 弱化文字 |

### 2.3 语义色（涨红跌绿 · A股惯例）

| 语义 | 值 | 用途 |
|------|-----|------|
| 涨 / 同比上升 | `#d63384`（红） | KPI delta up |
| 跌 / 同比下降 | `#16a34a`（绿） | KPI delta down |
| 看好 / 正向 | `#0d7c3b` | rating-buy、dot-green |
| 中性 / 警示 | `#c8943b` | rating-hold、dot-yellow |
| 谨慎 / 负向 | `#b71c1c` | rating-sell、dot-red |
| 信息 | `#1e5fb4` | source-box、tier-medium |

> **注意区分**：财务数据「涨红跌绿」（A股惯例）；评级语义「看好=绿、谨慎=红」（国际评级惯例）。二者不冲突——一个是行情方向，一个是态度判断。

### 2.4 图表序列色（Stripe 六色）

```css
--chart-1:#635bff; --chart-2:#0d7c3b; --chart-3:#b71c1c;
--chart-4:#c8943b; --chart-5:#5b8def; --chart-6:#2e8b57;
```

多序列图表用 `.svg-bar-1~6` 序列色区分；单序列主色用 `#635bff`（紫）、次序列用 `#c8943b`（金）。

---

## 3. 组件清单（template.html 已内置）

| 组件 | class | 关键规范 |
|------|-------|---------|
| Hero 深色场景 | `.hero` | 深空蓝三段渐变 `#0a1628→#152238→#1a2744` + 金色 3px 底边 + 紫金曲线纹理；h1 42px 金暖白 |
| 深色切换 | `.theme-toggle` | 右上角固定圆形按钮，切换 `data-theme="dark\|light"`，localStorage 持久化 |
| 目录卡 | `.toc-card` | Apple 毛玻璃 `blur(12px)`，10 项网格，hover 紫左边条 |
| 执行摘要 | `.exec-summary` | 白卡 + 金色下划线标题，关键数字金色高亮 |
| 维度卡 | `.step-card` | 白卡圆角 20px，含 `.step-head` + `.step-body` |
| 数字水印头 | `.step-head` | 顶部紫金 2px 渐变条 + 巨大半透明数字水印 `.step-num-watermark`（180px，紫色 5% 透明）+ `.step-title` 28px 大标题 |
| 方法卡 | `.method-card` | 紫蓝渐变底 + 左边 4px 紫金条 + 四行（回答什么问题/用什么方法判/判据/需要哪些数据） |
| KPI 卡 | `.kpi-card` | 顶部 3px 紫金渐变条 + 30px 大数值 + `.kpi-delta`（up 涨红 / down 跌绿）|
| 人话卡 | `.human-term-card` | 术语→大白话→类比，浅紫渐变底 + 左紫条 |
| 反面假设 | `.reverse-note` | 「也可能是…」反证块，灰底 + 左灰条 |
| 洞察 | `.insight` | 紫底 + 左紫条 |
| 盯什么 | `.insight-card` | 「📌 普通投资者要点」卡，白→浅紫渐变 + 顶部紫条 |
| 数据表 | `.table-wrap > table` | 深空蓝渐变表头 + 金色 2px 底边 + 斑马纹 + 紫高亮 `td.highlight` |
| 风险卡 | `.risk-card` | 左色条：`risk-high` 红 / `risk-warn` 黄 / `risk-info` 蓝 |
| 结论框 | `.conclusion-wrap` | 金色渐变底 `#fdf8ee→#f7efd0` + 左金边，评级徽章内嵌 |
| 数据来源框 | `.source-box` | 浅灰底 + 左蓝条 + 状态徽章 |
| 徽章 | `.tier-badge` `.rating-badge` `.status-badge` | 档位 rich/medium/lean/online；评级 buy/hold/sell；状态 resolved/pending/gap/info |
| 图表卡 | `.chart-card` | 白卡 + `.chart-head` 头 + SVG（C1/C2/C3） |
| SWOT | `.swot-grid` | 2×2，四色对应 正/负/主/警 |
| 维度冲突 | `.dim-conflict` | 金红渐变底 + 虚线分隔解读区 |
| 跟踪指标 | `.tracking-list` | 名称加粗 + 当前值 + 箭头 + 阈值 |

---

## 4. 图表组件契约（C1 / C2 / C3）

`assets/template.html` 已内置三处可直接复制的 SVG 图表组件块（带占位符与坐标公式）。生成时**复制母版填数，禁止现写 SVG 或从零造图**。

| 图表 | 位置 | 实例化动作 | 配色 |
|------|------|-----------|------|
| **C1** 双序列柱状图 + 数据表 | dim3「三、市场规模」TAM 表之后 | 柱顶 `y = 290 - (value/Y_MAX)*270`，替换 `{v*/y*}` | 序列A `svg-bar-primary`(紫) / 序列B `svg-bar-energy`(金)；≥3 序列用 `.svg-bar-1~6` |
| **C2** 可比公司 PE 对比条形图 | dim6「六、估值」 | 条形宽度 `=(PE/同行最大值)×100%`，锚点加 `.gold` 金高亮 | `bar-fill` 紫渐变 / `.gold` 金渐变 |
| **C3** 八维评级雷达图 | conclusion 信号快照表之后 | 顶点 `θ=-90°+i*45°`，r: score3→120 / score2→80 / score1→40 | `svg-data` 紫填充 / 弱信号 `.weak` 金 |

> **强制一致性**：C3 雷达 8 轴评分严格等于同页信号快照表评级；C1/C2 数据与正文 KPI/表格完全一致，禁止图表与文字口径冲突。

---

## 5. 排版规则

| 层级 | 字号 | 字重 | 用途 |
|------|------|------|------|
| Hero H1 | 42px | 800 | 报告主标题 |
| step-title | 28px | 800 | 维度大标题 |
| 小节 h3 | 18px | 800 | 维度内小标题（紫金渐变色条） |
| 正文 | 15px | 400 | body 基准 |
| 方法卡/表格 | 13.5px | 400 | 数据密集区 |
| KPI 数值 | 30px | 800 | `tabular-nums` 等宽数字 |
| 注释/来源 | 12.5px | 400 | 次级信息 |

**字体栈**：`"PingFang SC","Inter","SF Pro Display","Microsoft YaHei",sans-serif`
**数字**：所有指标数值加 `font-feature-settings:"tnum"`，保证纵向对齐。
**关键数字高亮**：正文 `strong` 加金色背景下划线 `linear-gradient(transparent 62%, rgba(200,148,59,0.22) 62%)`。

---

## 6. 阴影与动效

**阴影分级**：`--shadow-sm`(贴附) / `--shadow-md`(悬浮) / `--shadow-lg`(抬升)。
**动效白名单**：hover 上浮 `translateY(-3px)` .25s；卡片 hover 微动；平滑滚动。禁全屏闪烁/自动播放/连续动画。

---

## 7. 禁令

- ❌ 荧光色、饱和度 >90% 的大面积色块
- ❌ 渐变文字滥用（仅 Hero H1 内 `.accent` 一段）
- ❌ 旋转/闪烁/视差/自动轮播
- ❌ 外部字体/图表库 CDN（报告必须离线可开，SVG 自包含）
- ❌ 纯黑背景大面积铺底（深色仅 Hero 与数据表表头）
- ❌ 互联网黑话、营销措辞（"重磅""必看""强烈推荐"）
- ❌ 裸 emoji 评级（须用 `.rating-badge`）、纯文字置信度（须用 `.tier-badge`）

---

## 8. 响应式与打印

**断点**：`≤900px` KPI/风险卡塌两列；`≤768px` KPI 两列、字号下调；`≤560px` 单列、step-title 20px。
**打印**：Hero 保留深底（`print-color-adjust:exact`）；`.side-nav`/`.top-progress`/`.theme-toggle` 隐藏；`[data-theme="dark"]` 强制回落亮色；`.step-card`/`.chart-card`/`.conclusion-wrap`/`table` 加 `break-inside:avoid`。

导出命令（macOS 无头 Chrome）：
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf="{行业}_八维分析报告.pdf" "{行业}_八维分析报告.html"
```

---

## 9. 视觉交付自检

- [ ] `<html>` 默认 `data-theme="light"`，深色切换按钮 `#themeToggle` 在位
- [ ] 八个维度卡 `id="dim1"`–`dim8` 齐全，每卡含 `.step-head`（数字水印 + step-title）
- [ ] 每维评级用 `.rating-badge`、档位用 `.tier-badge`，无裸 emoji 评级、无纯文字置信度
- [ ] 每维含五件套：`.human-term-card` / `.reverse-note` / `.insight-card` + `.source-box`
- [ ] 数据表深空蓝渐变表头 + 金色底边，无裸 `<table>`（须包 `.table-wrap`）
- [ ] 综合结论 `.conclusion-wrap` 金色渐变底 + 评级徽章
- [ ] C1/C2/C3 三图在位，SVG 带 `role="img"`+`aria-label`，配色用 token 无 inline 硬色
- [ ] 无外部 CDN，双击 HTML 可离线渲染

---

## 10. 给 AI 的生成指令模板

```
版式：Analytics Blue 三色金融风（深空蓝 #0a1628 + Stripe 紫 #635bff + 琥珀金 #c8943b）
动作：复制 assets/template.html → 替换 {占位符} → 每维度填五件套（人话卡/反面假设/盯什么）+ 徽章（评级/档位/来源框）→ 实例化 C1/C2/C3 三图
禁止：手改 CSS 变量、行业皮肤、裸表格、裸 emoji 评级、纯文字置信度、外部 CDN
收尾：按 §9 自检逐条核对 + 跑 check_report.py 门禁
```

---

*视觉设计系统 v2.0 | 2026-08-18 | 对齐七步财报分析报告版式（深空蓝+Stripe紫+琥珀金三色体系、数字水印 step-head、紫金渐变色条、深蓝表头数据表）*
