#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维行业分析报告 · 质量门禁机械校验脚本（v3.1.0）
================================================
读取生成的 HTML 报告，逐条执行 quality-gate.md 的 P0 / P1 校验。
任一 P0 失败 → 退出码 1（阻断发布）；全部 P0 通过 → 退出码 0。

用法:
    python3 check_report.py <报告.html> [--strict]
    --strict : P1 失败也视为非零退出（默认已严格，--no-strict 才放宽）

v3.0 新增 P0-11 ~ P0-14（对应 2026-11-09 两次返工，防复发）:
    P0-11 全文标签栈平衡（未闭合 div 会吞噬后续章节）
    P0-12 默认皮肤 + v3 Hero 签名元素在位（禁止回落深空蓝）
    P0-13 入场动效不得含 opacity:0 初始态 / 角标不得插进 <script>
    P0-14 占位符残留
    P1-7  body 内旧三色 hex 残留提示
v3.0.1 新增（分享前审计）:
    P0-15 C1/C2/C3 三张数据图齐全（charts 曾是死字段，缺图报告能过全部旧门禁）

依赖: 仅标准库（re / sys / html / os）+ 同仓 scripts/html_helpers.py
"""
import os
import re
import sys
import html as html_lib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import html_helpers as hh  # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def find_section(text, *keywords, window=4000):
    """返回包含任一关键词的『最相关』段落。

    旧实现只取首个命中位置向后 window 字符，但关键词（护城河/估值/外部因素）
    常在导航/TOC/摘要处先出现，导致正文深处的真实章节被窗口截断 → 误杀（假阴性）。
    新实现：扫描所有命中位置，合并间隔 < window 的邻近命中为「章节段」，返回
    跨度最长的那一段，确保能扫到正文深处的真实章节。
    注：当前门禁使用 chapter_has() / section_by_anchor()，本函数保留供扩展，
    不是 P0 判定路径。
    """
    hits = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), text):
            hits.append(m.start())
    if not hits:
        return ""
    hits = sorted(set(hits))
    segs = []
    start = prev = hits[0]
    for h in hits[1:]:
        if h - prev > window:
            segs.append((start, prev + window))
            start = h
        prev = h
    segs.append((start, prev + window))
    best = max(segs, key=lambda s: s[1] - s[0])
    return text[best[0]:best[1]]


def chapter_has(text, anchors, required, window=4500):
    """章节级校验：任一枚锚点（anchors）邻近 window 字符内同时含全部 required 标记即判通过。
    比 find_section 更稳——直接验证『该章节确实包含这些要素』，而非依赖单一窗口截取。
    """
    for kw in anchors:
        for m in re.finditer(re.escape(kw), text):
            seg = text[max(0, m.start() - window // 2): m.start() + window]
            if all(r in seg for r in required):
                return True
    return False


def section_by_anchor(text, start_id, end_id):
    """按 section id 截取原始 HTML 片段；缺起始锚点返回空串。"""
    i = text.find('id="%s"' % start_id)
    if i < 0:
        return ""
    j = text.find('id="%s"' % end_id, i)
    return text[i:j] if j > i else text[i:]


def lifecycle_section(text):
    """P0-6 只在维度一（生命周期）章节内查旧阈值串。

    quality-gate.md 的伪代码写的就是 re.search(..., lifecycle)；旧实现误用全文
    plain，导致维度三「两法差距 >30% 必须解释」这类正常百分比表述被误判。
    返回原始 HTML 片段（不 strip_tags）：strip_tags 会把裸 ` <5% ` 当标签吞掉，
    使 P0-6 永远检不出 ` <5% `；调用方用 html.unescape 兼容 ` &lt;5% ` 写法。
    找不到 dim1 锚点时返回空串（锚点缺失由 P0-9 阻断）。
    """
    return section_by_anchor(text, "dim1", "dim2")


def count_method_cards(text):
    # 方法卡：升级后每维度置顶「方法卡」标识（📐方法卡 或 方法卡 四行结构）
    return len(re.findall(r"方法卡", text))


def count_derivation(text):
    return len(re.findall(r"推导过程", text))


def collect_hrefs(text):
    return re.findall(r'href=["\'](https?://[^"\']+)["\']', text)


def pure_domain_urls(urls):
    # 纯域名首页（无路径或仅 /）：不合格链接
    bad = []
    for u in urls:
        path = u.split("://", 1)[1].split("?", 1)[0].split("#", 1)[0]
        if path.count("/") <= 1 and (path.endswith("/") or "/" not in path[path.find("/"):]):
            # 形如 example.com 或 example.com/
            bad.append(u)
    return bad


def count_numbers(text):
    # 旧版口径，仅供扩展参考：当前 P0-4 使用 compute_key_coverage()，
    # 两者分母定义不同，不要把本函数的结果拿去和门禁输出对照。
    # 仅统计「叙述文本」中的数字（排除 svg 坐标、table 表格单元格、script 内的海量重复数字，
    # 否则真实报告分母被坐标/表格拉爆，覆盖率阈值失去意义）。
    body = text
    m = re.search(r"<body.*?>(.*)</body>", body, re.S | re.I)
    if m:
        body = m.group(1)
    body = re.sub(r"<svg.*?</svg>", " ", body, flags=re.S)
    body = re.sub(r"<table.*?</table>", " ", body, flags=re.S)
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    return len(re.findall(r"\d[\d,.%]*", body))


def compute_proximity_coverage(text):
    """旧版覆盖率口径（near=90 / href 起点 / 全部数字），保留供扩展，不在 P0 判定路径。

    当前 P0-4 使用 compute_key_coverage()：near=120、整段 <a> 锚点、只算关键数字。
    两个函数的分母与窗口都不同，切勿混用或据此返工。
    """
    body = text
    m = re.search(r"<body.*?>(.*)</body>", body, re.S | re.I)
    if m:
        body = m.group(1)
    body = re.sub(r"<svg.*?</svg>", " ", body, flags=re.S)
    body = re.sub(r"<table.*?</table>", " ", body, flags=re.S)
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    href_pos = [h.start() for h in re.finditer(r'href=["\']https?://', body)]
    nums = list(re.finditer(r"\d[\d,.%]*", body))
    if not nums:
        return 1.0, 0, 0
    covered = 0
    for n in nums:
        ns, ne = n.start(), n.end()
        if any(abs(ns - hs) <= 90 or abs(ne - hs) <= 90 for hs in href_pos):
            covered += 1
    return covered / len(nums), covered, len(nums)


def extract_body(text):
    m = re.search(r"<body.*?>(.*)</body>", text, re.S | re.I)
    return m.group(1) if m else text


def strip_noise(body):
    """排除 svg 坐标 / table 单元格 / script 内的海量数字，仅留叙述文本。"""
    body = re.sub(r"<svg.*?</svg>", " ", body, flags=re.S)
    body = re.sub(r"<table.*?</table>", " ", body, flags=re.S)
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    return body


def is_key_number(s):
    """关键数字 = 真实数据声明（需可核查），排除年份(19xx/20xx)与纯序数等非数据claim。"""
    if re.fullmatch(r"(19|20)\d{2}", s):
        return False
    if "%" in s:
        return True
    if "." in s:
        return True
    if s.replace(",", "").isdigit() and len(s.replace(",", "")) >= 4:
        return True
    return False


def link_anchors(raw):
    """返回所有 https 链接的 (a_start, a_end) 锚点区间（含长 URL 整体）。"""
    return [(m.start(), m.end()) for m in
            re.finditer(r'<a\b[^>]*href=["\']https?://[^>]*>.*?</a>', raw, re.S | re.I)]


def num_covered(ns, ne, anchors, near=120):
    """数字是否被某链接锚点覆盖：数字落在 [a_start-near, a_end+near] 区间内。
    用整个 <a>…</a> 锚点而非 href= 起点，避免长 URL 把视觉相邻数字推到 near 之外。"""
    return any(a0 - near <= ns and ne <= a1 + near for a0, a1 in anchors)


def compute_key_coverage(text):
    """关键数字覆盖率 = 可见文本中『邻近某来源链接锚点』的关键数字 / 关键数字总数。
    同时返回覆盖到的独立来源域名数（≥10 防单一来源复用造假）。
    坐标统一在 strip_noise 后的 body 内；style/href/src 属性值（含 URL 内数字）不计入分母。"""
    from urllib.parse import urlparse
    raw = strip_noise(extract_body(text))
    anchors = link_anchors(raw)
    spans = [(m.start(), m.end()) for m in re.finditer(r'(style|href|src)=["\'][^"\']*["\']', raw, re.I)]
    def in_span(p):
        return any(a <= p < b for a, b in spans)
    key = [n for n in re.finditer(r"\d[\d,.%]*", raw)
           if is_key_number(n.group()) and not in_span(n.start())]
    if not key:
        return 1.0, 0, 0, 0
    covered = 0
    seen_src = set()
    for n in key:
        ns, ne = n.start(), n.end()
        if num_covered(ns, ne, anchors):
            covered += 1
            # 取最近的链接域名计入
            best = min(anchors, key=lambda a: abs(a[0] - ns))
            m = re.search(r'href=["\'](https?://[^"\']+)["\']', raw[best[0]:best[1]])
            if m:
                seen_src.add(urlparse(m.group(1)).netloc)
    all_dom = set(urlparse(u).netloc for u in re.findall(r'href=["\'](https?://[^"\']+)["\']', raw))
    return covered / len(key), covered, len(key), len(all_dom)


def has_comparable_table(text):
    # 竞争格局章须含可比公司表：找含「市占率」或「份额」的 <table>，其 <tr> 数据行 >=3
    tables = re.findall(r"<table.*?</table>", text, re.S)
    for t in tables:
        if ("市占率" in t or "份额" in t) and ("CR" in t or "龙头" in t):
            rows = re.findall(r"<tr", t)
            if len(rows) >= 4:  # 含表头 1 行 + 数据 >=3
                return True
    return False


def check_nav(text):
    """导航模块校验：章节锚点(结构必须→P0) + 导航UI(增强→P1)。

    锚点 dim1–dim8 / conclusion / src-summary 是导航与各 section 的契约，
    缺失即破坏跳转，视为 P0 阻断；侧栏/目录卡/深色按钮为导航增强，
    缺失仅提示（P1），避免旧样本硬性不过。
    """
    p0, p1 = [], []
    anchors = ["dim1", "dim2", "dim3", "dim4", "dim5", "dim6", "dim7", "dim8",
               "conclusion", "src-summary"]
    missing = [a for a in anchors if f'id="{a}"' not in text]
    if missing:
        p0.append("P0-9 缺失章节锚点: " + ", ".join("#" + m for m in missing))
    if 'class="side-nav"' not in text:
        p1.append("P1-3 缺少桌面侧栏 .side-nav（导航模块未启用）")
    if 'class="toc-card"' not in text:
        p1.append("P1-3 缺少目录卡 .toc-card")
    if 'id="themeToggle"' not in text:
        p1.append("P1-3 缺少深色切换按钮 #themeToggle（data-theme 明暗机制缺失）")
    return p0, p1


def count_class_use(text, cls):
    """统计 body 内某组件类的实际使用次数（仅 body，排除 <style> 中的 CSS 定义）。"""
    body = extract_body(text)
    return len(re.findall(r'class="[^"]*\b' + re.escape(cls) + r'\b[^"]*"', body))


def check_five_pieces(text):
    """P0-10 内容五件套校验（v2.0 对齐七步财报版式）：
    每维度强制 人话卡/反面假设/盯什么 + 评级徽章/档位徽章/来源框；综合结论强制金色结论框。"""
    missing = []
    for cls, name in [("human-term-card", "人话卡"), ("reverse-note", "反面假设"),
                      ("insight-card", "盯什么"), ("rating-badge", "评级徽章"),
                      ("tier-badge", "可信度档位"), ("source-box", "数据来源框")]:
        n = count_class_use(text, cls)
        if n < 8:
            missing.append(f"{name}(.{cls})仅 {n} 个，要求每维度 ≥1")
    if count_class_use(text, "conclusion-wrap") < 1:
        missing.append("金色结论框(.conclusion-wrap)缺失")
    return missing


# ── v3.0 防复发门禁 ─────────────────────────────────────────────────────
def check_structure_balance(text):
    """P0-11：全文块级标签栈 + div 计数。

    2026-11-09 事故：三张风险卡各漏一个 </div>，浏览器把「数据来源汇总」
    整章吞进第三张卡，水印 10 被裁成 0。模板 CSS 无错，错在片段结构。
    另查 head 切分完整性：模板注释里出现 head 结束标签字面量会截断 <html>/CSS。
    """
    problems = hh.validate_document(text)
    if "<html" not in text:
        problems.append("<html> 起始标签缺失（head 切片被截断，整段 CSS 可能已丢）")
    return problems


def check_visual_skin(text):
    """P0-12：默认皮肤与 v3 Hero 签名结构必须在位，禁止回落到旧深空蓝。

    必须先剥离 HTML 注释：模板注释里若出现样式 id / head 结束标签等字面量，
    会把「没注入皮肤」误判成「已注入」（2026-11-09 实测踩过）。
    """
    t = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    problems = []
    # 必须查 style 块的 id，不能用「CSS 里有没有 --p-paper」代替：
    # 后者只要残留任一 token 就会放行，皮肤被改名/部分注入时查不出来。
    if not re.search(r'<style[^>]*id=["\']hydro-skin["\']', t, re.I):
        problems.append("P0-12 未注入 v3 默认皮肤（缺少 <style id=\"hydro-skin\">，"
                        "应由 render_report.py 自动注入 assets/hydro-skin.css）")
    for token, label in [("hero-masthead", "Hero 报头"), ("hero-art", "等高线签名图"),
                         ("hero-foot", "Hero 脚注区"), ("hero-content", "Hero 内容区")]:
        if token not in t:
            problems.append("P0-12 缺少 %s (.%s)" % (label, token))
    if '<div class="hero"><div class="hero-content">' in t:
        problems.append("P0-12 残留 v1 深空蓝 Hero 结构")
    if not re.search(r"--p-paper\s*:\s*#0e1215", t, re.I):
        problems.append("P0-12 缺少暗色模式 token 反相（--p-paper:#0e1215）")
    return problems


def check_motion_safety(text):
    """P0-13：入场动效只能用 transform；来源角标绝不能落进 <script>。

    两次历史坑：① `opacity:0→1` + `animation-fill-mode:both` 在截图工具 t=0
    抓帧 / JS 失效时让首屏整块文字消失；② 补链脚本把 <a class="ref"> 插进
    JS 字符串，导致整个 <script> 崩溃、兜底逻辑不执行。
    """
    problems = []
    styles = "\n".join(re.findall(r"<style\b.*?</style>", text, re.S | re.I))
    for kf in ("hydroRise", "hydroArt", "fadeIn", "reveal", "riseIn"):
        m = re.search(r"@keyframes\s+%s\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}" % kf,
                      styles, re.S | re.I)
        if m and re.search(r"opacity\s*:", m.group(1)):
            problems.append("P0-13 入场关键帧 @keyframes %s 含 opacity，"
                            "截图/无 JS 时会隐藏内容；只允许 transform" % kf)
    if re.search(r"\.reveal\s*\{[^}]*opacity\s*:\s*0", styles, re.I):
        problems.append("P0-13 .reveal 存在静态 opacity:0 初始态（无 JS 兜底会永久隐藏）")
    for s in re.findall(r"<script\b.*?</script>", text, re.S | re.I):
        if 'class="ref"' in s or "class='ref'" in s:
            problems.append("P0-13 <script> 内混入来源角标，会破坏 JS 语法")
    return problems


def check_charts(text):
    """P0-15：C1/C2/C3 三张数据图必须真实出现在成品 body 中。

    2026-11-09 审计发现：生成器文档声称三图由 charts 数据算坐标，但
    render_c1/c2/c3 从未被 build() 调用，charts 是死字段；门禁也不查三图。
    于是「删光三张图」的报告照样能通过全部 P0/P1。此检查堵住该缺口。
    """
    body = extract_body(text)
    problems = []
    n_card = len(re.findall(r'class="[^"]*chart-card', body))
    if n_card < 3:
        problems.append("P0-15 .chart-card 仅 %d 个，要求 C1/C2/C3 共 3 个" % n_card)
    specs = [
        ("C1 市场规模双序列柱状图",
         "<svg" in body and "<rect" in body
         and ("svg-bar-primary" in body or "svg-bar-energy" in body)),
        ("C2 可比公司 PE 条形图",
         "bar-chart" in body and "bar-fill" in body and "bar-row" in body),
        ("C3 八维评级雷达图", "svg-data" in body and "<polygon" in body),
    ]
    for label, ok in specs:
        if not ok:
            problems.append("P0-15 缺少 %s（或图元不完整）" % label)
    return problems


def check_placeholders(text):
    """P0-14 / P1-7：占位符与旧三色残留。"""
    body = extract_body(text)
    p0, p1 = [], []
    # head 也要查：{行业名称} / 标题占位符若没被替换，只在正文查会漏。
    for tok in ("{R(", "{{C1}}", "{{C2}}", "{{C3}}", "{行业名称}", "{日期}", "TODO"):
        if tok in text:
            p0.append("P0-14 残留占位符 %s" % tok)
    if "UNSOURCED" in body:
        p1.append("P1-7 正文残留 [UNSOURCED] 标记，需补来源或改写为降级署名")
    old = {c: body.count(c) for c in ("#635bff", "#c8943b", "#0a1628", "#4f46e5")
           if c in body}
    if old:
        p1.append("P1-7 body 内残留旧三色 hex：%s（生成器已自动映射 C1 图例，"
                  "其余请改用 --p-* token）" % old)
    return p0, p1


def main():
    argv = sys.argv[1:]
    flags = {a for a in argv if a.startswith("--")}
    paths = [a for a in argv if not a.startswith("--")]
    unknown = flags - {"--strict", "--no-strict"}
    if len(paths) != 1 or unknown:
        print("用法: python3 check_report.py <报告.html> [--strict|--no-strict]",
              file=sys.stderr)
        if unknown:
            print("未知参数: %s" % ", ".join(sorted(unknown)), file=sys.stderr)
        sys.exit(2)
    path = paths[0]
    if not os.path.isfile(path):
        print("🔴 报告文件不存在或不是文件：%s" % path, file=sys.stderr)
        sys.exit(2)
    try:
        text = load(path)
    except (OSError, UnicodeDecodeError) as e:
        print("🔴 无法读取报告：%s" % e, file=sys.stderr)
        sys.exit(2)
    plain = strip_tags(text)

    fails_p0 = []
    fails_p1 = []
    notes = []

    # ---- P0 ----
    n_card = count_method_cards(text)
    if n_card < 8:
        fails_p0.append(f"P0-1 方法卡不足 8 个（实际 {n_card}）")
    else:
        notes.append(f"P0-1 方法卡 = {n_card} ✅")

    n_deriv = count_derivation(text)
    if n_deriv < 8:
        fails_p0.append(f"P0-2 推导过程不足 8 个（实际 {n_deriv}）")
    else:
        notes.append(f"P0-2 推导过程 = {n_deriv} ✅")

    if not has_formula_recompute(text):
        fails_p0.append("P0-3 缺少可复算公式块（公式词 ≥4 + <details> 计算折叠）")
    else:
        notes.append("P0-3 可复算公式块 + 生命周期计算折叠齐全 ✅")

    urls = collect_hrefs(text)
    # 关键数字口径（排除年份/序数等非数据声明） + 独立来源数硬要求
    kcov, kcovered, ktotal, nsrc = compute_key_coverage(text)
    if kcov < 0.9:
        fails_p0.append(f"P0-4 链接邻近率 {kcov:.1%} < 90%（{kcovered}/{ktotal} 个关键数字邻近有链接）")
    else:
        notes.append(f"P0-4 链接邻近率 {kcov:.1%} ✅（{kcovered}/{ktotal} 个关键数字邻近有链接）")
    if nsrc < 10:
        fails_p0.append(f"P0-4 独立来源域名仅 {nsrc} 个 < 10（疑似单一来源复用）")
    else:
        notes.append(f"P0-4 独立来源域名 {nsrc} 个 ✅")
    bad = pure_domain_urls(urls)
    if bad:
        fails_p0.append(f"P0-4 存在纯域名首页链接（不合格）：{bad[0]}")
    else:
        notes.append("P0-4 无纯域名首页链接 ✅")

    if not chapter_has(text, ["护城河", "防守性"], ["5×4", "三问"]):
        fails_p0.append("P0-5 护城河章未出现 5×4 矩阵 + 三问验证")
    else:
        notes.append("P0-5 护城河 5×4 矩阵 + 三问验证 ✅")

    lc = lifecycle_section(text)
    if not lc:
        notes.append("P0-6 维度一章节缺失，跳过阈值校验（锚点缺失由 P0-9 阻断）")
    elif re.search(r"<\s*5%|5\s*-\s*30%|>\s*30%", html_lib.unescape(lc)):
        fails_p0.append("P0-6 生命周期章节出现旧阈值错误串（<5% / 5-30% / >30%）")
    else:
        notes.append("P0-6 生命周期章节阈值无错误串（章节级校验） ✅")

    if not has_comparable_table(text):
        fails_p0.append("P0-7 竞争格局章无可比公司份额表（≥3 家）")
    else:
        notes.append("P0-7 可比公司份额表存在 ✅")

    if not chapter_has(text, ["估值", "市值", "PE"], ["同业", "历史分位"]) and \
       not chapter_has(text, ["估值", "市值", "PE"], ["行业分位", "历史"]):
        fails_p0.append("P0-8 估值未给「相对(同业)+绝对(历史)」双视角")
    else:
        notes.append("P0-8 估值双视角 ✅")

    # ---- 导航模块校验（方案 A 新增） ----
    nav_p0, nav_p1 = check_nav(text)
    fails_p0 += nav_p0
    fails_p1 += nav_p1
    if not nav_p0:
        notes.append("P0-9 章节锚点 10/10 完整 ✅")
    if not nav_p1:
        notes.append("P1-5 导航模块(侧栏/目录卡/深色切换)完整 ✅")

    # ---- P0-10 内容五件套（v2.1 新增） ----
    five_missing = check_five_pieces(text)
    if five_missing:
        fails_p0.append("P0-10 内容五件套不齐: " + "; ".join(five_missing))
    else:
        notes.append("P0-10 内容五件套(人话卡/反面假设/盯什么/评级/档位/来源框)+金色结论框 齐全 ✅")

    # ---- P0-11 ~ P0-14：v3 防复发门禁 ----
    bal = check_structure_balance(text)
    if bal:
        fails_p0.append("P0-11 全文标签栈不平衡（%d 处）：%s"
                        % (len(bal), " | ".join(bal[:4])))
    else:
        notes.append("P0-11 全文标签栈平衡（div 计数 + 块级容器闭合） ✅")

    skin = check_visual_skin(text)
    if skin:
        fails_p0.extend(skin)
    else:
        notes.append("P0-12 v3 默认皮肤 + Hero 签名结构 + 暗色 token 齐全 ✅")

    motion = check_motion_safety(text)
    if motion:
        fails_p0.extend(motion)
    else:
        notes.append("P0-13 入场动效纯 transform / script 内无角标 ✅")

    ph_p0, ph_p1 = check_placeholders(text)
    if ph_p0:
        fails_p0.extend(ph_p0)
    else:
        notes.append("P0-14 无占位符残留 ✅")
    fails_p1.extend(ph_p1)

    charts = check_charts(text)
    if charts:
        fails_p0.extend(charts)
    else:
        notes.append("P0-15 C1/C2/C3 三张数据图齐全 ✅")

    # ---- P1 ----
    if not chapter_has(text, ["外部因素", "PEST", "政策"], ["事实", "传导", "对象", "量级", "时点"]):
        fails_p1.append("P1-1 PEST 五段链未走全（事实/传导/对象/量级/时点）")
    else:
        notes.append("P1-1 PEST 五段链走全 ✅")

    if not has_prosperity_board(text):
        fails_p1.append("P1-2 景气指标看板不完整（维度八须有含五维 + 跟踪频率的表格）")
    else:
        notes.append("P1-2 景气指标看板(五维+频率+表格)完整 ✅")

    if not has_two_method_cross(text):
        fails_p1.append("P1-3 市场规模未做「自上而下 × 自下而上」两法交叉")
    else:
        notes.append("P1-3 规模两法交叉齐全 ✅")

    if not has_structure(text):
        fails_p1.append("P1-4 结构不完整（八维卡片 / 反共识检验 / 推翻信号 / HTML 闭合）")
    else:
        notes.append("P1-4 结构完整可解析 ✅")

    if not has_as_of_timestamp(text):
        fails_p1.append("P1-6 报告头未声明数据截止时点（日期 + 时分，如 2026-11-08 22:00）")
    else:
        notes.append("P1-6 数据截止时点已声明 ✅")

    return fails_p0, fails_p1, notes


def has_formula_recompute(text):
    """P0-3：报告须含可复算公式块 + 生命周期计算 <details> 折叠块。"""
    body = extract_body(text)
    plain = strip_tags(body)
    words = ["渗透率", "UE", "CAGR", "PEG", "CCC", "TAM", "CR8", "SAM", "SOM"]
    hits = sum(1 for w in words if w in plain)
    return hits >= 4 and "<details" in body and any(op in plain for op in ("=", "÷", "×"))


def has_two_method_cross(text):
    """P1-3：维度三须同时给出自上而下与自下而上两法测算。"""
    seg = section_by_anchor(text, "dim3", "dim4")
    return bool(seg) and "自上而下" in seg and "自下而上" in seg


def has_structure(text):
    """P1-4：八维卡片齐全 + 综合结论含反共识与推翻信号 + HTML 基本闭合。"""
    seg = section_by_anchor(text, "conclusion", "src-summary")
    ok_conclusion = "反共识" in seg and "推翻信号" in seg
    ok_html = all(t in text for t in ("<html", "</html>", "<body", "</body>"))
    return count_class_use(text, "step-card") >= 8 and ok_conclusion and ok_html


def has_as_of_timestamp(text):
    """P1-6：报告头须声明数据截止时点（日期 + 时分）。"""
    i = text.find('id="dim1"')
    hero = text[:i] if i > 0 else text[:8000]
    return bool(re.search(r"20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}", hero)) and \
           any(w in hero for w in ("截至", "截止", "数据时点"))


def has_prosperity_board(text):
    """P1-2：维度八须有含五维 + 跟踪频率的表格化景气看板。

    旧实现只数全文出现「量/价/库存/订单/产能」≥4 个字，任何报告都能通过。
    """
    seg = section_by_anchor(text, "dim8", "conclusion")
    if not seg:
        return False
    dims = sum(1 for d in ["量", "价", "库存", "订单", "产能"] if d in seg)
    return dims >= 4 and "<table" in seg and "频率" in seg


if __name__ == "__main__":
    p0, p1, notes = main()
    print("=" * 56)
    print("八维报告质量门禁 · 校验结果")
    print("=" * 56)
    for n in notes:
        print("  " + n)
    print("-" * 56)
    if p0:
        print("🔴 P0 阻断项（必须返工）:")
        for f in p0:
            print("   ✗ " + f)
    if p1:
        print("🟠 P1 必改项:")
        for f in p1:
            print("   ! " + f)
    if not p0 and not p1:
        print("✅ 全部门禁通过，报告可发布。")
    print("=" * 56)
    if p0:
        sys.exit(1)
    if p1 and "--no-strict" not in sys.argv:
        sys.exit(1)
    sys.exit(0)
