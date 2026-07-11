#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重生成报告侧边目录（保留已有 h2 id，按文档顺序重建 <nav class="toc toc--side">）。

用于报告内容增删章节后，侧边 TOC 锚点过期的情况。
幂等：每次都按当前 h2 重建。
用法: python3 tools/regen_toc.py <file.html> [file2 ...]
"""
import os
import re
import sys

H2_RE = re.compile(r'<h2([^>]*)>(.*?)</h2>', re.DOTALL | re.IGNORECASE)
TOC_NAV_RE = re.compile(r'<nav class="toc toc--side">.*?</nav>', re.DOTALL)
EMOJI_RE = re.compile(
    r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
    r'\u2190-\u21FF\u2300-\u23FF\u25A0-\u25FF\u2B00-\u2BFF]'
)


def regen(html):
    h2s = list(H2_RE.finditer(html))
    if not h2s:
        return html, None
    items = []
    for m in h2s:
        attrs = m.group(1)
        text = m.group(2)
        id_m = re.search(r'id="([^"]+)"', attrs)
        if not id_m:
            continue  # 跳过没有 id 的 h2（理论上不该有）
        id_val = id_m.group(1)
        toc_text = re.sub(r'<[^>]+>', '', text)
        toc_text = EMOJI_RE.sub('', toc_text).strip()
        if not toc_text:
            continue
        items.append('<li><a href="#%s">%s</a></li>' % (id_val, toc_text))
    toc = (
        '<nav class="toc toc--side">\n'
        '  <div class="toc__title">目录</div>\n'
        '  <ol>' + ''.join(items) + '</ol>\n'
        '</nav>'
    )
    if TOC_NAV_RE.search(html):
        html = TOC_NAV_RE.sub(toc, html, count=1)
    return html, toc


def main():
    files = sys.argv[1:] or [f for f in os.listdir('.')
                             if f.endswith('.html') and f != 'index.html']
    for p in files:
        if not os.path.isfile(p):
            continue
        html = open(p, encoding='utf-8').read()
        new_html, toc = regen(html)
        if toc is None:
            print('[%s] 无 h2, 跳过' % p)
            continue
        open(p, 'w', encoding='utf-8').write(new_html)
        print('[%s] TOC 重建, %d 章' % (p, toc.count('<li>')))


if __name__ == '__main__':
    main()
