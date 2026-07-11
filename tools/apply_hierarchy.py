#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三级导航层级化（导航层级 / 无 iframe）：
  首页 → 行业报告 → 公司报告

能力（幂等，可重复运行）：
  1) coking-coal-report.html：移除 3 个紫色渐变「打开完整报告」CTA 块，
     在文末插入「十八、相关公司深度报告」卡片网格，链接到 3 份独立公司报告。
  2) 11 份公司报告：在面包屑中插入行业父级回链
     （首页 > [行业] > [公司]），并修正 huaibei 误写的「有色金属」→「焦煤行业」。
"""
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 公司报告 -> (父级行业报告, 行业标签)
COMPANY_MAP = {
    "shougang-report.html":       ("coking-coal-report.html",   "焦煤行业"),
    "jiayou-report.html":         ("coking-coal-report.html",   "焦煤行业"),
    "huaibei-report.html":        ("coking-coal-report.html",   "焦煤行业"),
    "shaanxi-coal-report.html":   ("thermal-coal-report.html",  "动力煤行业"),
    "yankuang-energy-report.html":("thermal-coal-report.html",  "动力煤行业"),
    "guanghui-energy-report.html":("thermal-coal-report.html",  "动力煤行业"),
    "zijin-mining-report.html":   ("nonferrous-metals-report.html", "有色金属行业"),
    "zhaojin-mining-report.html": ("nonferrous-metals-report.html", "有色金属行业"),
    "zangge-mining-report.html":  ("nonferrous-metals-report.html", "有色金属行业"),
    "xingye-yintin-report.html":  ("nonferrous-metals-report.html", "有色金属行业"),
    "shenhuo-shares-report.html": ("nonferrous-metals-report.html", "有色金属行业"),
}

RELATED_GRID = '''    <section class="related-reports">
        <h2 id="chapter-18">十八、相关公司深度报告</h2>
        <p>以下公司深度研究报告已独立成篇，点击查看完整的五年财务分析、敏感性分析与投资建议：</p>
        <div class="related-reports__grid">
            <a class="related-card" href="shougang-report.html">
                <span class="related-card__name">首钢资源</span>
                <span class="related-card__ticker">00639.HK</span>
                <span class="related-card__desc">纯正焦煤标的，高派息、低估值，净现金充裕。</span>
                <span class="related-card__go">查看完整报告 →</span>
            </a>
            <a class="related-card" href="jiayou-report.html">
                <span class="related-card__name">嘉友国际</span>
                <span class="related-card__ticker">603871.SH</span>
                <span class="related-card__desc">跨境物流与蒙古焦煤供应链核心标的。</span>
                <span class="related-card__go">查看完整报告 →</span>
            </a>
            <a class="related-card" href="huaibei-report.html">
                <span class="related-card__name">淮北矿业</span>
                <span class="related-card__ticker">600985.SH</span>
                <span class="related-card__desc">煤焦化一体化，区位与产品结构优势显著。</span>
                <span class="related-card__go">查看完整报告 →</span>
            </a>
        </div>
    </section>'''


def fix_coking_coal(path):
    html = open(path, encoding="utf-8").read()
    changed = []

    # 1) 移除 3 个紫色渐变 CTA 块（含其后续 <hr>
    pat = re.compile(
        r'<div style="background: linear-gradient\(135deg, #667eea 0%, #764ba2 100%\)[\s\S]*?打开完整报告[\s\S]*?</a>\s*</div>\s*<hr style="margin:40px 0;">'
    )
    n = len(pat.findall(html))
    html = pat.sub("", html)
    if n:
        changed.append(f"移除 {n} 个紫色渐变 CTA 块")

    # 2) 插入「相关公司深度报告」卡片网格（仅一次）
    if "related-reports" not in html:
        # 定位 report-layout__main 的闭合 </div> 紧跟 </main>
        marker = "        </div>\n</main>"
        if marker in html:
            html = html.replace(marker, RELATED_GRID + "\n" + marker, 1)
            changed.append("插入相关公司深度报告卡片网格")
        else:
            changed.append("⚠️ 未找到插入锚点（</div></main>）")
    else:
        changed.append("相关公司卡片已存在，跳过")

    open(path, "w", encoding="utf-8").write(html)
    return changed


def fix_breadcrumb(path, parent, industry):
    html = open(path, encoding="utf-8").read()
    changed = []

    # 若已含父级行业回链则跳过
    if f'href="{parent}"' in html and f">{industry}</a>" in html:
        changed.append("面包屑行业回链已存在，跳过")
        return changed

    # 面包屑 nav 结构：首页 > sep > current
    nav_pat = re.compile(
        r'(<nav class="site-nav">\s*<a href="index.html">首页</a>\s*'
        r'<span class="site-nav__sep">/</span>\s*)'
        r'<span class="site-nav__current">(.*?)</span>\s*</nav>',
        re.DOTALL,
    )

    m = nav_pat.search(html)
    if not m:
        changed.append("⚠️ 未匹配到面包屑 nav 结构")
        return changed

    current = m.group(2)
    # 剥离 current 文本里自带的行业前缀（避免「焦煤行业 > 煤炭行业 · 嘉友」这类重复）
    current = re.sub(r'^(有色金属|煤炭行业|焦煤行业)\s*[·•\-]\s*', '', current)

    def repl(mm):
        head = mm.group(1)
        return (f'{head}<a href="{parent}">{industry}</a>\n'
                f'                <span class="site-nav__sep">/</span>\n'
                f'                <span class="site-nav__current">{current}</span>\n'
                f'            </nav>')

    new_html = nav_pat.sub(repl, html, count=1)
    open(path, "w", encoding="utf-8").write(new_html)
    changed.append(f"面包屑插入 [{industry}] 回链（原 current：{current[:24]}…）")
    return changed


def main():
    os.chdir(ROOT)
    print("===== 焦煤行业报告：公司章节改造 =====")
    print(" coking-coal-report.html:", "; ".join(fix_coking_coal("coking-coal-report.html")))

    print("\n===== 公司报告面包屑：行业父级回链 =====")
    for f, (parent, industry) in COMPANY_MAP.items():
        print(f" {f}: " + "; ".join(fix_breadcrumb(f, parent, industry)))


if __name__ == "__main__":
    main()
