# 八维分析 · 质量门禁（quality-gate）

> 本文件是报告发布前的**质量门禁**。元原则：**凡是重要规则，必须能被程序检查；不能被检查的规则等于建议。**
> 门禁由 [check_report.py](check_report.py) 机械执行，P0 不过则报告不得输出。人工自检清单（SKILL.md 末尾）仅作补充，不替代本门禁。

---

## 分级

| 级别 | 含义 | 不通过后果 |
|------|------|-----------|
| **P0** | 阻断发布 | 报告不得输出，必须返工 |
| **P1** | 发布前必改 | 阻塞发布，改完再发 |
| **P2** | 优化项 | 不阻断，建议做 |

---

## 🔴 P0 · 阻断发布（任一不满足则不得输出）

| # | 规则 | 机械校验方式 |
|---|------|------------|
| P0-1 | 八章方法卡齐全 | 统计 `.spec` 或方法卡块数 = 8，且每块含「方法卡」标识 |
| P0-2 | 八章推导过程齐全 | 统计推导块数 = 8，且默认展开 |
| P0-3 | 关键数字有公式来源 | 渗透率/CR8/UE/PE/PEG 等核心数可由报告内公式复算；脚本提取公式块校验 |
| P0-4 | 链接邻近率 ≥ 90% 且非纯域名 | 关键数字落在 near=120 字符窗口 + 整段 `<a>…</a>` 锚点内即计覆盖，覆盖率 ≥ 0.9；正则 `^https?://[^/]+/?$` 命中即不合格。**仅代表链接密度，不代表链接可核查**：用 `verify_links.py` 验活 + 按 output-spec.md 人工抽查 |
| P0-5 | 护城河用 5×4 矩阵 | 护城河章须出现 5×4 矩阵与「三问验证」关键词 |
| P0-6 | 生命周期阈值用正确表 | 阈值须用本 Skill 判定表（15/20/35/60/70+，工程化切分，非书中原档）；**仅维度一章节**不得出现「<5% / 5-30% / >30%」旧阈值串（其它章节的百分比表述不受限） |
| P0-7 | 可比公司数据表存在 | 竞争格局章含 ≥3 家可比公司的份额/盈利对照表 |
| P0-8 | 估值双视角 | 同时给「相对（同业分位）+ 绝对（历史分位）」结论，且排除低估值陷阱 |
| P0-9 | 章节锚点齐全 | `id="dim1"~"dim8" / conclusion / src-summary` 共 10 个，导航契约不可破 |
| P0-10 | 内容五件套 | 每维度含人话卡 / 反面假设 / 盯什么 + 评级 / 档位 / 来源框徽章，结论框在位 |
| **P0-11** | **全文标签栈平衡** | `html_helpers.validate_document()`：div 开闭计数相等 + 块级容器栈无悬空。**渲染前另有一道逐片段校验**（`render_report.validate_data_fragments()`），不平衡直接拒绝出稿 |
| **P0-12** | **v3 默认皮肤在位** | 必须存在 `<style id="hydro-skin">`（**不能**只用 `--p-paper` token 代替，否则皮肤被改名/部分注入会漏检）；Hero 含 `.hero-masthead / .hero-art / .hero-foot / .hero-content`；暗色 token `--p-paper:#0e1215` 存在；无旧 `<div class="hero">` 残留 |
| **P0-13** | **入场动效安全** | `@keyframes hydroRise/hydroArt/reveal` 内不得出现 `opacity`（只允许 transform）；`.reveal` 无静态 `opacity:0`；`<script>` 内不得混入 `<a class="ref">` |
| **P0-14** | **无占位符残留** | 全文（含 `<head>`）不得出现 `{R(` / `{{C1}}` / `{{C2}}` / `{{C3}}` / `{行业名称}` / `{日期}` / `TODO`；扫描前先剔除 `data:image/*;base64,` 段，避免内嵌二维码随机字符误报 |
| **P0-15** | **C1/C2/C3 三图齐全** | body 内 `.chart-card` ≥3；C1 有 `<svg>+<rect>+svg-bar-*`；C2 有 `.bar-chart+.bar-fill+.bar-row`；C3 有 `.svg-data+<polygon>`。**历史漏洞**：charts 曾是死字段、三图靠手写 SVG，删光三图也能过全部旧门禁 |
| **P0-16** | **紧凑溯源条强制在位** | body 内 `.brand-block` / `.brand-head`（单行署名）/ `.brand-meta`（单行说明）/ `.brand-qr` / `.report-attribution` 齐全；`.brand-channel` 两行（公众号 / 视频号各一行，不并排）；`id="qrLightbox"` + `getElementById('qrLightbox')` 在位（小码点得开大图）；**无 `<figcaption>`**（码下不放字）；**`.brand-qr` 宽度 ≤60px**（v3.2.2，防页脚重新膨胀成广告卡）；`assets/brand.json` 的 `wechat` / `video` 名称出现；两张 `<img src="data:image/png;base64,...">` 内嵌二维码；无 `retired_names` 旧名残留。**无关闭开关**：报告多级转发后页脚是唯一出处锚点 |

---

## 🟠 P1 · 发布前必改

| # | 规则 | 机械校验方式 |
|---|------|------------|
| P1-1 | PEST 走完五段链 | 每个外部因素含 事实→传导→对象→量级→时点 五段 |
| P1-2 | 景气指标看板完整 | 含量/价/库存/订单/产能五维与跟踪频率 |
| P1-3 | 规模测算含两法交叉 | 市场规模须自上而下 × 自下而上，差距超过 30% 已解释 |
| P1-4 | 结构完整可解析 | HTML 可被解析，八维卡片齐全，综合结论含反共识检验与推翻信号 |
| P1-5 | 导航模块完整 | 侧栏 / 目录卡 / 深色切换齐全（章节锚点另属 P0-9） |
| P1-6 | 数据截止时点已声明 | 报告头含「截至 YYYY-MM-DD HH:MM」；行情/估值数据须标口径 |
| **P1-7** | 无旧三色 / 无 UNSOURCED | body 内 `#635bff / #c8943b / #0a1628 / #4f46e5` 残留提示（生成器已自动映射 C1 图例，其余改用 `--p-*` token）；`[UNSOURCED]` 需补来源或改降级署名 |

---

## 🟢 P2 · 优化项（不阻断，建议做）

| # | 规则 | 说明 |
|---|------|------|
| P2-1 | 小白翻译段 + 章末一句话 | 每章含 💬 小白翻译与「本章一句话」摘要 |
| P2-2 | 打印样式核对 | HTML 打印时隐藏吸顶导航、折叠块强制展开、图表不跨页断裂 |
| P2-3 | 来源汇总表登记 | 文末来源表含全部六元组字段，无链接项标「无公开链接」 |

---

## 校验脚本

`check_report.py` 读取生成的 HTML 报告，逐条执行 P0/P1 校验，任一 P0 失败则退出码非 0（CI/手动阻断均可接入）。脚本逻辑见文件内注释，关键检查：

| 规则 | 实际实现函数 |
|------|-------------|
| P0-1 / P0-2 | `count_method_cards()` / `count_derivation()` |
| P0-3 | `has_formula_recompute()` |
| P0-4 | `compute_key_coverage()` + `pure_domain_urls()`；返工定位 `locate_uncovered.py`；链接验活 `verify_links.py` |
| P0-5 / P0-6 | `chapter_has()` / `lifecycle_section()`（仅维度一，且用 `html.unescape` 兼容 `&lt;5%`） |
| P0-7 / P0-8 | `has_comparable_table()` / `chapter_has()` |
| P0-9 / P0-10 | `check_nav()` / `check_five_pieces()` |
| P1-1 ~ P1-6 | `chapter_has()` / `has_prosperity_board()` / `has_two_method_cross()` / `has_structure()` / `check_nav()` / `has_as_of_timestamp()` |
| **P0-11 ~ P0-16 / P1-7** | `check_structure_balance()` / `check_visual_skin()` / `check_motion_safety()` / `check_placeholders()` / `check_charts()` / `check_brand()`（复用 `scripts/html_helpers.py`） |
| 生成器输入校验 | `render_report.validate_required_fields()` / `validate_charts()` / `validate_data_fragments()`：缺字段、图表数值错、标签不平衡 → 退出码 2 且中文提示，不出稿 |
| 视觉验收 | `scripts/capture.py`（Chrome headless 裁剪页，锚点不滚动）+ 明暗双主题首屏截图 |
| 链接验活 | `verify_links.py`（唯一链接数 / 可达 / 失效数） |
| JS 语法 | `references/check_js.py`（先剥离 HTML 注释再提取内联脚本，再跑 `node --check`；不要手写提取正则） |

---

## 执行时点（v3.0.1 四道卡）

门禁**硬卡四道**，不是写完再自检：

1. **输入校验**：`render_report.validate_required_fields()` 查必填字段、`validate_charts()` 查图表数值结构；坏 JSON / 文件不存在 / 缺字段 → 中文提示 + 退出码 2，**不产出文件**。
2. **渲染前**：`render_report.validate_data_fragments()` 逐片段查标签栈，不平衡 → 退出码 2 且**不产出文件**。构造器 `html_helpers.RISK/SWOT/CONFLICT/D` 从源头保证闭合。
3. **渲染后**：`render_report.validate_document()` 全文复检；`inject_charts()` 保证 C1/C2/C3 落位。
4. **交付前**：`render_report.py` 默认自动调 `check_report.py`（可用 `--no-gate` 显式关闭，但交付前必须补跑 `--strict`），P0-15 核对三图在位，P0-16 核对紧凑溯源条（单行署名 / 单行说明 / 小码 ≤60px）与双二维码在位。

流程：Phase 0~2 采集与分析 → Phase 3 结论 → **Phase 4 `render_report.py --data --out`（内含四卡）** → Phase 4.5 视觉/链接/JS 验收 → 交付。

> 每次改版或分享前跑 `python3 scripts/selftest_all.py`：它会故意破坏成品并确认四道防线仍能拦截。

> ⚠️ **不要绕过门禁去手工修 HTML**：历史上所有排版事故都发生在「直接编辑成品 HTML」或「手写大段片段」时。要改内容就改数据 JSON，重新走生成器。
