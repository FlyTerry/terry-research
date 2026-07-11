#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_hkex.py — 港股(披露易) 年报/半年报 批量下载器 (Playwright 版)

原理(已实测可用):
  1. 用真实 Chromium 打开披露易「标题搜索」页 titlesearch.xhtml。
  2. 用 prefix.do 接口把股票代码(如 01818)解析成内部 stockId(如 12990)。
  3. JS 直接写入隐藏字段 stockId / from / to(YYYYMMDD)，并同步可见日期框。
  4. 点击 SEARCH(a.filter__btn-applyFilters-js) 提交 JSF 表单(整页回发)。
  5. 结果表格每页 100 条，点「LOAD MORE」循环加载全部。
  6. 解析每行: 发布时间 / 代码 / 名称 / 文档标题 / PDF 链接。
  7. 过滤出 Annual Report / Interim(Half-Year) Report(排除 Cancelled)。
  8. 下载 PDF 到 data/<key>/ 目录。

注意: 年报于次年发布(如 2025 年报在 2026 年 4 月发布)。
      披露易搜索的上界 to 不能超过"今天"(否则后端只返回 1 行),
      故 to 取动态今天, 即可覆盖 2026 年发布的 2025 年报; 年份再按标题过滤到 2020–2025。

用法:
  python3 tools/download_hkex.py --check            # 自检(招金)
  python3 tools/download_hkex.py --dry-run          # 打印计划不落盘
  python3 tools/download_hkex.py                     # 全量下载 4 家港股
  python3 tools/download_hkex.py --company zhaojin-mining shougang
"""

import argparse
import datetime
import os
import re
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.stderr.write("\n[错误] 未检测到 Playwright，请先:\n    pip install playwright && playwright install chromium\n")
    sys.exit(2)

URL = "https://www1.hkexnews.hk/search/titlesearch.xhtml"

# 港股公司(含 dual-listed 的 H 股代码; 若同时有 A 股, 文件名加 _HK 后缀避免覆盖)
COMPANIES = [
    {"key": "shougang",       "name": "首钢资源", "h": "00639", "a": None},
    {"key": "zhaojin-mining", "name": "招金矿业", "h": "01818", "a": None},
    {"key": "yankuang-energy","name": "兖矿能源", "h": "01171", "a": "600188"},
    {"key": "zijin-mining",   "name": "紫金矿业", "h": "02899", "a": "601899"},
]

REPORT_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]


def get_stock_id(page, code):
    raw = page.evaluate("""async (code) => {
        const u=`https://www1.hkexnews.hk/search/prefix.do?&callback=callback&lang=EN&type=A&name=${code}&market=SEHK&_=${Date.now()}`;
        const r=await fetch(u); return await r.text();
    }""", code)
    m = re.search(r'"stockId":(\d+),"code":"' + code, raw)
    return m.group(1) if m else None


def safe_goto(page, url, retries=3):
    last = None
    for i in range(retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return True
        except Exception as e:
            last = e
            print(f"    [重试] 页面加载超时, 第 {i+1} 次 ({e.__class__.__name__})")
            page.wait_for_timeout(3000)
    return False


def run_search(page, stock_id):
    # 注意: 披露易搜索的 to 上限不能超过"今天", 否则后端校验失败只返回 1 行。
    # 用动态今天作为上界, 即可覆盖 2026 年发布的 2025 年报(标题含 2025, 客户端按标题年份过滤)。
    today = datetime.date.today().strftime("%Y/%m/%d")
    for attempt in range(3):
        page.evaluate("""(args) => {
            const sid=args.sid, today=args.today;
            const setN=(n,v)=>{const e=document.querySelector('input[name='+n+']'); if(!e)return;
                const d=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e),'value');
                if(d&&d.set)d.set.call(e,v); else e.value=v;
                ['input','change','blur'].forEach(ev=>e.dispatchEvent(new Event(ev,{bubbles:true})));};
            const setV=(id,v)=>{const e=document.getElementById(id); if(!e)return;
                const d=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e),'value');
                if(d&&d.set)d.set.call(e,v); else e.value=v;
                ['input','change','blur'].forEach(ev=>e.dispatchEvent(new Event(ev,{bubbles:true})));};
            setN('stockId', String(sid)); setN('from','2020/01/01'); setN('to', today);
            setV('searchDate-From','2020/01/01'); setV('searchDate-To', today);
        }""", {"sid": int(stock_id), "today": today})
        page.wait_for_timeout(400)
        # 真实鼠标点击(已验证可触发 JSF 提交); 失败则降级为 JS click
        try:
            page.click("a.filter__btn-applyFilters-js", timeout=5000)
        except Exception:
            page.evaluate("document.querySelector('a.filter__btn-applyFilters-js').click()")
        page.wait_for_timeout(8000)
        rows = page.evaluate("""() => {
            const tables=[...document.querySelectorAll('table')];
            let best=null,bn=0; for(const t of tables){const r=t.querySelectorAll('tr').length; if(r>bn){bn=r;best=t;}}
            return best ? best.querySelectorAll('tr').length : 0;
        }""")
        if rows > 1:
            return True
        print(f"    [重试] 搜索未返回结果, 第 {attempt+1} 次")
        page.wait_for_timeout(2000)
    return False


def parse_rows(page):
    return page.evaluate("""() => {
        const tables=[...document.querySelectorAll('table')];
        let best=null,bn=0; for(const t of tables){const r=t.querySelectorAll('tr').length; if(r>bn){bn=r;best=t;}}
        if(!best) return [];
        const out=[];
        for(const tr of best.querySelectorAll('tr')){
            const cells=[...tr.querySelectorAll('td')];
            if(cells.length<4) continue;
            const release=cells[0].textContent.replace(/\\s+/g,' ').trim();
            const code=cells[1].textContent.trim();
            const name=cells[2].textContent.trim();
            const docCell=cells[3];
            const docTitle=docCell.textContent.replace(/\\s+/g,' ').trim();
            const link=docCell.querySelector('a');
            out.push({release, code, name, docTitle, href: link?link.href:null});
        }
        return out;
    }""")


def load_more(page):
    btn = page.query_selector("a.component-loadmore__link")
    if not btn:
        return False
    try:
        btn.click()
    except Exception:
        return False
    page.wait_for_timeout(3500)
    return True


def classify(doc_title):
    """返回 ('annual'|'interim', year) 或 None。"""
    t = doc_title.upper()
    cancelled = "CANCELLED" in t
    annual = ("ANNUAL REPORT" in t) or ("年報" in doc_title) or ("年报" in doc_title)
    interim = (("INTERIM REPORT" in t) or ("HALF-YEAR REPORT" in t) or ("HALF YEAR REPORT" in t)
               or ("中期報告" in doc_title) or ("中期报告" in doc_title))
    if not (annual or interim) or cancelled:
        return None
    kind = "annual" if annual else "interim"
    yrs = re.findall(r"(19|20)\d{2}", doc_title)
    year = None
    if yrs:
        cand = [int(y) for y in yrs if 2000 <= int(y) <= 2029]
        if cand:
            year = cand[-1]
    if year is None:
        m = re.search(r"(\d{4})", doc_title)
        if m:
            ry = int(m.group(1))
            year = ry - 1 if annual else ry
    return (kind, year)


def main():
    ap = argparse.ArgumentParser(description="港股(披露易)年报/半年报下载器")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    ap.add_argument("--company", nargs="+", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    companies = COMPANIES
    if args.company:
        keys = set(args.company)
        companies = [c for c in COMPANIES if c["key"] in keys]
        if not companies:
            print("未匹配公司:", args.company, file=sys.stderr); sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(locale="zh-CN")
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(60000)

        if args.check:
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            sid = get_stock_id(page, "01818")
            print(f"[HKEX] 招金 01818 -> stockId={sid} {'可达 ✅' if sid else '失败 ❌'}")
            browser.close(); return

        total = ok = skip = fail = 0
        for c in companies:
            cdir = os.path.join(args.out, c["key"])
            os.makedirs(cdir, exist_ok=True)
            print(f"\n=== {c['name']} ({c['key']}, H={c['h']}) ===")

            if not safe_goto(page, URL):
                print("  [跳过] 页面无法加载"); continue
            page.wait_for_timeout(3500)
            sid = get_stock_id(page, c["h"])
            if not sid:
                print("  [跳过] 无法解析 stockId"); continue
            print(f"  stockId={sid}")

            if not run_search(page, sid):
                print("  [跳过] 搜索未返回结果"); continue

            seen = {}
            iters = 0
            prev = -1
            stable = 0
            while iters < 80:
                rows = parse_rows(page)
                for r in rows:
                    if r["href"]:
                        seen.setdefault(r["href"], r)
                cur = len(seen)
                if args.verbose:
                    print(f"    已加载 {cur} 条")
                if cur == prev:
                    stable += 1
                    if stable >= 3:   # 连续 3 次无新增 -> 到底
                        break
                else:
                    stable = 0
                prev = cur
                if not load_more(page):
                    break
                iters += 1

            # 过滤年报/半年报
            wanted = {}
            if args.verbose:
                print(f"    累计解析 {len(seen)} 条, 样例:")
                for i, (href, r) in enumerate(list(seen.items())[:5]):
                    print(f"      [{i}] {r['docTitle'][:80]}")
            for href, r in seen.items():
                cls = classify(r["docTitle"])
                if not cls:
                    continue
                kind, year = cls
                if year not in REPORT_YEARS:
                    continue
                wanted[(year, kind)] = (r["docTitle"], href)

            print(f"  命中年报/半年报 {len(wanted)} 份 (2020–2025)")

            suffix = "_HK" if c.get("a") else ""
            for (year, kind), (title, href) in sorted(wanted.items()):
                label = "年报" if kind == "annual" else "半年报"
                fname = f"{c['name']}{year}{label}{suffix}.pdf"
                fpath = os.path.join(cdir, fname)
                total += 1
                if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                    print(f"  [跳过] {fname}"); skip += 1; continue
                if args.dry_run:
                    print(f"  [计划] {fname}  <-  {href}"); continue
                try:
                    resp = page.context.request.get(href, timeout=90000)
                    raw = resp.body()
                except Exception as e:
                    print(f"  [失败] {fname}  异常: {e}"); fail += 1; continue
                if not raw or raw[:4] != b"%PDF":
                    print(f"  [失败] {fname}  非PDF/空 url={href}"); fail += 1; continue
                with open(fpath, "wb") as f:
                    f.write(raw)
                print(f"  [OK]   {fname}  ({len(raw)} bytes)"); ok += 1
                time.sleep(0.4)

        browser.close()

    print(f"\n完成: 计划 {total} | 成功 {ok} | 跳过 {skip} | 失败 {fail}")
    if args.dry_run:
        print("(dry-run 模式，未写入文件)")


if __name__ == "__main__":
    main()
