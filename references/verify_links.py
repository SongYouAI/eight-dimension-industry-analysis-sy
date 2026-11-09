#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维报告 · 来源链接验活（辅助工具，不阻断发布）
================================================
check_report.py 的 P0-4「链接邻近率」只判「数字邻近 120 字内有没有 <a>」，
不判链接能否打开、页面里是否真有被引数字。本脚本补前者：HEAD 探活，
列出明确失效（4xx/5xx）的 URL。HEAD 报 4xx/5xx 时再用 GET 复核一次：
部分站点（如 yofc.com）对 HEAD / 自定义 UA 直接返 404，但 GET 正常，
只信 HEAD 会把好链误报成坏链。

网络不可达/超时、站点拒绝 HEAD（403/405/429）不计入失效，避免把环境
问题误报成坏链。本脚本不验证页面内容是否含被引数字（仍需人工按
output-spec.md 四级颗粒度抽查）。

用法:
    python3 verify_links.py <报告.html>
    python3 verify_links.py <报告.html> --limit 30 --timeout 5

退出码: 恒 0（只提示，不阻断）
依赖: 仅标准库
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import html
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; eight-dim-verify/1.0)"


def collect(text):
    """抽取并去重；HTML 里的 &amp; 必须还原成 &，否则带查询参数的 URL 会被错误探活。"""
    seen, out = set(), []
    for u in re.findall(r'href=["\'](https?://[^"\']+)["\']', text):
        u = html.unescape(u)
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _request_code(url, timeout, method, extra_headers=None):
    """返回 HTTP 状态码；网络问题返回 None。"""
    headers = {"User-Agent": UA}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError, ValueError):
        return None


def probe(url, timeout):
    """返回 (ok|dead|skip, 说明)。HEAD 失效时以 GET 复核为准。"""
    code = _request_code(url, timeout, "HEAD")
    if code is None:
        return "skip", "网络不可达 / 超时"
    if code in (403, 405, 429):
        return "skip", f"HTTP {code}（站点拒绝探活，非链接失效）"
    if 200 <= code < 400:
        return "ok", f"HTTP {code}"
    # 站点对 HEAD / 自定义 UA 返 404 但 GET 正常 → 以 GET 为准，避免误删好链
    code2 = _request_code(url, timeout, "GET", {"Range": "bytes=0-0"})
    if code2 is None:
        return "dead", f"HTTP {code}（GET 复核超时）"
    if 200 <= code2 < 400:
        return "ok", f"HTTP {code2}（HEAD {code} → GET 复核可达）"
    return "dead", f"HTTP {code2}（HEAD {code}）"


def main():
    ap = argparse.ArgumentParser(description="八维报告来源链接验活（只提示，不阻断发布）")
    ap.add_argument("report", help="报告 HTML 路径")
    ap.add_argument("--limit", type=int, default=0, help="最多探活 N 个（0=全部）")
    ap.add_argument("--timeout", type=float, default=5.0, help="单链接超时秒数，默认 5")
    ap.add_argument("--workers", type=int, default=8, help="并发探活数，默认 8")
    args = ap.parse_args()
    try:
        text = open(args.report, encoding="utf-8").read()
    except OSError as e:
        print(f"无法读取：{e}", file=sys.stderr)
        return 0

    urls = collect(text)
    if args.limit > 0:
        urls = urls[:args.limit]
    print(f"唯一链接 {len(urls)} 个 | 超时 {args.timeout}s")

    stat = {"ok": 0, "dead": 0, "skip": 0}
    dead = []
    workers = max(1, min(args.workers, len(urls) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for u, (st, msg) in zip(urls, pool.map(lambda x: probe(x, args.timeout), urls)):
            stat[st] += 1
            if st == "dead":
                dead.append((u, msg))
    print(f"可达 {stat['ok']} | 失效 {stat['dead']} | 跳过 {stat['skip']}")
    if dead:
        print("明确失效链接：")
        for u, msg in dead:
            print(f"  x {msg}  {u}")
    print("提示：网络不可达/超时、403/405/429 不计入失效；本脚本不验证页面内容。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
