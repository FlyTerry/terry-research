#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正：报告原本带有内联目录章节（<h2>目录</h2> 或 <h2>报告目录</h2> 等，标题文本含「目录」），
被误当作第一章纳入侧边 TOC。本脚本针对已改造为两栏布局的报告：
  1. 删除主内容里的旧内联目录块（含「目录」的 <h2> 到下一个 <h2> 之前）
  2. 删除侧边 .toc--side 中对应的 <li> 项
其余章节 ch 编号在两侧天然一致，无需重排。

用法: python3 tools/fix_inline_toc.py
"""
import glob
import re

INLINE_RE = re.compile(r'<h2[^>]*>[^<]*目录[^<]*</h2>.*?(?=<h2)', re.DOTALL | re.IGNORECASE)
TOC_LI_RE = re.compile(r'<li><a href="#[^"]*">[^<]*目录[^<]*</a></li>')


def fix(path):
    with open(path, encoding='utf-8') as f:
        h = f.read()
    before = h
    if INLINE_RE.search(h):
        h = INLINE_RE.sub('', h)
    if '目录' in h:
        h = TOC_LI_RE.sub('', h)
    if h != before:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(h)
        return True
    return False


if __name__ == '__main__':
    for p in sorted(glob.glob('*.html')):
        if p == 'index.html':
            continue
        if fix(p):
            print('FIXED', p)
