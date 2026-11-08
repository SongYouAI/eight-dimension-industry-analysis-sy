#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维报告 · 分段视觉验收截图（Phase 3.5 配套）
=============================================
Chrome headless 对 file://...#dim3 锚点不会滚动，直接截图永远停在首屏。
本脚本把指定 section 裁成独立 HTML（复用原报告 <head> 的 CSS/JS），
再调 Chrome 截图，用于验收图表区 / 表格区是否溢出、遮挡或裁切。

用法:
    python3 capture.py <报告.html> --section dim3
    python3 capture.py <报告.html> --section dim3 --out /tmp/dim3.png --width 1280 --height 1800
    python3 capture.py <报告.html> --all --outdir ./shots

退出码: 0 = 全部截图成功；1 = 参数/文件/Chrome 不可用；2 = 部分截图失败
依赖: 标准库 + 本机 Chrome
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

# 跨平台自动探测：旧版写死 macOS 路径，Linux/Windows 上直接失败。
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
]
CHROME_COMMANDS = ["google-chrome", "google-chrome-stable", "chromium",
                   "chromium-browser", "chrome"]
SECTIONS = ["dim1", "dim2", "dim3", "dim4", "dim5", "dim6", "dim7", "dim8",
            "conclusion", "src-summary"]


def find_chrome(explicit=None):
    """返回可用的 Chrome 路径；支持 --chrome 传绝对路径或 PATH 上的命令名。"""
    if explicit:
        return explicit if (os.path.isfile(explicit) or shutil.which(explicit)) else None
    for p in CHROME_CANDIDATES:
        if os.path.isfile(p):
            return p
    for cmd in CHROME_COMMANDS:
        got = shutil.which(cmd)
        if got:
            return got
    return None


def slice_section(text, sid):
    """裁出 id=sid 的 step-card（到下一个 step-card 或 body 结尾）。"""
    m = re.search(r'<div class="step-card"\s+id="%s"' % re.escape(sid), text)
    if not m:
        return None
    start = m.start()
    nxt = re.search(r'<div class="step-card"\s+id="', text[start + 10:])
    end = start + 10 + nxt.start() if nxt else text.rfind("</body>")
    if end < 0:
        end = len(text)
    head = text[:text.index("</head>") + len("</head>")]
    body = text[start:end]
    return (head + '\n<body>\n<div class="main-wrap" style="padding:20px 30px;">\n'
            + body + "\n</div>\n</body>\n</html>\n")


def shot(page_path, out_path, chrome, width, height, timeout_ms):
    # as_uri() 会正确编码中文/空格路径；直接拼 "file://"+path 在含空格目录会失败。
    cmd = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
           "--hide-scrollbars", "--virtual-time-budget=%d" % timeout_ms,
           "--window-size=%d,%d" % (width, height),
           "--screenshot=" + out_path, Path(page_path).resolve().as_uri()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=max(30, timeout_ms / 1000 + 30))
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0


def main():
    ap = argparse.ArgumentParser(description="八维报告分段视觉验收截图")
    ap.add_argument("report", help="报告 HTML 路径（绝对路径更稳）")
    ap.add_argument("--section", choices=SECTIONS, help="只截某一个 section")
    ap.add_argument("--all", action="store_true", help="截全部 10 个 section")
    ap.add_argument("--out", help="单张截图输出路径")
    ap.add_argument("--outdir", help="--all 时的输出目录")
    ap.add_argument("--chrome", default=None, help="Chrome 路径或命令名（默认自动探测）")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=1800)
    ap.add_argument("--timeout", type=int, default=3000, help="virtual-time-budget 毫秒")
    args = ap.parse_args()

    report = os.path.abspath(args.report)
    if not os.path.isfile(report):
        print("报告不存在：%s" % report, file=sys.stderr)
        return 1
    chrome = find_chrome(args.chrome)
    if not chrome:
        print("未找到 Chrome/Chromium（用 --chrome 指定路径或命令名）", file=sys.stderr)
        return 1
    print("Chrome: %s" % chrome)
    if not args.section and not args.all:
        ap.error("需要 --section 或 --all")
    text = open(report, encoding="utf-8").read()

    ids = SECTIONS if args.all else [args.section]
    if args.all:
        outdir = os.path.abspath(args.outdir or "./shots")
        os.makedirs(outdir, exist_ok=True)
    else:
        outdir = None

    failed = []
    with tempfile.TemporaryDirectory(prefix="eightdim-capture-") as tmp:
        for sid in ids:
            frag = slice_section(text, sid)
            if frag is None:
                print("SKIP %s：找不到该 section" % sid)
                failed.append(sid)
                continue
            page = os.path.join(tmp, sid + ".html")
            open(page, "w", encoding="utf-8").write(frag)
            out = (os.path.join(outdir, sid + ".png") if outdir else
                   os.path.abspath(args.out or (sid + "_capture.png")))
            ok = shot(page, out, chrome, args.width, args.height, args.timeout)
            print(("OK   " if ok else "FAIL ") + sid + " -> " + out)
            if not ok:
                failed.append(sid)
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
