#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量把研究报告改造为两栏布局（自动生成 sticky 侧边目录 + 回到顶部 + 阅读进度 + 章节高亮）。

改造内容:
  1. 从报告所有 <h2> 章节标题提取文本，给每个 h2 加 id（ch1..chN），自动生成 <nav class="toc toc--side">
  2. 主内容包裹为 <div class="container report-layout__main">，<main> 改为 .report-layout(grid)，左侧 aside 放 sticky TOC
  3. 在 </body> 前注入 .read-progress / .to-top 与 <script src="assets/app.js">

幂等: 已含 report-layout__main 的报告自动跳过；已含 assets/app.js 引用的不重复注入。

用法:
  python3 tools/apply_layout_v2.py <file.html> [file2 ...]
  python3 tools/apply_layout_v2.py            # 默认处理当前目录除 index.html 外的所有报告
"""
import os
import re
import sys

H2_RE = re.compile(r'<h2([^>]*)>(.*?)</h2>', re.DOTALL | re.IGNORECASE)
MAIN_OPEN_RE = re.compile(r'<main class="container">')
MAIN_CLOSE = '</main>'

APP_JS = 'assets/app.js'
READ_PROGRESS = '<div class="read-progress" aria-hidden="true"></div>'
TO_TOP = '<button class="to-top" aria-label="回到顶部" title="回到顶部">↑</button>'
SCRIPT_TAG = '<script src="%s"></script>' % APP_JS

EMOJI_RE = re.compile(
    r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
    r'\u2190-\u21FF\u2300-\u23FF\u25A0-\u25FF\u2B00-\u2BFF]'
)


def build_toc(html):
    """给所有 h2 加 id，返回 (new_html, toc_html)。无 h2 时返回 (html, None)。"""
    h2s = list(H2_RE.finditer(html))
    if not h2s:
        return html, None
    items = []
    offset = 0
    for i, m in enumerate(h2s, 1):
        attrs = m.group(1)
        text = m.group(2)
        toc_text = re.sub(r'<[^>]+>', '', text)       # 去标签
        toc_text = EMOJI_RE.sub('', toc_text).strip()   # 去 emoji/符号
        if 'id=' in attrs:
            id_m = re.search(r'id="([^"]+)"', attrs)
            id_val = id_m.group(1) if id_m else 'ch%d' % i
            new_tag = m.group(0)
        else:
            id_val = 'ch%d' % i
            new_tag = '<h2 id="%s"%s>%s</h2>' % (id_val, attrs, text)
        start, end = m.start() + offset, m.end() + offset
        html = html[:start] + new_tag + html[end:]
        offset += len(new_tag) - (end - start)
        items.append('<li><a href="#%s">%s</a></li>' % (id_val, toc_text))
    toc = (
        '<nav class="toc toc--side">\n'
        '  <div class="toc__title">目录</div>\n'
        '  <ol>' + ''.join(items) + '</ol>\n'
        '</nav>'
    )
    return html, toc


def transform(path):
    with open(path, encoding='utf-8') as f:
        html = f.read()
    changed = []

    if 'report-layout__main' in html:
        return path, ['已处理-跳过'], False

    html, toc = build_toc(html)
    if toc is None:
        return path, ['无 h2 章节, 跳过'], False

    if MAIN_OPEN_RE.search(html):
        new_main_open = (
            '<main class="report-layout">\n'
            '    <aside class="report-layout__aside">\n'
            '        ' + toc + '\n'
            '    </aside>\n'
            '    <div class="container report-layout__main">\n'
        )
        html = MAIN_OPEN_RE.sub(new_main_open, html, count=1)
        html = html.replace(MAIN_CLOSE, '    </div>\n</main>', 1)
        changed.append('两栏布局+自动TOC(%d章)' % toc.count('<li>'))
    else:
        return path, ['无 <main class=container>', '跳过'], False

    if 'assets/app.js' not in html:
        inject = '\n%s\n%s\n    %s\n' % (READ_PROGRESS, TO_TOP, SCRIPT_TAG)
        if '</body>' in html:
            html = html.replace('</body>', inject + '</body>', 1)
        else:
            html += inject
        changed.append('注入进度条/回到顶部/JS')
    else:
        changed.append('JS已存在-跳过注入')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path, changed, True


if __name__ == '__main__':
    files = sys.argv[1:]
    if not files:
        files = [f for f in os.listdir('.')
                 if f.endswith('.html') and f != 'index.html']
    for p in files:
        if not os.path.isfile(p):
            continue
        path, log, ok = transform(p)
        print('[%s] %s: %s' % ('OK' if ok else 'SKIP', path, ', '.join(log)))
