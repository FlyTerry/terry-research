#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_reports.py — 深度研究公司 年报/半年报 批量下载器 (Playwright 版)

工作原理（已实测可用）:
  - A 股(巨潮): 用真实 Chromium 打开巨潮「全文检索」页（页面 JS 生成反爬 token），
    再于该页面上下文调用 fulltextSearch/full 接口翻页拉全量公告，按标题筛选
    「YYYY年年度报告 / 半年度报告」，PDF 直链为 https://static.cninfo.com.cn/<adjunctUrl>。
  - 港股(披露易): 用真实 Chromium 打开披露易搜索页，调用 titleSearchServlet 接口。

依赖:
  pip install playwright && playwright install chromium

用法:
  python3 tools/download_reports.py --check            # 浏览器内核自检
  python3 tools/download_reports.py --dry-run          # 打印计划，不落盘
  python3 tools/download_reports.py                     # 全量下载（2020-2025）
  python3 tools/download_reports.py --company zijin-mining yankuang-energy
  python3 tools/download_reports.py --years 2023 2024 2025
  python3 tools/download_reports.py --a-share-only     # 只下 A 股（港股接口待修复时可先用）
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.stderr.write(
        "\n[错误] 未检测到 Playwright。请先安装：\n"
        "    pip install playwright\n"
        "    playwright install chromium\n")
    sys.exit(2)


# ---------------------------------------------------------------------------
# 公司清单: key(文件夹名) -> 中文名 + A股代码(可空) + H股代码(可空)
# ---------------------------------------------------------------------------
COMPANIES = [
    {"key": "guanghui-energy", "name": "广汇能源", "a": "600256", "h": None},
    {"key": "huaibei",         "name": "淮北矿业", "a": "600985", "h": None},
    {"key": "jiayou",          "name": "嘉友国际", "a": "603871", "h": None},
    {"key": "shaanxi-coal",    "name": "陕西煤业", "a": "601225", "h": None},
    {"key": "shenhuo-shares",  "name": "神火股份", "a": "000933", "h": None},
    {"key": "shougang",        "name": "首钢资源", "a": None,     "h": "00639"},
    {"key": "xingye-yintin",   "name": "兴业银锡", "a": "000426", "h": None},
    {"key": "yankuang-energy", "name": "兖矿能源", "a": "600188", "h": "01171"},
    {"key": "zangge-mining",   "name": "藏格矿业", "a": "000408", "h": None},
    {"key": "zhaojin-mining",  "name": "招金矿业", "a": None,     "h": "01818"},
    {"key": "zijin-mining",    "name": "紫金矿业", "a": "601899", "h": "02899"},
]

REPORT_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

EXCLUDE_WORDS = ["摘要", "英文", "补充", "更新后", "更正", "说明", "稿", "预案",
                 "摘要版", "征求意见", "反馈", "问询", "回复", "修订说明",
                 "意见", "独立董事", "事前认可", "独立意见", "报告书的"]


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


# ---------------------------------------------------------------------------
# A 股: 巨潮全文检索
# ---------------------------------------------------------------------------
def cninfo_fetch_all(page, code):
    """翻页拉取该股票全部公告（list of dict）。"""
    out = []
    for pn in range(1, 60):
        js = (
            "async () => {"
            f"  const url='https://www.cninfo.com.cn/new/fulltextSearch/full?"
            f"searchkey={code}&sdate=2000-01-01&edate=2026-12-31"
            f"&isfulltext=false&sortName=pubdate&sortType=desc"
            f"&pageNum={pn}&pageSize=100&type=';"
            "  const r=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'}});"
            "  return await r.text();"
            "}"
        )
        try:
            txt = page.evaluate(js)
            d = json.loads(txt)
        except Exception:
            break
        anns = (d.get("announcements") or []) if isinstance(d, dict) else []
        out.extend(anns)
        if len(anns) < 100:
            break
        time.sleep(0.3)
    return out


def classify_cninfo(ann, years):
    """返回 ('annual'|'interim', year) 或 None。年份优先取标题，缺失时由发布时间推断。"""
    title = strip_tags(ann.get("announcementTitle") or ann.get("title") or "")
    is_interim = ("半年度报告" in title) or ("中期报告" in title)
    is_annual = ("年度报告" in title) and not is_interim
    if not (is_annual or is_interim):
        return None
    m = re.search(r"(20\d{2})", title)
    if m:
        yr = int(m.group(1))
    else:
        at = ann.get("announcementTime")
        if not at:
            return None
        try:
            dt = datetime.datetime.fromtimestamp(int(at) / 1000)
        except Exception:
            return None
        # 年报次年发布 → 发布年-1；半年报当年发布 → 发布年
        yr = dt.year - 1 if is_annual else dt.year
    if yr not in years:
        return None
    return ("annual" if is_annual else "interim", yr)


def collect_cninfo(page, code, years):
    anns = cninfo_fetch_all(page, code)
    buckets = {}  # (year, kind) -> [(title, url, score), ...]
    for a in anns:
        cls = classify_cninfo(a, years)
        if not cls:
            continue
        kind, yr = cls
        adj = a.get("adjunctUrl") or ""
        if not adj:
            continue
        title = strip_tags(a.get("announcementTitle") or "")
        url = "https://static.cninfo.com.cn/" + adj.lstrip("/")
        score = any(w in title for w in EXCLUDE_WORDS)
        buckets.setdefault((yr, kind), []).append((title, url, score))
    wanted = {}
    for key, cands in buckets.items():
        # 优先选不含排除词（摘要/英文/补充等）的版本；若只有带“摘要”的也照收
        cands.sort(key=lambda x: x[2])
        wanted[key] = (cands[0][0], cands[0][1])
    return wanted, len(anns)


# ---------------------------------------------------------------------------
# 港股: 披露易 (JSF servlet) — 待修复，目前可能返回空
# ---------------------------------------------------------------------------
def collect_hkex(page, code, years):
    wanted = {}
    total = 0
    for yr in years:
        js = (
            "async () => {"
            "  const url='https://www1.hkexnews.hk/search/titleSearchServlet.do?"
            "sortDir=DESC&sortByOptions=DateTime&category=0&market=SEH"
            f"&stockId={code}&from={yr}-01-01&to={yr}-12-31"
            "&title=&next=0&docs=30';"
            "  const r=await fetch(url,{headers:{'Referer':'https://www1.hkexnews.hk/search/titlesearch.xhtml'}});"
            "  return await r.text();"
            "}"
        )
        try:
            txt = page.evaluate(js)
            d = json.loads(txt)
        except Exception:
            continue
        total += int(d.get("recordCnt") or 0)
        res = d.get("result") or []
        if isinstance(res, str):
            try:
                res = json.loads(res)
            except Exception:
                res = []
        for item in res:
            blob = json.dumps(item, ensure_ascii=False) if not isinstance(item, str) else item
            low = blob.lower()
            if str(yr) not in low:
                continue
            is_interim = ("interim report" in low) or ("中期報告" in blob) or ("中期报告" in blob)
            is_annual = (("annual report" in low) or ("年報" in blob) or ("年报" in blob)) and not is_interim
            if not (is_annual or is_interim):
                continue
            pdfs = re.findall(r"https?://[^\"'\\s]+?\.pdf", blob)
            if not pdfs:
                pdfs = re.findall(r"(?:href|src)=['\"]([^'\"]+?\.pdf)['\"]", blob)
            if pdfs:
                key = (yr, "interim" if is_interim else "annual")
                wanted[key] = (blob[:60], pdfs[0])
    return wanted, total


# ---------------------------------------------------------------------------
# PDF 下载与校验
# ---------------------------------------------------------------------------
def save_pdf(path, raw):
    if not raw or len(raw) < 100:
        return False
    if raw[:4] != b"%PDF":
        return False
    with open(path, "wb") as f:
        f.write(raw)
    return True


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="深度研究公司年报/半年报下载器 (Playwright)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
                    help="数据根目录 (默认 <repo>/data)")
    ap.add_argument("--years", nargs="+", type=int, default=REPORT_YEARS,
                    help="报告年份，默认 2020..2025")
    ap.add_argument("--company", nargs="+", default=None, help="仅下载指定 key（默认全部）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不下载")
    ap.add_argument("--check", action="store_true", help="仅用浏览器内核自检后退出")
    ap.add_argument("--verbose", action="store_true", help="打印诊断信息")
    ap.add_argument("--a-share-only", action="store_true", help="只下载 A 股（跳过港股）")
    args = ap.parse_args()

    years = sorted(set(args.years))
    companies = COMPANIES
    if args.company:
        keys = set(args.company)
        companies = [c for c in COMPANIES if c["key"] in keys]
        if not companies:
            print("未匹配到公司 key:", args.company, file=sys.stderr)
            sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(locale="zh-CN")

        if args.check:
            # A 股自检
            page.goto("https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord=000426",
                      wait_until="networkidle")
            time.sleep(4)
            try:
                anns = cninfo_fetch_all(page, "000426")
                print(f"[CNINFO] 公告数={len(anns)}  {'可达 ✅' if anns else '为空 ❌'}")
            except Exception as e:
                print("[CNINFO] 自检异常:", e)
            browser.close()
            return

        total = ok = skip = fail = 0
        for c in companies:
            cdir = os.path.join(args.out, c["key"])
            os.makedirs(cdir, exist_ok=True)
            print(f"\n=== {c['name']} ({c['key']}) ===")
            wanted = {}
            diag = []
            if c["a"]:
                page.goto(f"https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord={c['a']}",
                          wait_until="networkidle")
                time.sleep(3)
                w, n = collect_cninfo(page, c["a"], years)
                wanted.update(w)
                diag.append(f"巨潮拉取 {n} 条 → 命中 {len(w)} 份")

            if c["h"] and not args.a_share_only:
                page.goto("https://www1.hkexnews.hk/search/titlesearch.xhtml", wait_until="domcontentloaded")
                time.sleep(3)
                w, n = collect_hkex(page, c["h"], years)
                wanted.update(w)
                diag.append(f"披露易记录 {n} 条 → 命中 {len(w)} 份")

            if diag:
                print("  " + "；".join(diag))
            if not wanted:
                print("  (未匹配到年报/半年报)")
            for (year, kind), (title, url) in sorted(wanted.items()):
                label = "年报" if kind == "annual" else "半年报"
                fname = f"{c['name']}{year}{label}.pdf"
                fpath = os.path.join(cdir, fname)
                total += 1
                if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                    print(f"  [跳过] {fname}")
                    skip += 1
                    continue
                if args.dry_run:
                    print(f"  [计划] {fname}  <-  {url}")
                    continue
                try:
                    resp = page.context.request.get(
                        url, headers={"Referer": "https://www.cninfo.com.cn/"}, timeout=90000)
                    raw = resp.body()
                except Exception as e:
                    print(f"  [失败] {fname}  异常: {e}")
                    fail += 1
                    continue
                if save_pdf(fpath, raw):
                    print(f"  [OK]   {fname}  ({len(raw)} bytes)")
                    ok += 1
                else:
                    print(f"  [失败] {fname}  非PDF/空 url={url}")
                    fail += 1
                time.sleep(0.5)

        browser.close()

    print(f"\n完成: 计划 {total} | 成功 {ok} | 跳过 {skip} | 失败 {fail}")
    if args.dry_run:
        print("(dry-run 模式，未写入文件)")


if __name__ == "__main__":
    main()
