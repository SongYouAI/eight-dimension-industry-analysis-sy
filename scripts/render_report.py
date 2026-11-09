#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维行业报告 · 数据驱动生成器（v3.2.2 · HYDRO PAPER 默认皮肤）
================================================================
把「来源池 → 片段结构校验 → 角标绑定 → 八维章节骨架 → v3 视觉皮肤
→ Hero 自动生成 → 三图 → 装饰符号清理 → 机械门禁」固化成一条链路。
下次出报告只改数据 JSON，**不需要再写任何 CSS / Hero HTML / 后处理注入脚本**。

用法:
    python3 render_report.py --data example_data.json --out 报告.html
    python3 render_report.py --data x.json --out y.html --no-gate
    python3 render_report.py --data x.json --out y.html --legacy-skin   # 仅用于对照旧版
    python3 render_report.py --selftest-charts      # 三图渲染自检
    python3 render_report.py --selftest-helpers     # 构造器/校验器自检

v3.0 三条硬规则（对应 2026-11-09 两次返工）:
    1. 所有 top_html / conclusion_html / sources_html / dims[].extra 片段在拼接前
       逐段跑 html_helpers.validate_fragment()，标签栈不平衡直接拒绝出稿。
    2. 默认注入 assets/hydro-skin.css 并自动把旧 Hero 升级成 v3 签名结构，
       禁止回落到深空蓝 Hero；门禁 P0-12 会再查一次。
    3. 入场动效只允许 transform，不允许 opacity:0 静态初始态（P0-13）。

数据文件字段:
    meta / sources / dims / top_html / conclusion_html / sources_html  见 example_data.json
    charts           c1/c2/c3 图表数据（**唯一推荐的图表数据源**）
                     · 在片段里写 {{C1}} / {{C2}} / {{C3}} 占位符 → 由 render_c1/c2/c3 按数值渲染
                     · 片段里已有手写精细图 → 保留手写图，charts 仍用于数值一致性校验
                     · 两者都无 → 自动把 charts 渲染结果追加到 dim3 / dim6 / 综合结论
                     绝不允许「charts 改了、图还是旧坐标」：门禁 P0-15 查三图在位。
    hero             v3 Hero 配置（缺省时由 meta 自动生成，见 default_hero_cfg）
    link_patches     raw 片段补链锚点（可选）
    branding         只认可选 url（延伸阅读）。页脚品牌溯源块为强制项，
                     文案与双二维码在 assets/brand.json，数据 JSON 关不掉（P0-16）

依赖: 仅标准库；门禁复用 references/check_report.py
"""
import argparse
import base64
import html
import json
import math
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "assets", "template.html")
SKIN = os.path.join(ROOT, "assets", "hydro-skin.css")
GATE = os.path.join(ROOT, "references", "check_report.py")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import html_helpers as hh  # noqa: E402

# 旧三色 → v3 单色 + 石灰色。数据文件里即使沿用旧 hex 也自动适配，
# 不再需要人工改 JSON（门禁 P1-7 仍会提示残留）。
LEGACY_COLOR_MAP = {
    "#635bff": "#2a4bd7", "#4f46e5": "#2a4bd7",
    "#c8943b": "#a8a293", "#d4a853": "#a8a293",
    "#0a1628": "#12181c",
}

# C2 超轴断轴标记：斜纹 + 「超轴 ×N」，避免把 154 倍 PE 画成 100% 满格误导读者。
# 集中覆盖在 <head> 末尾，遵守「优先复用模板 CSS、覆盖须集中并注明原因」。
AXIS_BREAK_CSS = (
    '<style>/* 覆盖（生成器）：C2 超轴断轴标记 */\n'
    '.bar-fill.axis-break{background:repeating-linear-gradient(45deg,var(--gold),'
    'var(--gold) 6px,rgba(200,148,59,.35) 6px,rgba(200,148,59,.35) 12px);}\n'
    '</style>\n'
)


# ── 来源与角标 ────────────────────────────────────────────────────────
def ref(sources, key):
    s = sources.get(key)
    if not s:
        return ""
    # URL 必须转义：含 & 的来源地址若不转成 &amp; 会破坏 HTML 属性并截断链接。
    return '<a class="ref" href="%s" target="_blank" rel="noopener">🔗</a>' \
           % html.escape(s["url"], quote=True)


def SRC(sources, key):
    s = sources.get(key, {})
    return s.get("title", "") + " " + ref(sources, key)


def P(text, sources, key):
    return "<p>" + text + " " + ref(sources, key) + "</p>"


def auto_link(frag, sources, key):
    """给每个不含链接的 <p> 末尾补来源角标，保证 P0-4 链接邻近率。

    门禁按 near=120 字符窗口判定；单段长度须 ≤150 字（SKILL.md 排版规则），
    否则段首数字可能落不进句末链接的窗口，需拆段。
    """
    r = ref(sources, key)
    if not r:
        return frag

    def fix(m):
        inner = m.group(1)
        if "href=" in inner:
            return m.group(0)
        return "<p>" + inner.rstrip() + " " + r + "</p>"

    return re.sub(r"<p(?:\s[^>]*)?>(.*?)</p>", fix, frag, flags=re.S)


# ── 维度骨架（五件套 + 方法卡 + 推导，全由生成器保证）────────────────
def render_dim(d, sources):
    k = d["src"]
    h = ['<div class="step-card" id="%s">' % d["id"]]
    h.append('<div class="step-head"><div class="step-num-watermark">%s</div>' % d["n"])
    h.append('<div class="step-head-text"><div class="step-num">DIMENSION %s</div>' % d["n"])
    h.append('<div class="step-title">%s</div><div class="step-sub">%s</div></div></div>' % (d["title"], d["sub"]))
    h.append('<div class="step-body">')
    h.append('<span class="tier-badge %s">%s</span> <span class="rating-badge %s">%s</span>'
             % (d["tier"][0], d["tier"][1], d["rating"][0], d["rating"][1]))
    h.append(P("<strong>核心结论：</strong>" + d["conclusion"], sources, k))

    h.append('<div class="method-card"><span class="mc-icon">📐</span><div class="mc-body">'
             '<div class="mc-title">方法卡</div>')
    for label, val in d["method"]:
        if label == "判据是什么":
            val = val + " " + ref(sources, k)
        h.append('<div class="mc-row"><b>%s</b><span>%s</span></div>' % (label, val))
    h.append("</div></div>")

    h.append("<h3>📊 关键数据</h3><div class=\"kpi-grid\">")
    for label, val, unit, delta, dc in d["kpis"]:
        h.append('<div class="kpi-card"><div class="kpi-label">%s %s</div>'
                 '<div class="kpi-value">%s<span class="kpi-unit">%s</span></div>'
                 '<div class="kpi-delta %s">%s</div> %s</div>'
                 % (label, ref(sources, k), val, unit, dc, delta, ref(sources, k)))
    h.append("</div>")

    h.append("<h3>🔍 推导过程</h3>")
    h.append(P("<strong>取数 → 口径 → 计算 → 对照阈值 → 结论 → 敏感性：</strong>"
               "本章数值取自下列来源，口径已在正文标注，计算式在正文或折叠块内给出，"
               "并已与本 Skill 判据表逐条对照。", sources, k))
    h.append("<h3>📝 深度分析</h3>")
    for para in d["paras"]:
        h.append(P(para, sources, k))
    if d.get("extra"):
        h.append(d["extra"])

    h.append("<h3>💬 小白翻译</h3>")
    h.append('<div class="human-term-card"><span class="ht-icon">💬</span><div class="ht-body">'
             '<span class="ht-term">%s：</span><span class="ht-plain">%s %s</span></div></div>'
             % (d["term"][0], d["term"][1], ref(sources, k)))
    h.append("<h3>⚖️ 反面视角</h3>")
    h.append('<div class="reverse-note"><strong>也可能是…</strong>%s %s</div>'
             % (d["reverse"], ref(sources, k)))
    h.append('<div class="insight"><strong>洞察：</strong>%s %s</div>' % (d["insight"], ref(sources, k)))
    h.append("<h3>⚠️ 风险与推翻信号</h3>")
    h.append(P("本维度最大不确定性已列于「反面视角」与下方「盯什么」。"
               "任一触发阈值被击穿，本章结论需重新检验。", sources, k))
    h.append("<h3>📌 盯什么</h3><div class=\"insight-grid\">")
    for t, desc in d["watch"]:
        h.append('<div class="insight-card"><div class="insight-icon">📌</div>'
                 '<div class="insight-title">盯什么：%s</div>'
                 '<div class="insight-desc">%s %s</div></div>' % (t, desc, ref(sources, k)))
    h.append("</div>")
    h.append('<div class="source-box"><div class="sb-title">数据来源</div>%s '
             '<span class="status-badge status-resolved">已验证</span> '
             '<a href="#src-summary">🔗 核查来源</a></div>' % SRC(sources, k))
    h.append('<p class="chapter-one"><strong>本章一句话：</strong>%s %s</p>' % (d["conclusion"], ref(sources, k)))
    h.append("</div></div>")
    return "\n".join(h)


# ── 三图：数据算坐标，禁止硬编码 <rect> ───────────────────────────────
def render_c1(c, sources):
    """C1 双序列柱状图：刻度、组距、柱高全部由数据算出（换行业数据不会画错轴）。

    旧版把 Y 轴刻度写死成 1.0/2.0/3.0、x 步长写死 160，
    axis_max 或年份数一变就出现「柱高对不上刻度」或柱子溢出 viewBox。
    """
    labels = c["labels"]
    amax = float(c["axis_max"]) or 1.0
    series = c["series"]
    left, right, top, bottom = 50, 540, 20, 290
    plot_h = bottom - top
    n = max(1, len(labels))
    group_w = (right - left) / n
    bar_w, gap = 40, 4
    ns = len(series)
    cluster_w = ns * bar_w + (ns - 1) * gap
    offset = max(0.0, (group_w - cluster_w) / 2.0)

    bars = []
    for gi, lab in enumerate(labels):
        gx = left + gi * group_w
        for si, ser in enumerate(series):
            v = ser["values"][gi]
            hgt = round(min(float(v) / amax, 1.0) * plot_h, 1)  # 超轴钳到轴顶
            y = round(bottom - hgt, 1)
            bx = round(gx + offset + si * (bar_w + gap), 1)
            bars.append('<rect x="%s" y="%s" width="%d" height="%s" rx="3" class="%s"/>'
                        % (bx, y, bar_w, hgt, ser["cls"]))
            vy = max(top + 12, y - 6)  # 数值标签不越出图表上沿
            bars.append('<text x="%s" y="%s" class="svg-val" text-anchor="middle">%s</text>'
                        % (round(bx + bar_w / 2.0, 1), round(vy, 1), v))
        bars.append('<text x="%s" y="306" class="svg-axis-text" text-anchor="middle">%s</text>'
                    % (round(gx + group_w / 2.0, 1), lab))

    axes = ['<line x1="50" y1="20" x2="50" y2="290" class="svg-axis"/>',
            '<line x1="50" y1="290" x2="540" y2="290" class="svg-axis"/>',
            '<text x="44" y="294" class="svg-axis-text" text-anchor="end">0</text>']
    for t in (1, 2, 3):
        frac = t / 3.0
        yy = round(bottom - plot_h * frac, 1)
        tick = "%g" % round(amax * frac, 2)
        axes.append('<line x1="50" y1="%s" x2="540" y2="%s" class="svg-grid"/>' % (yy, yy))
        axes.append('<text x="44" y="%s" class="svg-axis-text" text-anchor="end">%s</text>'
                    % (round(yy + 4, 1), tick))

    legend = "".join('<span><i class="swatch" style="background:%s"></i>%s</span>'
                     % (LEGACY_COLOR_MAP.get(s["color"].lower(), s["color"]), s["name"])
                     for s in series)
    return ('<div class="chart-card"><div class="chart-head">%s %s</div>'
            '<svg viewBox="0 0 560 320" role="img" aria-label="%s" style="padding:16px;">'
            '%s%s</svg><div class="legend" style="padding:0 16px 16px;">%s</div></div>'
            % (c["title"], ref(sources, c.get("ref", "")), c["title"],
               "".join(axes), "".join(bars), legend))


def render_c2(c, sources):
    """C2 可比公司 PE 条形图。超轴值用断轴斜纹 + 「超轴 ×N」，不拉满冒充满格。"""
    amax = c["axis_max"]
    rows = []
    for r in c["rows"]:
        over = r["pe"] > amax
        w = 100.0 if over else round(r["pe"] / amax * 100, 1)
        cls = "bar-fill" + (" gold" if r.get("gold") else "") + (" axis-break" if over else "")
        val = ("%s（超轴 ×%.1f）" % (r["pe"], r["pe"] / amax)) if over else str(r["pe"])
        rows.append('<div class="bar-row"><span class="bar-label">%s %s</span>'
                    '<span class="bar-track"><span class="%s" style="width:%s%%"></span></span>'
                    '<span class="bar-val">%s</span></div>'
                    % (r["name"], ref(sources, r.get("ref", "")), cls, w, val))
    return ('<div class="chart-card"><div class="chart-head">%s %s</div>'
            '<div class="bar-chart" role="img" aria-label="可比公司 PE 对比">\n%s\n</div></div>'
            % (c["title"], ref(sources, c.get("ref", "")), "\n".join(rows)))


def render_c3(c, sources):
    """C3 八维评级雷达。评分 1–3 映射到半径，顶点由公式算，不硬编码。"""
    axes = c["axes"]
    n = len(axes)
    cx, cy, radius = 160, 150, 110
    pts = []
    for i, a in enumerate(axes):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        rr = radius * a["score"] / 3.0
        pts.append("%.1f,%.1f" % (cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return ('<div class="chart-card"><div class="chart-head">%s %s</div>'
            '<svg viewBox="0 0 320 300" role="img" aria-label="八维评级雷达图">'
            '<circle cx="160" cy="150" r="110" class="svg-grid" fill="none"/>'
            '<polygon points="%s" class="svg-data"/></svg></div>'
            % (c["title"], ref(sources, c.get("ref", "")), " ".join(pts)))


# ── 图表数据校验与注入（v3.0.1 修复：charts 曾是死字段）─────────────────
# 历史缺陷：render_c1/c2/c3 定义了却从未被 build() 调用，三图实际由数据作者
# 把 SVG 硬编码进 dims[].extra；文档却声称「坐标由数值计算，禁止硬编码」。
# 结果：按文档只填 charts 会得到一份没有图的报告，而门禁也查不出来。
CHART_SLOTS = (
    # key, 占位符, 目标 dim 序号(1-based), 手写图识别标志
    ("c1", "{{C1}}", 3, ("svg-bar-primary", "svg-bar-energy")),
    ("c2", "{{C2}}", 6, ("bar-chart", "bar-fill")),
    ("c3", "{{C3}}", None, ("svg-data",)),
)


def validate_charts(charts):
    """校验 charts 结构，把 KeyError/IndexError/ZeroDivisionError 变成可读提示。

    只在 charts 存在时做；缺字段由门禁 P0-15 判「三图是否在位」。
    """
    errs = []
    if not isinstance(charts, dict):
        return ["charts 必须是对象（含 c1/c2/c3），实际为 %s" % type(charts).__name__]
    for key, _tok, _dim, _markers in CHART_SLOTS:
        c = charts.get(key)
        if not isinstance(c, dict):
            errs.append("charts.%s 缺失或不是对象" % key)
            continue
        if not c.get("title"):
            errs.append("charts.%s.title 缺失" % key)
        if key == "c1":
            labels = c.get("labels") or []
            series = c.get("series") or []
            try:
                amax = float(c.get("axis_max", 0))
            except (TypeError, ValueError):
                amax = 0
            if amax <= 0:
                errs.append("charts.c1.axis_max 必须是正数（实际 %r）" % c.get("axis_max"))
            if not labels:
                errs.append("charts.c1.labels 为空")
            if not series:
                errs.append("charts.c1.series 为空")
            for i, s in enumerate(series):
                vals = s.get("values") if isinstance(s, dict) else None
                if not isinstance(vals, list) or len(vals) != len(labels):
                    errs.append("charts.c1.series[%d].values 长度 %s 与 labels 长度 %d 不符"
                                % (i, len(vals) if isinstance(vals, list) else "非数组", len(labels)))
                    continue
                for v in vals:
                    try:
                        float(v)
                    except (TypeError, ValueError):
                        errs.append("charts.c1.series[%d].values 含非数值 %r" % (i, v))
                        break
        elif key == "c2":
            try:
                amax = float(c.get("axis_max", 0))
            except (TypeError, ValueError):
                amax = 0
            if amax <= 0:
                errs.append("charts.c2.axis_max 必须是正数（实际 %r）" % c.get("axis_max"))
            rows = c.get("rows") or []
            if not rows:
                errs.append("charts.c2.rows 为空")
            for i, r in enumerate(rows):
                try:
                    float(r.get("pe"))
                except (TypeError, ValueError):
                    errs.append("charts.c2.rows[%d].pe 非数值 %r" % (i, r.get("pe")))
        else:
            axes = c.get("axes") or []
            if not axes:
                errs.append("charts.c3.axes 为空")
            for i, a in enumerate(axes):
                try:
                    score = float(a.get("score"))
                except (TypeError, ValueError):
                    errs.append("charts.c3.axes[%d].score 非数值 %r" % (i, a.get("score")))
                    continue
                if not 0 <= score <= 3:
                    errs.append("charts.c3.axes[%d].score=%s 超出 0~3" % (i, score))
    return errs


def render_charts(charts, sources):
    """按 charts 数值渲染三图；缺某张就返回已能渲染的部分。"""
    out = {}
    if isinstance(charts.get("c1"), dict):
        out["c1"] = render_c1(charts["c1"], sources)
    if isinstance(charts.get("c2"), dict):
        out["c2"] = render_c2(charts["c2"], sources)
    if isinstance(charts.get("c3"), dict):
        out["c3"] = render_c3(charts["c3"], sources)
    return out


def inject_charts(parts, data, sources, warnings=None):
    """把 charts 渲染结果放进报告；返回（是否已处理全部三图）。

    优先级：占位符替换 > 已有手写精细图（保留，不降级）> 自动追加到默认章节。
    `parts` 已是渲染后的字符串列表：[top, dim1..dimN, conclusion, sources]。
    """
    warn = warnings.append if warnings is not None else (lambda _m: None)
    charts = data.get("charts") or {}
    if not charts:
        warn("数据文件未声明 charts：三图只能靠手写 HTML，门禁 P0-15 会核对三图是否在位")
        return parts
    errs = validate_charts(charts)
    if errs:
        raise ValueError("charts 数据结构有误：\n  - " + "\n  - ".join(errs[:10]))
    rendered = render_charts(charts, sources)
    n_dim = len(data.get("dims", []))
    concl_idx = 1 + n_dim  # parts[-2] 的显式写法

    used = set()
    for key, token, _dim, _markers in CHART_SLOTS:
        if key not in rendered:
            continue
        for i, part in enumerate(parts):
            if token in part:
                parts[i] = part.replace(token, rendered[key])
                used.add(key)

    for key, _token, dim_no, markers in CHART_SLOTS:
        if key in used or key not in rendered:
            continue
        idx = (1 + dim_no - 1) if dim_no and dim_no <= n_dim else concl_idx
        idx = min(idx, len(parts) - 1)
        target = parts[idx]
        if any(m in target for m in markers):
            # 已有手写精细图（例如 C3 带多层网格/轴标签的定制 SVG）属于正常兼容路径，
            # 不降级替换、也不打扰使用者；charts 此时作为图表数值声明参与结构校验。
            continue
        parts[idx] = target + "\n" + rendered[key]
        warn("%s：数据文件未写占位符且无手写图，已按 charts.%s 自动追加到默认章节"
             % (key.upper(), key))
    return parts


# ── 页脚：紧凑品牌溯源条（v3.2.2） ──────────────────────────────────────
# 单行署名 + 两行渠道 + 单行说明，整块 560px、小码 52px 紧跟渠道文字。
# 报告会被多级转发，页脚是唯一稳定的出处锚点。品牌常量集中在
# assets/brand.json，二维码内嵌 base64，离线打开 / 打印都不丢图。
DEFAULT_ATTRIBUTION = "八维行业分析法 · 松幽"
BRAND_JSON = os.path.join(ROOT, "assets", "brand.json")


def _esc(s):
    return html.escape(str(s), quote=True)


def load_brand():
    with open(BRAND_JSON, encoding="utf-8") as f:
        b = json.load(f)
    for key in ("wechat", "video", "qr_wechat", "qr_video"):
        if not b.get(key):
            raise ValueError("assets/brand.json 缺少必填字段 %s" % key)
    return b


def _qr_data_uri(filename):
    """返回二维码 data URI：优先读 brand.json 的 qr_*_data，回退读源图 PNG。

    SkillHub 等分发渠道只允许 .md/.py/.json/.html 等文本文件，PNG 会被
    平台 400 拒绝；图片数据放 brand.json 后，商店版不依赖 PNG 也能离线出图。
    """
    with open(BRAND_JSON, encoding="utf-8") as f:
        cfg = json.load(f)
    field = "qr_wechat_data" if filename == cfg.get("qr_wechat") else "qr_video_data"
    b64 = cfg.get(field)
    if not b64:
        path = os.path.join(os.path.dirname(BRAND_JSON), filename)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
    return "data:image/png;base64," + b64


# 点击小码放大：复用同一份 base64，不重复内嵌图片，报告体积不翻倍。
# 无外部依赖，离线打开 / 打印均可；ESC 或点击遮罩关闭。
QR_LIGHTBOX_JS = """<script>
(function(){
  var box=document.getElementById('qrLightbox');
  if(!box) return;
  var big=box.querySelector('img');
  document.addEventListener('click',function(e){
    var btn=e.target.closest && e.target.closest('.brand-qr');
    if(!btn) return;
    e.preventDefault();
    big.src=btn.querySelector('img').src;
    big.alt=btn.querySelector('img').alt;
    box.hidden=false;
  });
  box.addEventListener('click',function(){box.hidden=true;});
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape') box.hidden=true;
  });
})();
</script>"""


def render_footer(data):
    """强制输出紧凑溯源条：每个渠道一行（左介绍 + 紧跟的小码，点击放大）。

    v3.2.2：单行署名 / 两行渠道 / 单行说明，整块 560px、小码 52px。
    二维码不并排、不附图注；点小码在 qrLightbox 里放大同一张图。
    数据 JSON 的 branding 只认可选 url，其余一律忽略（P0-16 复核）。
    """
    brand = load_brand()
    override = data.get("branding") or {}
    if not isinstance(override, dict):
        raise ValueError("branding 必须是对象，参照 README 的字段说明")
    hint = _esc(brand.get("hint", "点击二维码查看大图"))
    channels = (
        ("公众号", brand["wechat"], brand["qr_wechat"]),
        ("视频号", brand["video"], brand["qr_video"]),
    )
    rows = []
    for kind, name, filename in channels:
        rows.append(
            '<div class="brand-channel">'
            '<div class="brand-channel-copy">'
            '<p class="brand-channel-name">%s「%s」</p>'
            '<p class="brand-channel-hint">%s</p>'
            '</div>'
            '<button class="brand-qr" type="button" aria-label="放大%s「%s」二维码">'
            '<img src="%s" alt="%s「%s」二维码">'
            '</button>'
            '</div>'
            % (_esc(kind), _esc(name), hint, _esc(kind), _esc(name),
               _qr_data_uri(filename), _esc(kind), _esc(name))
        )
    meta = [
        '<p class="brand-meta">',
        '<span class="brand-note">%s</span>' % _esc(brand.get("note", "")),
    ]
    if override.get("url"):
        meta.append('<span class="brand-link"><a href="%s" target="_blank" '
                    'rel="noopener">延伸阅读</a></span>' % _esc(override["url"]))
    meta.append('<span class="report-attribution">分析框架：%s</span>'
                % _esc(brand.get("method") or DEFAULT_ATTRIBUTION))
    meta.append('</p>')
    lines = [
        '<footer class="report-footer">',
        '<div class="brand-block">',
        '<p class="brand-head">'
        '<span class="brand-kicker">%s</span>'
        '<span class="brand-title">%s</span>'
        '</p>' % (_esc(brand.get("kicker", "原创出品 · 欢迎溯源")),
                  _esc(brand.get("title", ""))),
        '<div class="brand-channels">',
        "\n".join(rows),
        '</div>',
        "\n".join(meta),
        '</div>',
        '<div class="qr-lightbox" id="qrLightbox" hidden><img alt="二维码大图"></div>',
        QR_LIGHTBOX_JS,
        '</footer>',
    ]
    return "\n".join(lines) + "\n"


# ── 组装 ──────────────────────────────────────────────────────────────
def fix_axis_break(s):
    """兼容已有 raw 片段：含「超轴」的 bar-row 给 bar-fill 加断轴斜纹类。"""
    parts = re.split(r'(?=<div class="bar-row">)', s)
    out = []
    for part in parts:
        if part.startswith('<div class="bar-row">') and "超轴" in part:
            part = part.replace('class="bar-fill"', 'class="bar-fill axis-break"', 1)
            part = part.replace("（超轴）", "（超轴，已断轴）", 1)
        out.append(part)
    return "".join(out)


# ── v3 视觉与防错 ───────────────────────────────────────────────────────
def skin_block():
    """默认皮肤作为 <head> 最后一段 <style>，压过模板内置 CSS 与 AXIS_BREAK_CSS。"""
    css = open(SKIN, encoding="utf-8").read()
    return ('\n<style id="hydro-skin" data-design="HYDRO PAPER v3.0">\n'
            + css.strip() + '\n</style>\n')


def default_hero_cfg(data):
    """数据文件没写 hero 时，用 meta 自动推导 v3 Hero（禁止回落到旧深空蓝）。"""
    meta = data.get("meta", {})
    region = meta.get("region", "中国市场")
    company = meta.get("company", "")
    # 不编造时点：缺 date / as_of 时留空，由 validate_required_fields() 拒稿。
    date = meta.get("date", "")
    as_of = meta.get("as_of") or ((date + " 00:00") if date else "")
    badge = " · ".join(x for x in [meta.get("lifecycle", ""),
                                  ("案例锚点 " + company) if company else ""] if x)
    return {
        # 期号由数据文件给（meta.note_no / hero.note_no），缺省 "01"；
        # 旧版把某一份报告的 "08" 硬编码进公共生成器，别的行业也会显示 NO. 08。
        "note_no": meta.get("note_no", "01"),
        "as_of": as_of,
        "overline": "INDUSTRY ANALYSIS / " + region,
        "title_lines": [meta.get("industry", ""), "八维行业分析报告"],
        "badge": badge,
        "subtitle": "产业生命周期驱动 · 八维自适应权重 · 本报告以行业为分析主体、"
                    "公司为案例锚点，不构成投资建议。",
        "subtitle_src": "",
        "meta": [
            {"label": "数据截至", "value": meta.get("date", "") or as_of[:10]},
            {"label": "生命周期", "value": meta.get("lifecycle", "")},
            {"label": "地域范围", "value": region},
            {"label": "综合吸引力", "value": meta.get("attractiveness", "见综合结论")},
        ],
    }


def upgrade_hero(top, hero_html):
    """把旧版 Hero 元素换成 v3 签名结构。

    旧实现把右边界取到 `.main-wrap` 起点，会连带吞掉 Hero 与 main-wrap 之间的
    任何内容（导航、提示条、打印按钮等）。现在按标签栈精确找 Hero 自身的配对
    闭合标签；找不到配对时才回退到 main-wrap 策略。
    """
    m = re.search(r'<(?:div|header)\b[^>]*class\s*=\s*["\'][^"\']*\bhero\b[^"\']*["\']',
                  top, re.I)
    if not m:
        return hero_html + "\n" + top
    tm = re.match(r"<\s*([A-Za-z][\w-]*)", m.group(0))
    tag = tm.group(1).lower() if tm else "div"
    end = None
    depth = 0
    for t in re.finditer(r"<\s*(/?)\s*(div|header)\b[^>]*>", top[m.start():], re.I):
        closing, name = t.group(1), t.group(2).lower()
        if name != tag:
            continue
        if closing:
            depth -= 1
            if depth <= 0:
                end = m.start() + t.end()
                break
        else:
            depth += 1
    if end is None:
        mw = re.search(r'<div class="main-wrap"', top[m.start():])
        end = m.start() + mw.start() if mw else len(top)
    return top[:m.start()] + hero_html + "\n" + top[end:]


def validate_data_fragments(data):
    """渲染前逐片段查标签栈。`.main-wrap` 是唯一允许跨片段的容器。"""
    errs = []
    for name in ("top_html", "conclusion_html", "sources_html"):
        errs += hh.validate_fragment(data.get(name, ""), name, allow_cross_class="main-wrap")
    for i, d in enumerate(data.get("dims", []), 1):
        errs += hh.validate_fragment(d.get("extra", ""),
                                     "dims[%d].extra" % i, allow_cross_class="main-wrap")
        for j, p in enumerate(d.get("paras", [])):
            errs += hh.validate_fragment(p, "dims[%d].paras[%d]" % (i, j))
    return errs


def validate_required_fields(data):
    """⓪ 必填字段校验：把 KeyError traceback 变成可操作的中文提示。"""
    errs = []
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errs.append("缺少 meta 对象（至少要有 industry）")
    elif not meta.get("industry"):
        errs.append("meta.industry（行业名称）为空")
    if isinstance(meta, dict) and not (meta.get("as_of") or meta.get("date")):
        errs.append("meta.as_of 或 meta.date（数据截止时点）为空；"
                    "生成器不会替你编造日期，请按 P1-6 给出 YYYY-MM-DD HH:MM")
    if not isinstance(data.get("sources"), dict):
        errs.append("缺少 sources 对象（来源池 {key: {url, title}}）")
    dims = data.get("dims")
    if not isinstance(dims, list):
        errs.append("缺少 dims 数组（8 个维度）")
    elif not dims:
        errs.append("dims 数组为空——只会生成一份没有章节的废报告")
    elif len(dims) != 8:
        errs.append("dims 应有 8 个维度，实际 %d 个" % len(dims))
    for k in ("top_html", "conclusion_html", "sources_html"):
        if not data.get(k):
            errs.append("%s 为空（导航/Hero/结论/来源章节需要它）" % k)
    for i, d in enumerate(dims if isinstance(dims, list) else [], 1):
        if not isinstance(d, dict):
            errs.append("dims[%d] 不是对象" % i)
            continue
        for f in ("id", "n", "src", "title", "sub", "conclusion", "tier",
                  "rating", "method", "kpis", "paras", "term", "reverse",
                  "insight", "watch"):
            if f not in d:
                errs.append("dims[%d] 缺字段 %s（参照 example_data.json）" % (i, f))
                break
    return errs


def build(data, legacy_skin=False, keep_emoji=False, warnings=None):
    # ⓪ 必填字段
    ferrs = validate_required_fields(data)
    if ferrs:
        raise ValueError("数据文件字段不完整：\n  - " + "\n  - ".join(ferrs[:12]))
    # ① 结构门禁前置：任何一个片段标签不平衡，直接拒绝出稿
    errs = validate_data_fragments(data)
    if errs:
        raise ValueError("HTML 片段标签不平衡（%d 处），已拒绝出稿：\n  - %s"
                         % (len(errs), "\n  - ".join(errs[:12])))

    tpl = open(TPL, encoding="utf-8").read()
    # 用 rfind 取最后一个 head 结束标签：模板注释里若出现同名字符串，
    # index() 会把 head 截断在注释中途，丢掉 <html> 与整段 CSS（P1-4 曾拦下此事故）。
    h_end = tpl.rfind("</head>")
    if h_end < 0:
        raise ValueError("template.html 缺少 head 结束标签")
    head = tpl[:h_end]  # 不含 head 结束标签，注入后只补一次
    head = head.replace("{行业名称}", data["meta"]["industry"])
    if "<html" not in head:
        raise ValueError("head 切片不含 <html> 标签，模板结构可能已损坏")
    # ② 默认注入 v3 皮肤；AXIS_BREAK_CSS 在前，皮肤在后取得最高优先级。
    #    用切片拼接而非 str.replace：后者会把注释里的同名字符串也替换掉，
    #    导致皮肤被注入多次。
    inject = AXIS_BREAK_CSS if legacy_skin else AXIS_BREAK_CSS + skin_block()
    head = head + inject + "</head>"
    m = re.search(r"(<script>\s*/\* 入场动效.*?)</body>", tpl, re.S)
    tail = m.group(1) if m else ""

    sources = data["sources"]
    top = data.get("top_html", "")
    # ③ Hero 自动生成 / 自动升级：数据文件不再需要手写 Hero HTML
    if not legacy_skin:
        # 显式 hero 只覆盖它写了的字段，其余由 meta 推导补全，
        # 避免「数据文件给了 hero 但漏了 note_no / foot_left」导致首屏留白。
        cfg = default_hero_cfg(data)
        cfg.update(data.get("hero") or {})
        top = upgrade_hero(top, hh.HERO(cfg, lambda k: ref(sources, k) if k else ""))

    parts = [top]
    for d in data["dims"]:
        parts.append(auto_link(render_dim(d, sources), sources, d["src"]))
    parts.append(data.get("conclusion_html", ""))
    parts.append(data.get("sources_html", ""))
    # ③-b 三图实例化：charts 占位符 / 手写图保留 / 自动追加（见 inject_charts）
    inject_charts(parts, data, sources, warnings)
    # ③-c 导航骨架缺失只提示不静默：P1-3 会因此阻断严格门禁
    warn = warnings.append if warnings is not None else (lambda _m: None)
    for token, label in (('id="themeToggle"', "深色切换按钮"),
                         ('class="side-nav"', "侧栏导航"),
                         ('class="toc-card"', "目录卡")):
        if token not in top:
            warn("top_html 缺少%s（%s）；严格门禁 P1-3 会阻断，"
                 "请参照 scripts/example_data.json 的 top_html 补齐导航骨架" % (label, token))
    # ③-d 页脚放在最后：v3.2.2 起紧凑溯源条强制输出，无开关
    parts.append(render_footer(data))
    body = fix_axis_break("\n".join(parts))
    # 旧三色硬编码兜底：即便数据文件里仍写 #635bff / #c8943b，也统一换成
    # v3 的钴蓝 + 石灰色，避免「文字换了皮肤、图表还是紫金」的半吊子状态。
    if not legacy_skin:
        for old_c, new_c in LEGACY_COLOR_MAP.items():
            body = body.replace(old_c, new_c).replace(old_c.upper(), new_c)
    # 数据驱动的补链：raw HTML 片段（非 <p> 段落）里的关键数字由数据文件声明锚点，
    # 避免把「某个行业的某句话」硬编码进生成器。同一数字可能在多处出现，
    # 默认替换全部匹配；需要只补一处时把 after 写足以上下文即可。
    for patch in data.get("link_patches", []):
        anchor, key = patch["after"], patch["src"]
        n = patch.get("count", 0)  # 0 = 全部
        if anchor in body:
            body = body.replace(anchor, anchor + " " + ref(sources, key)) if n == 0 \
                   else body.replace(anchor, anchor + " " + ref(sources, key), n)
    doc = head + "\n<body>\n" + body + "\n" + tail + "\n</body>\n</html>\n"
    # ④ 装饰符号清理：只动 HTML 正文，跳过 script/style/注释（防「锚点插进 JS」重演）
    if not keep_emoji:
        doc, _ = hh.clean_decorative_symbols(doc)
    # ⑤ 全文再查一次，防止片段拼接后互相影响
    doc_errs = hh.validate_document(doc)
    if doc_errs:
        raise ValueError("拼接后全文标签不平衡，已拒绝出稿：\n  - %s"
                         % "\n  - ".join(doc_errs[:8]))
    return doc


def selftest_charts():
    src = {"x": {"url": "https://example.com/report/2026.html", "title": "示例"}}
    c1 = render_c1({"title": "C1", "axis_max": 3.0, "labels": ["2025", "2026E"], "ref": "x",
                    "series": [{"name": "中国", "cls": "svg-bar-primary", "color": "#635bff", "values": [2.36, 2.33]},
                               {"name": "北美", "cls": "svg-bar-energy", "color": "#c8943b", "values": [1.13, 1.49]}]}, src)
    c2 = render_c2({"title": "C2", "axis_max": 35.19, "ref": "x",
                    "rows": [{"name": "板块", "pe": 35.19, "ref": "x"},
                             {"name": "锚点", "pe": 30.7, "gold": True, "ref": "x"},
                             {"name": "超轴样本", "pe": 154.16, "ref": "x"}]}, src)
    c3 = render_c3({"title": "C3", "ref": "x",
                    "axes": [{"score": 3}, {"score": 2}, {"score": 1}, {"score": 3},
                             {"score": 2}, {"score": 2}, {"score": 3}, {"score": 1}]}, src)
    c1_alt = render_c1({"title": "C1-alt", "axis_max": 10.0,
                        "labels": ["A", "B", "C", "D"], "ref": "x",
                        "series": [{"name": "S", "cls": "svg-bar-primary",
                                    "color": "#635bff", "values": [1, 2, 3, 4]}]}, src)
    alt_ticks = re.findall(r'text-anchor="end">([^<]+)<', c1_alt)
    checks = [("C1 <rect> 由数值算出", "<rect" in c1 and "2.36" in c1),
              ("C1 刻度随 axis_max 变化", alt_ticks == ["0", "3.33", "6.67", "10"]),
              ("C1 多组不溢出 viewBox", all(float(x) + 40 <= 540
                                       for x in re.findall(r'<rect x="([\d.]+)"', c1_alt))),
              ("C2 超轴有断轴类", "axis-break" in c2 and "×4.4" in c2),
              ("C3 polygon 8 顶点", len(re.findall(r"[\d.]+,[\d.]+", c3)) == 8)]
    for name, ok in checks:
        print(("OK   " if ok else "FAIL ") + name)
    return 0 if all(ok for _, ok in checks) else 1


def main():
    ap = argparse.ArgumentParser(description="八维行业报告 · 数据驱动生成器 v3.2.2")
    ap.add_argument("--data", help="数据 JSON 路径")
    ap.add_argument("--out", help="输出 HTML 路径")
    ap.add_argument("--no-gate", action="store_true", help="生成后不自动跑机械门禁")
    ap.add_argument("--legacy-skin", action="store_true",
                    help="仅供对照：不注入 v3 皮肤、不升级 Hero（门禁会阻断）")
    ap.add_argument("--keep-emoji", action="store_true", help="保留装饰 emoji，不做符号清理")
    ap.add_argument("--selftest-charts", action="store_true", help="自检三图渲染函数")
    ap.add_argument("--selftest-helpers", action="store_true", help="自检构造器/结构校验器")
    args = ap.parse_args()
    if args.selftest_charts:
        return selftest_charts()
    if args.selftest_helpers:
        return hh.selftest()
    if not args.data or not args.out:
        ap.error("需要 --data 与 --out")
    try:
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        print("🔴 无法读取数据文件 %s：%s" % (args.data, e), file=sys.stderr)
        return 2
    except (ValueError, UnicodeDecodeError) as e:
        print("🔴 数据文件不是合法 UTF-8 JSON（%s）：%s" % (args.data, e), file=sys.stderr)
        return 2
    warnings = []
    try:
        out = build(data, legacy_skin=args.legacy_skin,
                    keep_emoji=args.keep_emoji, warnings=warnings)
    except (ValueError, KeyError, TypeError, IndexError, OSError) as e:
        print("🔴 渲染中止：\n" + str(e), file=sys.stderr)
        return 2
    for w in warnings:
        print("🟠 " + w, file=sys.stderr)
    try:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
    except OSError as e:
        print("🔴 无法写入输出文件 %s：%s" % (args.out, e), file=sys.stderr)
        return 2
    print("已生成: %s | 字符数: %d | 皮肤: %s"
          % (args.out, len(out), "legacy(对照)" if args.legacy_skin else "HYDRO PAPER v3.2.2"))
    if not args.no_gate:
        if not os.path.isfile(GATE):
            print("🔴 找不到门禁脚本 %s（skill 目录不完整）" % GATE, file=sys.stderr)
            return 2
        r = subprocess.run([sys.executable, GATE, args.out], capture_output=True, text=True)
        print(r.stdout.rstrip())
        if r.stderr.strip():
            print(r.stderr.rstrip(), file=sys.stderr)
        print("门禁退出码:", r.returncode)
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
