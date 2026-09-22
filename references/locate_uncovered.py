#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维报告 · 返工定位器（P0-4 关键数字链接覆盖率诊断）
====================================================
check_report.py 只告诉你「覆盖率 19% < 90%」，不告诉你「哪 120 个数字漏了」。
没有定位信息就只能盲改。本脚本复用 check_report 的**同一套口径常量**，
逐条列出未覆盖数字及其上下文，并给出按章节聚合的补链建议点位。

用法:
    python3 locate_uncovered.py <报告.html>
    python3 locate_uncovered.py <报告.html> --ctx 120    # 上下文宽度（默认 90）
    python3 locate_uncovered.py <报告.html> --sections   # 只输出按章节聚合
    python3 locate_uncovered.py -h                       # 查看完整帮助

退出码: 0 = 已达标 / 正常输出；2 = 参数或文件错误
依赖: 仅标准库 + 同目录 check_report.py
"""
import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_report as cr  # noqa: E402

# 章节锚点顺序（与模板/side-nav 契约一致）
SECTIONS = [
    ("hero", "报告头部 / 执行摘要"),
    ("dim1", "维度一 行业概览与生命周期"),
    ("dim2", "维度二 商业模式可行性"),
    ("dim3", "维度三 市场规模与空间"),
    ("dim4", "维度四 护城河与防守性"),
    ("dim5", "维度五 竞争格局与盈利性"),
    ("dim6", "维度六 估值分析"),
    ("dim7", "维度七 外部驱动力（PEST）"),
    ("dim8", "维度八 景气度跟踪"),
    ("conclusion", "综合结论"),
    ("src-summary", "数据来源汇总"),
]


def section_spans(raw):
    """在 strip_noise 后的坐标系里，定位每个章节的字符区间。"""
    marks = []
    for sid, _label in SECTIONS:
        pat = f'id="{sid}"'
        i = raw.find(pat)
        marks.append((i if i >= 0 else 10 ** 9, sid))
    # hero / exec-summary 没有 id，用 class 兜底
    for cls, sid in [('class="hero"', "hero"), ('class="exec-summary"', "hero")]:
        i = raw.find(cls)
        if i >= 0:
            marks.append((i, sid))
    marks.sort()
    spans = []
    for k, (start, sid) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(raw)
        spans.append((start, end, sid))
    return spans


def which_section(pos, spans):
    for a, b, sid in spans:
        if a <= pos < b:
            return sid
    return "?"


def parse_args(argv=None):
    """参数解析（argparse：自带 -h/--help、类型校验与规范退出码）。"""
    ap = argparse.ArgumentParser(
        prog="locate_uncovered.py",
        description="八维报告返工定位器：列出 P0-4 门禁判定为「未覆盖」的关键数字。"
                    "复用 check_report.py 的同一套口径常量，因此判定结果与门禁完全一致。",
        epilog="提示：数字落在 style/href/src 属性值内会被自动排除；"
               "SVG 与 <table> 内的数字不计入分母（无需为其补链）。"
               "补链杠杆点：门禁按 near=120 字符窗口 + 整段 <a> 锚点判定，"
               "长句句末插 1 个链接即可覆盖其前 120 字内的数字。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("report", metavar="报告.html", help="八维分析报告 HTML 文件路径")
    ap.add_argument("--ctx", type=int, default=90, metavar="N",
                    help="未覆盖数字的上下文显示宽度，默认 90 字符")
    ap.add_argument("--sections", action="store_true",
                    help="只输出按章节聚合的统计视图（不逐条列出）")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    path = args.report
    ctx = max(0, args.ctx)
    only_sections = args.sections

    if not os.path.isfile(path):
        print(f"❌ 文件不存在：{path}", file=sys.stderr)
        sys.exit(2)

    try:
        text = io.open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"❌ 无法读取文件：{path}\n   {e}", file=sys.stderr)
        sys.exit(2)
    raw = cr.strip_noise(cr.extract_body(text))
    anchors = cr.link_anchors(raw)
    spans_attr = [(m.start(), m.end()) for m in
                  re.finditer(r'(style|href|src)=["\'][^"\']*["\']', raw, re.I)]

    def in_attr(p):
        return any(a <= p < b for a, b in spans_attr)

    key = [n for n in re.finditer(r"\d[\d,.%]*", raw)
           if cr.is_key_number(n.group()) and not in_attr(n.start())]
    uncovered = [n for n in key if not cr.num_covered(n.start(), n.end(), anchors)]

    kcov, kcov_n, ktot, nsrc = cr.compute_key_coverage(text)

    # 通过线：covered/total ≥ 0.9 ⇒ covered ≥ ceil(0.9*total)
    need_covered = -(-9 * ktot // 10)          # ceil(0.9 * ktot)
    allowed_miss = ktot - need_covered          # 最多可留的未覆盖数
    gap = max(0, len(uncovered) - allowed_miss)  # 至少还需补链的数字数

    print("=" * 78)
    print("八维报告 · P0-4 关键数字链接覆盖率诊断")
    print("=" * 78)
    print(f"  文件            : {os.path.basename(path)}")
    print(f"  当前覆盖率      : {kcov:.1%}  （已覆盖 {kcov_n}/{ktot}）")
    print(f"  独立来源域名    : {nsrc} 个（P0 要求 ≥10）")
    print(f"  未覆盖数字      : {len(uncovered)} 个（通过线最多可留 {allowed_miss} 个）")
    print(f"  至少还需补链    : {gap} 个" + ("　✅ 已达标" if gap == 0 else ""))
    print("-" * 78)

    secs = section_spans(raw)
    bucket = {}
    for n in uncovered:
        bucket.setdefault(which_section(n.start(), secs), []).append(n)

    label_map = dict(SECTIONS)

    if only_sections:
        print("按章节聚合：")
        for sid, _ in SECTIONS:
            items = bucket.get(sid, [])
            if items:
                print(f"  ✗ {label_map.get(sid, sid):<28} 未覆盖 {len(items):>3} 个")
        print("=" * 78)
        sys.exit(0)

    if not uncovered:
        print("✅ 无未覆盖关键数字，P0-4 直接通过。")
        print("=" * 78)
        sys.exit(0)

    for sid, _ in SECTIONS:
        items = bucket.get(sid, [])
        if not items:
            continue
        print(f"\n▍{label_map.get(sid, sid)}  ·  未覆盖 {len(items)} 个")
        for n in items:
            s = max(0, n.start() - ctx)
            pre = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw[s:n.start()]))
            post = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw[n.end():n.end() + 40]))
            print(f"   «{n.group()}» …{pre}【{n.group()}】{post}")
        print(f"   → 建议：在本段句末补 1 个 <a class=\"ref\" href=\"…\">[n]</a>；"
              f"门禁按 near=120 字符窗口判定，句末单链即可覆盖其前 120 字内的数字。")

    print("\n" + "-" * 78)
    print("提示：数字落在 style/href/src 属性值内会被自动排除；")
    print("      SVG 与 <table> 内的数字不计入分母（无需为其补链）。")
    print("=" * 78)


if __name__ == "__main__":
    main()
