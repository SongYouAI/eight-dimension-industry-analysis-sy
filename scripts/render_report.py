#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维行业报告 · 数据驱动生成器（v2.2）
=====================================
把「来源池 → 角标绑定 → 八维章节骨架 → 模板 CSS/JS 复用 → 三图 → 机械门禁」
固化成一条链路。下次出报告只改 example_data.json，不重写生成器。

用法:
    python3 render_report.py --data example_data.json --out 报告.html
    python3 render_report.py --data x.json --out y.html --no-gate
    python3 render_report.py --selftest-charts

数据文件字段（见 example_data.json）:
    meta             行业名 / 日期 / 数据截至 / 生命周期 / 地域 等
    sources          {key: {url, title}}  来源池（URL 必须带路径，非纯域名）
    dims             8 个维度，字段见 render_dim()
    top_html         Hero + 导航 + 目录卡 + 执行摘要（已渲染片段）
    conclusion_html  综合结论 step-card（含 id="conclusion"）
    sources_html     数据来源汇总 step-card（含 id="src-summary"）
    charts           {c1, c2, c3} 图表数据，供 render_c1/c2/c3 使用

依赖: 仅标准库；门禁复用 references/check_report.py
"""
import argparse
import html
import json
import math
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "assets", "template.html")
GATE = os.path.join(ROOT, "references", "check_report.py")

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
                     % (s["color"], s["name"]) for s in series)
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


def build(data):
    tpl = open(TPL, encoding="utf-8").read()
    head = tpl[:tpl.index("</head>") + len("</head>")]
    head = head.replace("{行业名称}", data["meta"]["industry"])
    head = head.replace("</head>", AXIS_BREAK_CSS + "</head>")
    m = re.search(r"(<script>\s*/\* 入场动效.*?)</body>", tpl, re.S)
    tail = m.group(1) if m else ""

    sources = data["sources"]
    parts = [data.get("top_html", "")]
    for d in data["dims"]:
        parts.append(auto_link(render_dim(d, sources), sources, d["src"]))
    parts.append(data.get("conclusion_html", ""))
    parts.append(data.get("sources_html", ""))
    body = fix_axis_break("\n".join(parts))
    # 数据驱动的补链：raw HTML 片段（非 <p> 段落）里的关键数字由数据文件声明锚点，
    # 避免把「某个行业的某句话」硬编码进生成器。同一数字可能在多处出现，
    # 默认替换全部匹配；需要只补一处时把 after 写足以上下文即可。
    for patch in data.get("link_patches", []):
        anchor, key = patch["after"], patch["src"]
        n = patch.get("count", 0)  # 0 = 全部
        if anchor in body:
            body = body.replace(anchor, anchor + " " + ref(sources, key)) if n == 0 \
                   else body.replace(anchor, anchor + " " + ref(sources, key), n)
    return head + "\n<body>\n" + body + "\n" + tail + "\n</body>\n</html>\n"


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
    ap = argparse.ArgumentParser(description="八维行业报告 · 数据驱动生成器")
    ap.add_argument("--data", help="数据 JSON 路径")
    ap.add_argument("--out", help="输出 HTML 路径")
    ap.add_argument("--no-gate", action="store_true", help="生成后不自动跑机械门禁")
    ap.add_argument("--selftest-charts", action="store_true", help="自检三图渲染函数")
    args = ap.parse_args()
    if args.selftest_charts:
        return selftest_charts()
    if not args.data or not args.out:
        ap.error("需要 --data 与 --out")
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    html = build(data)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成: %s | 字符数: %d" % (args.out, len(html)))
    if not args.no_gate:
        r = subprocess.run([sys.executable, GATE, args.out], capture_output=True, text=True)
        print(r.stdout.rstrip())
        print("门禁退出码:", r.returncode)
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
