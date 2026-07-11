#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_unified_design.py — 将研究报告 HTML 改造为统一设计系统

用法:
    python3 tools/apply_unified_design.py <report.html> [coal|nonferrous]

动作:
  1. 移除 <head> 内联 <style> 设计块, 改为引用 assets/terry-style.css
  2. <body> 标注行业主题 (theme-coal / theme-nonferrous)
  3. 注入固定顶部导航 .site-header + 主容器 <main class="container">
     (若文件已有 <div class="container">, 则原地升级为 <main>, 不重复嵌套)
  4. 统一报告 H1 为 .report-title + 版本徽标 + .report-subtitle; 同步规范化 <title>
  5. 重命名旧组件类到统一系统: info-box/mine-detail/warning-box/...
  6. 文末补 .site-footer (数据来源 + 免责声明), 并闭合 </main>; 移除旧页脚块

幂等: 已含 theme-/terry-style.css/site-footer 的文件会跳过相应步骤。
"""
import re
import sys

THEMES = {"coal": "theme-coal", "nonferrous": "theme-nonferrous"}

HEADER_TPL = """    <header class="site-header">
        <div class="site-header__inner">
            <a class="site-logo" href="index.html">📊 Terry Research</a>
            <nav class="site-nav">
                <a href="index.html">首页</a>
                <span class="site-nav__sep">/</span>
                <span class="site-nav__current">{crumb}</span>
            </nav>
        </div>
    </header>

    <main class="container">
"""

FOOTER_TPL = """
    <hr class="divider">
    </main>

    <footer class="site-footer">
        <p>© 2026 Terry Research</p>
        <p>{source}</p>
        <p>本报告基于公开资料整理，仅供学习交流，不构成任何投资建议。投资有风险，入市需谨慎。</p>
    </footer>
"""

CLASS_MAP = [
    ('class="info-box"', 'class="box box--info"'),
    ('class="mine-detail"', 'class="detail-card"'),
    ('class="warning-box"', 'class="box box--warning"'),
    ('class="verification-status"', 'class="box box--warning"'),
    ('class="status-verified"', 'class="m-ok"'),
    ('class="status-pending"', 'class="m-warn"'),
    ('class="status-undisclosed"', 'class="m-no"'),
]


def clean_text(s: str) -> str:
    """规范年区间破折号, 去掉前导 emoji 与末尾版本号。"""
    s = s.strip()
    s = re.sub(r"^[\s\U0001F000-\U0001FAFF\U00002600-\U000027BF\ufe0f]+", "", s)
    s = re.sub(r"(\d{4})\s*[-–—]\s*(\d{4})", r"\1–\2", s)
    s = re.sub(r"[\s—\-–]*(详细版(?:\s*v?[\d.]+)?)\s*$", "", s)
    return s.strip()


def infer_crumb(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = clean_text(m.group(1)) if m else ""
    if any(k in title for k in ("煤炭", "煤业", "焦煤", "动力煤")):
        return "煤炭行业 · " + title
    if any(k in title for k in ("有色", "金", "矿", "锡")):
        return "有色金属 · " + title
    return title or "研究报告"


def transform_h1(html: str) -> str:
    def repl(m):
        inner = m.group(2)
        badge = ""
        mm = re.search(r"(.*?)[\s—\-–]*(详细版\s*v?[\d.]+)\s*$", inner)
        if mm:
            inner = clean_text(mm.group(1))
            badge = f'<span class="version-badge">{mm.group(2).replace(" ", "")}</span>'
        else:
            inner = clean_text(inner)
        return f'<h1 class="report-title">{inner}{badge}</h1>'
    return re.sub(r"<h1([^>]*)>(.*?)</h1>", repl, html, count=1, flags=re.S)


def normalize_title(html: str) -> str:
    def repl(m):
        return f"<title>{clean_text(m.group(1))}</title>"
    return re.sub(r"<title>(.*?)</title>", repl, html, count=1, flags=re.S)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 tools/apply_unified_design.py <report.html> [coal|nonferrous]")
        sys.exit(1)
    path = sys.argv[1]
    theme = sys.argv[2] if len(sys.argv) > 2 else (
        "nonferrous" if any(k in path for k in ("zijin", "zhaojin", "zangge", "xingye", "shenhuo", "nonferrous"))
        else "coal"
    )
    if theme not in THEMES:
        print("theme 必须是 coal 或 nonferrous")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        html = f.read()

    cls = THEMES[theme]
    changed = []

    # 1. 移除内联设计 <style> 块
    if "<style>" in html and "terry-style.css" not in html:
        html = re.sub(r"<style>.*?</style>", "", html, count=1, flags=re.S)
        changed.append("移除内联<style>")

    # 2. 引入共享 CSS
    if "terry-style.css" not in html:
        html = re.sub(r"(</title>\s*)",
                      r'\1    <link rel="stylesheet" href="assets/terry-style.css">\n',
                      html, count=1)
        changed.append("引入terry-style.css")

    # 3. body 主题
    if "theme-" not in html:
        html = re.sub(r"<body(\s[^>]*)?>", f'<body class="{cls}">', html, count=1)
        changed.append(f"body->{cls}")

    # 4. 顶部导航 + 主容器
    if "site-header" not in html:
        crumb = infer_crumb(html)
        if '<div class="container">' in html:
            header_no_main = HEADER_TPL.format(crumb=crumb).split("<main")[0].rstrip("\n") + "\n"
            html = html.replace('<div class="container">', '<main class="container">', 1)
            html = re.sub(r"<body[^>]*>", lambda m: m.group(0) + "\n" + header_no_main, html, count=1)
        else:
            html = re.sub(r"<body[^>]*>", lambda m: m.group(0) + "\n" + HEADER_TPL.format(crumb=crumb), html, count=1)
        changed.append("注入site-header")

    # 5. 组件类重命名
    for a, b in CLASS_MAP:
        if a in html:
            html = html.replace(a, b)
            changed.append(f"{a}->{b}")

    # 6. H1 + title 规范化
    if "report-title" not in html:
        html = transform_h1(html)
        changed.append("H1->report-title")
    if "terry-style.css" in html:
        html = normalize_title(html)
        changed.append("title规范化")

    # 7. 页脚: 替换文末旧 <hr>...数据来源... 块, 或补 footer
    if "site-footer" not in html:
        m = re.search(r"<hr>\s*<p[^>]*>.*?数据来源.*?</p>", html, re.S)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(0)).strip()
            text = re.sub(r"\s*\|\s*制作：.*$", "", text)   # 去掉 " | 制作：..."
            text = text.replace("|", "｜")
            html = html[:m.start()] + FOOTER_TPL.format(source=text) + html[m.end():]
        else:
            block = FOOTER_TPL.format(source="数据来源：公司年度报告等官方渠道")
            if "</body>" in html:
                html = html.replace("</body>", block + "\n</body>", 1)
            elif "</html>" in html:
                html = html.replace("</html>", block + "\n</body>\n</html>", 1)
            else:
                html += block + "\n</body>\n</html>"
        changed.append("注入site-footer")

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] {path}  ({theme})  变更: {', '.join(changed) if changed else '无'}")


if __name__ == "__main__":
    main()
