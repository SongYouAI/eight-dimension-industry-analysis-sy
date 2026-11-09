#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八维行业报告 · 安全 HTML 片段构造器 + 结构校验（v3.0）
================================================================
背景（2026-11-09 排版事故）：
    手写数据文件时用 `D(cls, inner)` 只闭合一层 <div>，但三张风险卡的
    inner 里各带一个未闭合的 <div class="risk-card-desc">。浏览器被迫把
    后面的「数据来源汇总」整章吞进第三张风险卡，水印 10 被裁成 0。
    模板 CSS 没有错，错在**数据片段的标签不平衡**，而当时门禁不查这个。

因此本模块提供两道防线：
    1) `D / P / RISK / SWOT / CONFLICT / HERO` 等构造器：所有块级标签显式闭合，
       且 D() 会拒绝结构化 inner（防止再把它当纯文本卡用）。
    2) `validate_fragment / validate_document`：渲染前逐片段校验标签栈，
       渲染后由 references/check_report.py 再查一遍全文（P0-11）。

用法（写数据文件时）：
    import sys; sys.path.insert(0, "<skill>/scripts")
    import html_helpers as hh
    from render_report import ref
    R = lambda k: ref(SOURCES, k)
    html = hh.RISK("risk-high", "01", "高", "来水波动", "……", R("gu_energy"))

仅依赖标准库。
"""
import re

# 只校验「一旦悬空会吞噬后续内容」的块级容器。
# <p>/<span>/<a> 由浏览器自动闭合，不纳入栈，避免正常写法被误杀。
BLOCK_TAGS = {
    "div", "details", "table", "thead", "tbody", "tfoot", "tr", "td", "th",
    "ul", "ol", "li", "section", "aside", "header", "footer", "main", "article",
    "svg", "figure", "figcaption", "blockquote",
}

# 装饰性 emoji → 印刷体标记 / 空。长串在前，避免先删短串留下悬挂空格。
# 注意：🌙 / ☀️ 不在表内（主题切换按钮要用），⚠️ 会被清掉 → 正文改用「注意：」措辞。
EMOJI_MAP = [
    ("⚠️ ", ""), ("⚠️", ""),
    ("📐 ", ""), ("📐", ""),
    ("💬 ", ""), ("💬", ""),
    ("📌 ", ""), ("📌", ""),
    ("⚡ ", ""), ("⚡", ""),
    ("📑 ", ""), ("📑", ""),
    ("⚖️ ", ""), ("⚖️", ""),
    ("📊 ", ""), ("📊", ""),
    ("🔍 ", ""), ("🔍", ""),
    ("📝 ", ""), ("📝", ""),
    ("💡 ", ""), ("💡", ""),
    ("🔗", "↗"),
    ("🔴", ""), ("🟠", ""), ("🔵", ""),
    ("🟢", ""), ("🟡", ""),
]


# ── 结构校验 ────────────────────────────────────────────────────────────
def _strip_noise(s):
    """剔除注释 / script / style：字符串里出现的 '<div' 不能算作真实标签。"""
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<script\b.*?</script>", "", s, flags=re.S | re.I)
    s = re.sub(r"<style\b.*?</style>", "", s, flags=re.S | re.I)
    return s


def validate_fragment(frag, name="fragment", allow_cross_class=None):
    """返回错误描述列表；空列表表示块级标签栈平衡。

    `allow_cross_class` 用于「跨片段容器」：本 skill 的 `.main-wrap` 在
    top_html 打开、在 sources_html 末尾关闭，逐片段校验时会有意一开一缺。
    传入 "main-wrap" 即允许**本片段内**跳过 1 个该 class 的开标签、并容忍
    1 个孤立 </div>。全文校验（validate_document）不传该参数，仍会严格查平衡。
    """
    s = _strip_noise(frag or "")
    stack = []
    errors = []
    cross_close_budget = 1 if allow_cross_class else 0
    for m in re.finditer(r"<\s*(/?)\s*([A-Za-z][\w-]*)\b[^>]*?(/?)\s*>", s):
        closing, tag, self_closing = m.group(1), m.group(2).lower(), m.group(3)
        if tag not in BLOCK_TAGS or self_closing:
            continue
        pos = m.start()
        ctx = s[max(0, pos - 50):pos + 70].replace("\n", " ")
        cls = re.search(r'class\s*=\s*["\']([^"\']*)["\']', m.group(0), re.I)
        is_cross = (not closing and allow_cross_class and cls
                    and allow_cross_class in cls.group(1).split())
        if is_cross:
            continue  # 跨片段容器：本片段不负责闭合
        if closing:
            if stack and stack[-1][0] == tag:
                stack.pop()
            elif any(t == tag for t, _, _ in stack):
                errors.append("[%s] 标签乱序闭合 </%s> @%d，前文仍有 %d 个未闭合容器；上下文: %s"
                              % (name, tag, pos, len(stack), ctx))
                while stack and stack[-1][0] != tag:
                    t, p, _ = stack.pop()
                    errors.append("[%s] 未闭合 <%s> @%d（被 </%s> 强制回滚）" % (name, t, p, tag))
                if stack:
                    stack.pop()
            elif tag == "div" and not stack and cross_close_budget > 0:
                # 仅当本片段自身栈已清空时才容忍孤立 </div>——那必然是
                # .main-wrap 的跨片段闭合。若栈里还有别的未闭合容器，
                # 这个多余的 </div> 属于真实结构错误，不能被预算吞掉。
                cross_close_budget -= 1
            else:
                errors.append("[%s] 孤立闭合标签 </%s> @%d；上下文: %s" % (name, tag, pos, ctx))
        else:
            stack.append((tag, pos, ctx))
    for tag, pos, ctx in stack:
        errors.append("[%s] 未闭合 <%s> @%d；上下文: %s" % (name, tag, pos, ctx))
    return errors


def validate_document(html_text):
    """全文校验（供门禁 P0-11 调用）：div 计数 + 块级标签栈。"""
    body = html_text
    m = re.search(r"<body[^>]*>(.*)</body>", html_text, re.S | re.I)
    if m:
        body = m.group(1)
    problems = []
    opens = len(re.findall(r"<div\b", body, re.I))
    closes = len(re.findall(r"</div\s*>", body, re.I))
    if opens != closes:
        problems.append("div 数量不平衡：<div>=%d, </div>=%d（差 %+d）"
                        % (opens, closes, opens - closes))
    problems.extend(validate_fragment(body, "document"))
    return problems


# ── 装饰符号清理（跳过 script / style / 注释，避免重演「锚点插进 JS」陷阱）──
def clean_decorative_symbols(text):
    """只替换 HTML 正文与属性文本，绝不触碰 <script>/<style>/注释。"""
    parts = re.split(r"(<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->)",
                     text, flags=re.S | re.I)
    stats = {}
    for i in range(0, len(parts), 2):
        seg = parts[i]
        for src, dst in EMOJI_MAP:
            n = seg.count(src)
            if n:
                stats[src] = stats.get(src, 0) + n
                seg = seg.replace(src, dst)
        parts[i] = seg
    return "".join(parts), stats


# ── 安全构造器 ──────────────────────────────────────────────────────────
def _assert_plain(inner, ctor):
    """D() 只接受纯文本：出现块级标签即拒绝，逼调用方改用专用构造器。"""
    bad = re.findall(r"<(div|table|ul|li|details|svg|section)\b", inner or "", re.I)
    if bad:
        raise ValueError(
            "%s() 的 inner 含块级标签 <%s>，会重演 v1 嵌套事故；"
            "请改用 RISK / SWOT / CONFLICT 或自行显式闭合所有子标签。"
            % (ctor, ", <".join(sorted(set(bad)))))


def P(text, ref_html=""):
    """段落：文本 + 可选来源角标，显式闭合。"""
    return "<p>%s %s</p>" % (text, ref_html)


def D(cls, inner, ref_html=""):
    """纯文本卡片。禁止传入含块级标签的 inner（防嵌套事故）。"""
    _assert_plain(inner, "D")
    return '<div class="%s">%s %s</div>' % (cls, inner, ref_html)


def RISK(cls, idx, sev, title, desc, ref_html=""):
    """风险卡：四层 div 全部显式闭合。"""
    return ('<div class="risk-card %s">'
            '<div class="risk-top"><span class="risk-idx">%s</span>'
            '<span class="risk-sev">%s</span></div>'
            '<div class="risk-card-title">%s</div>'
            '<div class="risk-card-desc">%s %s</div>'
            '</div>') % (cls, idx, sev, title, desc, ref_html)


def SWOT(cls, head, desc, ref_html=""):
    """SWOT 单元：h4 + p 显式闭合。"""
    return ('<div class="swot-cell %s"><h4>%s</h4>'
            '<p>%s %s</p></div>') % (cls, head, desc, ref_html)


def CONFLICT(label, dot, tag, arrow, ref_html=""):
    """冲突检测行：三个 span 显式闭合。"""
    return ('<div class="conflict-row"><span class="conflict-label">%s</span>'
            '<span class="conflict-tag"><span class="dot %s"></span>%s</span>'
            '<span class="conflict-arrow">%s %s</span></div>') % (
                label, dot, tag, arrow, ref_html)


# ── Hero（v3 默认签名元素，生成器调用）───────────────────────────────────
# 历史教训：SVG 内的 <text> 注记会被截图 slice 裁切并压住 masthead / 元信息，
# 因此所有注记一律放在 .hero-foot，SVG 内只留线条与站点圆点。
HERO_ART = """<svg class="hero-art" viewBox="0 0 720 520" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
<circle class="ring" cx="560" cy="210" r="152"/><circle class="ring" cx="560" cy="210" r="96"/>
<path class="contour strong" d="M -60 470 C 120 430 220 350 380 370 S 620 280 780 310"/>
<path class="contour" d="M -60 442 C 120 402 220 322 380 342 S 620 252 780 282"/>
<path class="contour" d="M -60 414 C 120 374 220 294 380 314 S 620 224 780 254"/>
<path class="contour strong" d="M -60 386 C 120 346 220 266 380 286 S 620 196 780 226"/>
<path class="contour" d="M -60 358 C 120 318 220 238 380 258 S 620 168 780 198"/>
<path class="contour" d="M -60 330 C 120 290 220 210 380 230 S 620 140 780 170"/>
<path class="contour strong" d="M -60 302 C 120 262 220 182 380 202 S 620 112 780 142"/>
<path class="contour" d="M -60 274 C 120 234 220 154 380 174 S 620 84 780 114"/>
<path class="contour" d="M -60 246 C 120 206 220 126 380 146 S 620 56 780 86"/>
<path class="contour strong" d="M -60 218 C 120 178 220 98 380 118 S 620 28 780 58"/>
<path class="river" d="M -40 500 C 140 470 180 360 330 350 S 470 260 560 250 S 690 180 780 150"/>
<circle class="station" cx="180" cy="410" r="4"/><circle class="station" cx="400" cy="320" r="4"/><circle class="station" cx="600" cy="230" r="4"/>
<line class="tick" x1="560" y1="42" x2="560" y2="58"/><line class="tick" x1="560" y1="362" x2="560" y2="378"/>
</svg>"""


def HERO(cfg, R=None):
    """生成 v3「水文纸本」Hero。cfg 字段见 render_report.default_hero_cfg()。

    `cfg["note_no"]` 同时用于 masthead 的「RESEARCH NOTE · NO. xx」与
    h1 的 data-note 装饰（CSS 用 attr() 读取），两份编号始终一致。
    R 是 `lambda key: ref_html` 的来源角标函数；缺省时不出角标。
    """
    R = R or (lambda k: "")
    title = "<br>".join(cfg.get("title_lines") or ["八维行业分析报告"])
    metas = []
    for i, m in enumerate(cfg.get("meta") or []):
        metas.append('<div class="mt"><span class="mt-l">%s</span>'
                     '<span class="mt-v">%s %s</span></div>'
                     % (m.get("label", ""), m.get("value", ""), R(m.get("src", ""))))
    return (
        '<header class="hero">\n'
        + HERO_ART + '\n'
        + '<div class="hero-content">\n'
        + '<div class="hero-masthead"><span class="mh-left">RESEARCH NOTE · NO. %s</span>'
          '<span>数据截至 %s</span></div>\n' % (cfg.get("note_no", "08"), cfg.get("as_of", ""))
        + '<div class="hero-overline">%s</div>\n' % cfg.get("overline", "INDUSTRY ANALYSIS")
        + '<h1 data-note="%s">%s</h1>\n' % (cfg.get("note_no", ""), title)
        + '<div class="badge">%s</div>\n' % cfg.get("badge", "")
        + '<p class="subtitle">%s %s</p>\n' % (cfg.get("subtitle", ""), R(cfg.get("subtitle_src", "")))
        + '<div class="meta-row">\n' + "\n".join(metas) + '\n</div>\n'
        + '<div class="hero-foot"><span>%s</span><span class="hero-note">%s</span>'
          '<span class="scroll-line"></span></div>\n' % (
              cfg.get("foot_left", "SCROLL TO EXPLORE · 10 SECTIONS"),
              cfg.get("foot_note", "CONTOUR ART · SCHEMATIC / NOT TO SCALE"))
        + '</div>\n</header>'
    )


def selftest():
    """构造器自检：故意构造事故片段，确认校验器能抓到。"""
    R = lambda k: '<a class="ref" href="https://example.com/a/b">↗</a>'
    good = ('<div class="risk-grid">'
            + RISK("risk-high", "01", "高", "来水波动", "描述文字", R("x"))
            + RISK("risk-warn", "02", "中", "电价压制", "描述文字", R("x"))
            + RISK("risk-info", "03", "低", "利率反转", "描述文字", R("x"))
            + '</div>')
    bad = '<div class="risk-card"><div class="risk-card-title">标题</div><div class="risk-card-desc">说明'
    cases = [
        ("三张风险卡严格闭合", validate_fragment(good, "risk-grid") == []),
        ("v1 事故片段能被检出", len(validate_fragment(bad, "risk-card")) >= 2),
        ("D() 拒绝结构化 inner", _raises(lambda: D("x", '<div class="a">文本'))),
        ("HERO 结构自带签名元素", all(x in HERO({"title_lines": ["测试"]}) for x in
                                 ("hero-masthead", "hero-art", "hero-foot", "hero-content"))),
        ("注释里的 <div> 不算标签", validate_fragment("<!-- <div> -->\n<p>文本</p>", "note") == []),
        ("script 里的 <div> 不算标签",
         validate_fragment('<script>var s="<div>";</script><div class="a">x</div>', "js") == []),
    ]
    for n, ok in cases:
        print(("OK   " if ok else "FAIL ") + n)
    return 0 if all(ok for _, ok in cases) else 1


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
