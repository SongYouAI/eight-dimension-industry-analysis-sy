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
  6. 文档中的相对文件引用是否都存在 + 商店版（无 PNG）离线出图兼容

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
        check("严格门禁 P0-1~P0-16 / P1 全绿",
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

        # 页脚：v3.2.2 紧凑溯源条，数据 JSON 关不掉、尺寸不能回胀
        brand_cfg = json.loads((ROOT / "assets/brand.json").read_text(encoding="utf-8"))
        qr_imgs = re.findall(
            r'<img[^>]+src="data:image/png;base64,[A-Za-z0-9+/=]{200,}"', text)
        qr_css_w = re.search(r'\.brand-qr\{[^}]*?width:(\d+)px', text)
        check("默认强制输出紧凑溯源条（单行署名 / 两行小码 / 可放大）",
              'class="brand-block"' in text and len(qr_imgs) == 2
              and text.count('class="brand-channel"') == 2
              and 'class="brand-head"' in text
              and 'class="brand-meta"' in text
              and bool(qr_css_w) and int(qr_css_w.group(1)) <= 60
              and "<figcaption" not in text
              and 'id="qrLightbox"' in text
              and "getElementById('qrLightbox')" in text
              and brand_cfg["wechat"] in text and brand_cfg["video"] in text,
              "检出二维码 %d 张 / 渠道行 %d 行 / 小码 %spx"
              % (len(qr_imgs), text.count('class="brand-channel"'),
                 qr_css_w.group(1) if qr_css_w else "?"))
        off = dump("footer_off.json", {**base, "branding": {
            "attribution": False, "enabled": False,
            "wechat": "测试公众号", "video": "测试视频号"}})
        off_out = T / "footer_off.html"
        r = run([sys.executable, RENDER, "--data", off, "--out", off_out])
        off_text = off_out.read_text(encoding="utf-8") if off_out.is_file() else ""
        check("branding 全关也不能关掉品牌块（含门禁）",
              r.returncode == 0 and 'class="brand-block"' in off_text
              and brand_cfg["wechat"] in off_text
              and "测试公众号" not in off_text, "rc=%d" % r.returncode, r)
        on = dump("footer_url.json", {**base, "branding": {
            "url": "https://example.com/post"}})
        on_out = T / "footer_url.html"
        r = run([sys.executable, RENDER, "--data", on, "--out", on_out])
        on_text = on_out.read_text(encoding="utf-8") if on_out.is_file() else ""
        check("branding.url 只补延伸阅读链接",
              r.returncode == 0 and 'class="brand-link"' in on_text
              and "https://example.com/post" in on_text, r=r)
        # 商店版（SkillHub）不允许 PNG，二维码数据必须在 brand.json 里自带
        b64_ok = all(brand_cfg.get(k) for k in ("qr_wechat_data", "qr_video_data"))
        assets_ok = (ROOT / "assets" / "brand.json").is_file() and (
            b64_ok or all((ROOT / "assets" / p).is_file()
                          for p in (brand_cfg["qr_wechat"], brand_cfg["qr_video"])))
        brand_words = (brand_cfg["wechat"], brand_cfg["video"])
        leaks = []
        for f in sorted(list(SCRIPTS.glob("*.py")) + [ROOT / "assets/template.html"]):
            if f.is_file() and any(w in f.read_text(encoding="utf-8")
                                   for w in brand_words):
                leaks.append(str(f.relative_to(ROOT)))
        check("品牌常量集中在 assets/brand.json，二维码资源在位",
              assets_ok and not leaks, "; ".join(leaks[:3]))

        # 商店版兼容：SkillHub 不允许 PNG，移走源图后仍须能离线出图
        import shutil
        shop = T / "shop_skill"
        if shop.exists():
            shutil.rmtree(shop)
        shutil.copytree(ROOT, shop, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "shots*", "*.png", "*.pyc"))
        shop_out = T / "shop_report.html"
        r = run([sys.executable, shop / "scripts" / "render_report.py",
                 "--data", shop / "scripts" / "example_data.json",
                 "--out", shop_out])
        shop_text = shop_out.read_text(encoding="utf-8") if shop_out.is_file() else ""
        check("商店版无 PNG 仍能离线出图（brand.json 自带 base64）",
              r.returncode == 0 and len(re.findall(
                  r'src="data:image/png;base64,[A-Za-z0-9+/=]{200,}"', shop_text)) == 2,
              "rc=%d" % r.returncode, r)

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
            "删掉品牌块 → P0-16":
                re.sub(r'<footer class="report-footer">.*?</footer>', '', text,
                       count=1, flags=re.S),
            "二维码改外链 → P0-16":
                re.sub(r'src="data:image/png;base64,[A-Za-z0-9+/=]+"',
                       'src="https://example.com/qr.png"', text, count=1),
            "删掉点击放大层 → P0-16":
                text.replace('id="qrLightbox"', 'id="qrLightboxX"', 1),
            "二维码下加回图注 → P0-16":
                text.replace("</footer>", "<figcaption>公众号</figcaption>\n</footer>", 1),
            "拆掉单行署名 → P0-16":
                text.replace('class="brand-head"', 'class="brand-head-legacy"', 1),
            "小码放大回 88px → P0-16":
                text.replace("width:52px;padding:4px", "width:88px;padding:4px", 1),
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

        # verify_links.py 回归：站点对 HEAD 返 404、GET 返 200 时不得误报坏链
        import importlib.util
        from unittest import mock
        spec = importlib.util.spec_from_file_location(
            "verify_links_probe", str(ROOT / "references" / "verify_links.py"))
        vl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vl)
        with mock.patch.object(vl, "_request_code", side_effect=[404, 200]):
            st, msg = vl.probe("https://example.com/x.html", 3)
        check("HEAD 404 / GET 200 不误报坏链", st == "ok", msg)

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
