#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八维报告 · 内联 JS 语法验收（v3.0）
=====================================
为什么要独立脚本：手工用 `re.findall(r"<script.*?</script>")` 提取时，
**HTML 注释里出现的 script 起始标签字面量**会被当成真实脚本起点，把注释文本
喂给 node，产生莫名其妙的 SyntaxError（2026-11-09 实测踩过）。
本脚本先剥离 HTML 注释，再提取内联脚本，最后交给 node --check。

用法:
    python3 references/check_js.py <报告.html>

退出码: 0 通过 / 1 语法或结构异常 / 2 参数错误
依赖: 标准库；可选 node（缺失时退化为结构检查并提示）
"""
import re
import shutil
import subprocess
import sys
import tempfile
import os


def extract_inline_scripts(text):
    """先剥离注释，再取不带 src 的内联 <script> 内容。"""
    clean = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    out = []
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", clean, re.S | re.I):
        attrs, code = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue  # 外链脚本不在本地检查范围（v3 报告应无外链）
        out.append(code)
    return out


def structural_check(text, scripts):
    """不依赖 node 的兜底检查。"""
    problems = []
    clean = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    if "<html" not in clean:
        problems.append("缺少 <html> 起始标签（head 切片可能被截断）")
    for i, code in enumerate(scripts, 1):
        if 'class="ref"' in code or "class='ref'" in code:
            problems.append("第 %d 个 script 内混入来源角标，会破坏 JS" % i)
        if code.strip().startswith("，") or code.strip().startswith("。"):
            problems.append("第 %d 个 script 以中文标点开头，疑似把 HTML 注释当成了脚本" % i)
    return problems


def main():
    if len(sys.argv) < 2:
        print("用法: python3 check_js.py <报告.html>")
        return 2
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    scripts = extract_inline_scripts(text)
    print("内联 script 块: %d" % len(scripts))
    problems = structural_check(text, scripts)
    node = shutil.which("node")
    if node:
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                            encoding="utf-8") as f:
                f.write("\n;\n".join(scripts))
                tmp = f.name
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
            if r.returncode != 0:
                problems.append("node --check 失败:\n" + (r.stderr or "").strip()[:800])
            else:
                print("node --check: 通过")
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)
    else:
        print("未找到 node，跳过语法检查（仅做结构检查）")
    if problems:
        for p in problems:
            print("  ✗ " + p)
        return 1
    print("✅ 内联 JS 验收通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
