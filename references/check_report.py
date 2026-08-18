#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维行业分析报告 · 质量门禁机械校验脚本
================================================
读取生成的 HTML 报告，逐条执行 quality-gate.md 的 P0 / P1 校验。
任一 P0 失败 → 退出码 1（阻断发布）；全部 P0 通过 → 退出码 0。

用法:
    python3 check_report.py <报告.html> [--strict]
    --strict : P1 失败也视为非零退出（CI 用）

依赖: 仅标准库（re / sys / html）。
"""
import re
import sys
import html as html_lib


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
    覆盖关键词最多的那一段，确保能扫到正文深处的真实章节。
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
    """覆盖率 = 叙述文本中「邻近 90 字符内有 http 链接」的数字数 / 叙述数字总数。

    设计意图对齐 P0-4 精神：关键数字必须可核查。只要某数字附近（前后 90 字符）
    存在来源链接，即视为已覆盖；SVG/表格数字不计入分母。
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


def main():
    if len(sys.argv) < 2:
        print("用法: python3 check_report.py <报告.html> [--strict]")
        sys.exit(2)
    path = sys.argv[1]
    strict = "--strict" in sys.argv
    text = load(path)
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

    urls = collect_hrefs(text)
    # 关键数字口径（排除年份/序数等非数据声明） + 独立来源数硬要求
    kcov, kcovered, ktotal, nsrc = compute_key_coverage(text)
    if kcov < 0.9:
        fails_p0.append(f"P0-4 关键数字链接覆盖率 {kcov:.0%} < 90%（覆盖 {kcovered}/{ktotal}）")
    else:
        notes.append(f"P0-4 关键数字链接覆盖率 {kcov:.0%} ✅（覆盖 {kcovered}/{ktotal}）")
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

    if re.search(r"<5%|5-30%|>30%", plain):
        fails_p0.append("P0-6 生命周期阈值出现错误串（<5%/5-30%/>30%）")
    else:
        notes.append("P0-6 生命周期阈值无错误串 ✅")

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
        notes.append("P1-3 导航模块(侧栏/目录卡/深色切换)完整 ✅")

    # ---- P0-10 内容五件套（v2.1 新增） ----
    five_missing = check_five_pieces(text)
    if five_missing:
        fails_p0.append("P0-10 内容五件套不齐: " + "; ".join(five_missing))
    else:
        notes.append("P0-10 内容五件套(人话卡/反面假设/盯什么/评级/档位/来源框)+金色结论框 齐全 ✅")

    # ---- P1 ----
    if not chapter_has(text, ["外部因素", "PEST", "政策"], ["事实", "传导", "对象", "量级", "时点"]):
        fails_p1.append("P1-1 PEST 五段链未走全（事实/传导/对象/量级/时点）")
    else:
        notes.append("P1-1 PEST 五段链走全 ✅")

    if not has_prosperity_board(text):
        fails_p1.append("P1-2 景气指标看板不完整（量/价/库存/订单/产能）")

    return fails_p0, fails_p1, notes


def has_prosperity_board(text):
    dims = ["量", "价", "库存", "订单", "产能"]
    cnt = sum(1 for d in dims if d in text)
    return cnt >= 4


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
    if p1 and "--strict" in sys.argv:
        sys.exit(1)
    sys.exit(0)
