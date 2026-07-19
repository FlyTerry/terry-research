#!/usr/bin/env python3
"""Wrap wide tables (>=8 columns) in <div class="table-wrap"> for horizontal scrolling.
Idempotent: won't double-wrap tables already inside .table-wrap.

Run: python3 tools/wrap_wide_tables.py
"""

import re
import glob
import os

def wrap_wide_tables(filepath):
    with open(filepath, 'r') as f:
        html = f.read()

    # Find all <table...>...</table> blocks with their positions
    pattern = re.compile(r'<table[^>]*>', re.IGNORECASE)
    changes = []  # (pos, '<div...>') for insertion

    for m in pattern.finditer(html):
        start = m.start()
        end_tag = html.find('</table>', m.end())
        if end_tag == -1:
            continue
        table_inner = html[m.end():end_tag]

        # Count <th> in this table
        th_count = len(re.findall(r'<th[>\s]', table_inner))
        if th_count < 7:
            continue

        # Check if already inside a .table-wrap (look back up to 200 chars before table)
        before = html[max(0, start-200):start]
        last_div = before.rfind('<div class="table-wrap">')
        last_div_close = before.rfind('</div>')
        if last_div > last_div_close:
            continue  # already wrapped

        # Check if we already marked it for wrapping
        if any(abs(c[0] - start) < 10 for c in changes if c[1].startswith('<div')):
            continue

        changes.append((start, '<div class="table-wrap">'))
        changes.append((end_tag + len('</table>'), '</div>'))

    if not changes:
        return 0

    # Apply changes in reverse order (so positions stay valid)
    changes.sort(key=lambda x: x[0], reverse=True)
    for pos, text in changes:
        html = html[:pos] + text + html[pos:]

    with open(filepath, 'w') as f:
        f.write(html)
    return len(changes) // 2  # pair count

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reports = sorted(glob.glob('*-report.html'))
    total = 0
    for f in reports:
        n = wrap_wide_tables(f)
        if n:
            print(f'{f}: {n} table(s) wrapped')
            total += n
    print(f'\nTotal: {total} tables wrapped in {sum(1 for _ in reports)} reports')
