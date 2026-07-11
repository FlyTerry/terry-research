#!/usr/bin/env python3
# 从各年年报"主要会计数据和财务指标"文本汇总表提取官方口径历史数据。
# 每份年报给出 3 个年度(当年/上年/前年), 跨报告串联 2021-2025 并在重叠年交叉验证。
# 适用: 神火/兴业/藏格 A股 + 紫金 A+H。用法: python3 tools/extract_summary_financials.py <company_dir>
import sys, os, re, glob, json
import pdfplumber

NUM = re.compile(r"-?[0-9][0-9,]*\.?[0-9]*")

# 指标 -> 该行可能出现的标签(任一匹配)
LABELS = {
    "rev":    ["营业收入"],
    "np":     ["归属于上市公司股东的净利润", "归属于母公司股东的净利润"],
    "np_ded": ["归属于上市公司股东的扣除非经常性损益的净利润", "扣除非经常性损益的净利润"],
    "eps":    ["基本每股收益"],
    "roe":    ["加权平均净资产收益率"],
    "assets": ["总资产"],
    "equity": ["归属于上市公司股东的净资产", "归属于母公司股东的净资产", "归属于上市公司股东权益"],
}

def nums(line):
    out = []
    for tok in NUM.findall(line):
        t = tok.replace(",", "")
        if t in ("", "-", "."):
            continue
        try:
            out.append(float(t))
        except ValueError:
            pass
    return out

def find_summary_text(pdf):
    n = min(40, len(pdf.pages))
    texts = [pdf.pages[i].extract_text() or "" for i in range(n)]
    for i in range(n):
        if "主要会计数据" in texts[i]:
            # 汇总表常跨 2 页(每股收益/净资产收益率 溢出到次页), 拼接相邻页
            combo = texts[i] + "\n" + (texts[i + 1] if i + 1 < n else "")
            if "每股收益" in combo and ("总资产" in combo or "净资产" in combo):
                return combo
    return None

def row_vals(text, labels):
    # 年度值 = 前两个数 + 最后一个数(跳过中间"增减%"及百分号)
    for ln in text.splitlines():
        s = ln.strip()
        for lab in labels:
            if s.startswith(lab):
                ns = nums(s)
                if len(ns) >= 3:
                    return [ns[0], ns[1], ns[-1]]
    return None

def extract(path):
    with pdfplumber.open(path) as pdf:
        t = find_summary_text(pdf)
    if not t:
        return None
    # 年度取自文件名: A股汇总表恒为 [当年, 上年, 前年]
    m = re.search(r"(20\d{2})", os.path.basename(path))
    if not m:
        return None
    ry = int(m.group(1))
    ys = [ry, ry - 1, ry - 2]
    res = {y: {} for y in ys}
    for key, labs in LABELS.items():
        v = row_vals(t, labs)
        if v:
            for j, y in enumerate(ys):
                res[y][key] = v[j]
    return ys, res

def main():
    d = sys.argv[1]
    merged = {}
    overlap = {}  # 交叉验证记录
    for f in sorted(glob.glob(os.path.join(d, "*年报.pdf"))):
        if "半年" in f:
            continue
        r = extract(f)
        base = os.path.basename(f)
        if not r:
            print("!! 无汇总表:", base); continue
        ys, res = r
        print(f"=== {base} 覆盖 {ys} ===")
        for y in ys:
            dd = res[y]
            print(f"  {y}: 营收={dd.get('rev')} 归母净利={dd.get('np')} "
                  f"EPS={dd.get('eps')} ROE={dd.get('roe')} 净资产={dd.get('equity')} 总资产={dd.get('assets')}")
        for y in ys:
            for k, v in res[y].items():
                if y in merged and k in merged[y] and abs(merged[y][k] - v) > max(1, abs(v) * 0.005):
                    overlap.setdefault(y, {})[k] = f"DIFF {merged[y][k]} vs {v}"
                merged.setdefault(y, {})[k] = v
    print("\n===== 合并 2021-2025 (官方口径) =====")
    hdr = f"{'年份':<6}{'营收(亿)':>11}{'归母净利(亿)':>13}{'EPS':>8}{'ROE%':>8}{'归母净资产(亿)':>15}{'总资产(亿)':>12}"
    print(hdr)
    for y in range(2021, 2026):
        if y not in merged: continue
        m = merged[y]
        def a(k, dv=1e8, d=2):
            return f"{m[k]/dv:.{d}f}" if k in m else "  -"
        print(f"{y:<6}{a('rev'):>11}{a('np'):>13}"
              f"{(f'{m['eps']:.4f}' if 'eps' in m else '  -'):>8}"
              f"{(f'{m['roe']:.2f}' if 'roe' in m else '  -'):>8}"
              f"{a('equity'):>15}{a('assets'):>12}")
    if overlap:
        print("\n-- ⚠️ 重叠年交叉验证差异 --")
        print(json.dumps(overlap, ensure_ascii=False, indent=1))
    else:
        print("\n-- 重叠年交叉验证: 全部一致 ✓ --")

if __name__ == "__main__":
    main()
