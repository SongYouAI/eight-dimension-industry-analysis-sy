#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八维行业分析 Skill · 一键回归自检（分享 / 改版前必跑）
=========================================================
不联网、不依赖 Chrome、不改 skill 内任何文件；只用标准库 + 可选 node。

覆盖：
  1. 全部 Python 脚本语法编译
  2. 构造器 / 三图渲染函数自检
  3. 用 scripts/example_data.json 跑完整出稿链路 + 严格门禁 + JS 验收 + 幂等性
  4. 边界输入：坏 JSON / 缺字段 / charts 数值错 / 标签不平衡 / 占位符替换 / 中文路径
  5. 故意破坏拦截：删 </div> / 去皮肤 / 删三图 / 静态 opacity / script 内角标
  6. 文档中的相对文件引用是否都存在

用法:
    python3 scripts/selftest_all.py
    python3 scripts/selftest_all.py --verbose     # 打印每条用例的命令输出

退出码: 0 全通过 / 1 有失败 / 2 环境错误（skill 目录不完整）
"""
import argparse
import json
import os
import pathlib
import py_compile
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REFS = ROOT / "references"
RENDER = SCRIPTS / "render_report.py"
GATE = REFS / "check_report.py"
CHECKJS = REFS / "check_js.py"
EXAMPLE = SCRIPTS / "example_data.json"
CAPTURE = SCRIPTS / "capture.py"

VERBOSE = False
RESULTS = []


def run(cmd, cwd=None, timeout=180):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # 自检不在 skill 目录留 __pycache__
    return subprocess.run([str(x) for x in cmd], capture_output=True, text=True,
                          cwd=str(cwd or ROOT), timeout=timeout, env=env)


def check(label, ok, detail="", r=None):
    RESULTS.append((label, bool(ok), detail))
    print(("  OK   " if ok else "  FAIL ") + label + (("  — " + detail) if detail else ""))
    if not ok and VERBOSE and r is not None:
        print("        " + ((r.stdout or "") + (r.stderr or "")).strip()[:600].replace("\n", "\n        "))
    return bool(ok)


def env_check():
    missing = [str(p.relative_to(ROOT)) for p in
               (RENDER, GATE, CHECKJS, EXAMPLE, CAPTURE,
                ROOT / "assets/template.html", ROOT / "assets/hydro-skin.css",
                SCRIPTS / "html_helpers.py")
               if not p.is_file()]
    if missing:
        print("skill 目录不完整，缺文件：%s" % ", ".join(missing), file=sys.stderr)
        sys.exit(2)


def section(title):
    print("\n" + title)


def strip_chart_cards(t):
    """精确删除全部 .chart-card 块（保持标签栈平衡），用于验证 P0-15。"""
    out, pos = [], 0
    while True:
        i = t.find('<div class="chart-card">', pos)
        if i < 0:
            out.append(t[pos:])
            break
        out.append(t[pos:i])
        depth, j = 0, i
        for m in re.finditer(r"<div\b|</div>", t[i:]):
            depth += -1 if m.group(0).startswith("</") else 1
            if depth == 0:
                j = i + m.end()
                break
        pos = j
    return "".join(out)


def main():
    global VERBOSE
    ap = argparse.ArgumentParser(description="八维行业分析 skill 一键回归自检")
    ap.add_argument("--verbose", action="store_true", help="打印失败用例的完整输出")
    VERBOSE = ap.parse_args().verbose
    env_check()
    print("八维行业分析 Skill · 一键回归自检")
    print("skill 根目录: %s" % ROOT)

    with tempfile.TemporaryDirectory(prefix="eightdim-selftest-") as td:
        T = pathlib.Path(td)

        section("[1/6] Python 脚本语法编译")
        pyfiles = sorted(ROOT.rglob("*.py"))
        bad = []
        for p in pyfiles:
            if "__pycache__" in str(p):
                continue
            try:
                py_compile.compile(str(p), doraise=True, cfile=str(T / (p.name + "c")))
            except py_compile.PyCompileError as e:
                bad.append("%s: %s" % (p.relative_to(ROOT), e))
        check("%d 个 Python 脚本编译通过" % len(pyfiles), not bad, "; ".join(bad[:2]))

        section("[2/6] 构造器 / 三图函数自检")
        r = run([sys.executable, RENDER, "--selftest-helpers"])
        check("html_helpers 构造器自检", r.returncode == 0 and "FAIL" not in r.stdout, r=r)
        r = run([sys.executable, RENDER, "--selftest-charts"])
        check("C1/C2/C3 渲染函数自检", r.returncode == 0 and "FAIL" not in r.stdout, r=r)

        section("[3/6] 完整出稿链路（含自动门禁 / JS / 幂等）")
        good = T / "good.html"
        r = run([sys.executable, RENDER, "--data", EXAMPLE, "--out", good])
        check("样例数据出稿且自动门禁通过", r.returncode == 0 and good.is_file(),
              "rc=%d" % r.returncode, r)
        if not good.is_file():
            print("\n无法继续：样例报告未生成。", file=sys.stderr)
            return 1
        text = good.read_text(encoding="utf-8")
        r = run([sys.executable, GATE, good, "--strict"])
        check("严格门禁 P0-1~P0-15 / P1 全绿",
              r.returncode == 0 and "全部门禁通过" in r.stdout, r=r)
        r = run([sys.executable, CHECKJS, good])
        check("内联 JS 验收", r.returncode == 0, r=r)
        good2 = T / "good2.html"
        r = run([sys.executable, RENDER, "--data", EXAMPLE, "--out", good2, "--no-gate"])
        check("两次渲染逐字节一致（幂等）",
              r.returncode == 0 and good.read_bytes() == good2.read_bytes(), r=r)
        check("成品含 <html> 与 v3 皮肤", '<html' in text
              and '<style id="hydro-skin"' in text)

        section("[4/6] 边界输入（必须友好报错，不得 traceback）")
        base = json.loads(EXAMPLE.read_text(encoding="utf-8"))

        def dump(name, obj, raw=None):
            p = T / name
            p.write_text(raw if raw is not None else json.dumps(obj, ensure_ascii=False),
                         encoding="utf-8")
            return p

        def expect_rc2(label, data_path, *extra):
            r = run([sys.executable, RENDER, "--data", data_path,
                     "--out", T / "case_out.html", "--no-gate", *extra])
            out = r.stdout + r.stderr
            check(label, r.returncode == 2 and "Traceback" not in out,
                  "rc=%d" % r.returncode, r)

        expect_rc2("坏 JSON 语法", dump("bad.json", None, raw="{not json"))
        expect_rc2("缺少 meta", dump("no_meta.json",
                                    {k: v for k, v in base.items() if k != "meta"}))
        expect_rc2("meta 缺 industry", dump("no_industry.json",
                                            {**base, "meta": {k: v for k, v in base["meta"].items()
                                                              if k != "industry"}}))
        expect_rc2("缺少 sources", dump("no_sources.json",
                                       {k: v for k, v in base.items() if k != "sources"}))
        expect_rc2("缺少 dims", dump("no_dims.json",
                                    {k: v for k, v in base.items() if k != "dims"}))
        expect_rc2("dims 为空", dump("empty_dims.json", {**base, "dims": []}))
        expect_rc2("数据文件不存在", T / "does_not_exist.json")

        broken = base["conclusion_html"]
        i = broken.find('<div class="risk-card-desc">')
        if i >= 0:
            j = broken.find("</div>", i + 40)
            broken = broken[:j] + broken[j + 6:]
        expect_rc2("片段标签不平衡 → 渲染前拒稿",
                   dump("broken_frag.json", {**base, "conclusion_html": broken}))

        bad_c1 = {**base, "charts": {**base["charts"], "c1": {
            **base["charts"]["c1"],
            "series": [{"name": "X", "cls": "svg-bar-primary",
                        "color": "#2a4bd7", "values": [1]}]}}}
        expect_rc2("charts.c1 values 与 labels 长度不符",
                   dump("bad_c1.json", bad_c1))

        # 占位符必须被 charts 渲染替换
        ph = dump("placeholder.json", {**base, "top_html": base["top_html"] + "\n{{C1}}"})
        ph_out = T / "placeholder.html"
        r = run([sys.executable, RENDER, "--data", ph, "--out", ph_out, "--no-gate"])
        ph_text = ph_out.read_text(encoding="utf-8") if ph_out.is_file() else ""
        check("{{C1}} 占位符被 charts 渲染替换",
              r.returncode == 0 and "{{C1}}" not in ph_text
              and "svg-bar-primary" in ph_text, r=r)

        # 中文 / 空格路径可写
        cn_out = T / "中文 报告.html"
        r = run([sys.executable, RENDER, "--data", EXAMPLE, "--out", cn_out, "--no-gate"])
        check("中文/空格输出路径", r.returncode == 0 and cn_out.is_file(), r=r)

        # 页脚：默认署名 / 可关闭 / 可选品牌块 / 公共模板不夹带导流
        check("默认只出方法论署名（不带导流）",
              'class="report-attribution"' in text
              and 'class="brand-title"' not in text)
        off = dump("footer_off.json", {**base, "branding": {
            "attribution": False, "enabled": False}})
        off_out = T / "footer_off.html"
        r = run([sys.executable, RENDER, "--data", off, "--out", off_out, "--no-gate"])
        off_text = off_out.read_text(encoding="utf-8") if off_out.is_file() else ""
        check("branding 全关时无页脚", r.returncode == 0
              and '<footer class="report-footer">' not in off_text, r=r)
        on = dump("footer_on.json", {**base, "branding": {
            "enabled": True, "title": "测试品牌", "wechat": "测试公众号",
            "video": "测试视频号"}})
        on_out = T / "footer_on.html"
        r = run([sys.executable, RENDER, "--data", on, "--out", on_out])
        on_text = on_out.read_text(encoding="utf-8") if on_out.is_file() else ""
        check("branding.enabled 出品牌块且门禁通过",
              r.returncode == 0 and 'class="brand-title"' in on_text
              and "测试公众号" in on_text and "测试视频号" in on_text, r=r)
        # 只查品牌专名，通用词「公众号」在代码里是渲染模板，不算夹带；
        # 关键词拆开拼接，避免本文件自匹配。
        brand_words = ("松幽" + "舒苑", "松幽" + "Ai提效")
        leaks = []
        for f in sorted(list((ROOT / "assets").glob("*")) + list(SCRIPTS.glob("*.py"))):
            if f.is_file() and f.suffix in (".css", ".py", ".html"):
                s = f.read_text(encoding="utf-8")
                if any(w in s for w in brand_words):
                    leaks.append(str(f.relative_to(ROOT)))
        check("公共模板/脚本不夹带导流信息", not leaks, "; ".join(leaks[:3]))

        # 门禁文件不存在友好报错
        r = run([sys.executable, GATE, T / "missing.html"])
        check("门禁文件不存在友好报错",
              r.returncode != 0 and "Traceback" not in (r.stdout + r.stderr), r=r)

        section("[5/6] 故意破坏 → 门禁必须拦截")
        sabotage = {
            "删掉一个 </div> → P0-11":
                text.replace("</div></div>\n<div class=\"step-card\" id=\"dim2\"",
                             "</div>\n<div class=\"step-card\" id=\"dim2\"", 1),
            "去掉皮肤 style id → P0-12":
                text.replace('<style id="hydro-skin"', '<style id="renamed"', 1),
            "删光三张图 → P0-15": strip_chart_cards(text),
            "静态 opacity:0 → P0-13":
                text.replace(".hero-masthead{", ".reveal{opacity:0}\n.hero-masthead{", 1),
            "占位符残留 → P0-14": text.replace("<body>", "<body>\n{{C1}}", 1),
            "script 内混入角标 → P0-13":
                text.replace("<script>",
                             '<script>var x=\'<a class="ref" href="https://a.com/b">x</a>\';', 1),
        }
        for label, broken_text in sabotage.items():
            p = T / ("sab_%d.html" % len(label))
            p.write_text(broken_text, encoding="utf-8")
            r = run([sys.executable, GATE, p, "--strict"])
            check(label, r.returncode != 0, "rc=%d" % r.returncode, r)

        section("[6/6] 文档相对引用完整性")
        missing = []
        for md in sorted(ROOT.rglob("*.md")):
            for m in re.finditer(r"\]\(([^)#]+?)\)", md.read_text(encoding="utf-8")):
                t = m.group(1).strip()
                if t.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if not (md.parent / t).exists():
                    missing.append("%s -> %s" % (md.relative_to(ROOT), t))
        check("文档内相对文件引用全部存在", not missing, "; ".join(missing[:3]))

    total = len(RESULTS)
    failed = [x for x in RESULTS if not x[1]]
    print("\n" + "=" * 66)
    print("自检结果：%d 项，通过 %d 项，失败 %d 项" % (total, total - len(failed), len(failed)))
    if failed:
        for label, _, detail in failed:
            print("  ✗ %s %s" % (label, detail))
        print("=" * 66)
        return 1
    print("✅ 全部通过，本 skill 可分享 / 可继续生成报告。")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
