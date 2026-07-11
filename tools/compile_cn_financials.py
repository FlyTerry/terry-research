#!/usr/bin/env python3
# 编译某公司 2021-2025 历史财务序列（含交叉验证）
# 依赖: tools/extract_cn_financials.py（合并利润表/资产负债表直提）
# 用法: python3 tools/compile_cn_financials.py <company_dir>
import sys, os, re, json, glob, importlib.util

spec = importlib.util.spec_from_file_location("ex", os.path.join(os.path.dirname(__file__), "extract_cn_financials.py"))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)

def compile_company(d):
    raw = {}
    for f in sorted(glob.glob(os.path.join(d, "*.pdf"))):
        base = os.path.basename(f)
        m = re.search(r"(20\d{2})", base)
        if not m or "半年报" in base: continue
        y = int(m.group(1))
        raw[y] = ex.extract_report(f, y)
    YEARS = [2021, 2022, 2023, 2024, 2025]
    out = {y: {} for y in YEARS}
    metrics = ["rev", "cost", "np", "eps", "equity"]
    for M in metrics:
        for y in YEARS:
            cur = raw.get(y, {}).get(M, (None, None))[0]
            if cur is None and y+1 in raw:
                cur = raw[y+1].get(M, (None, None))[1]  # 次年比较栏
            out[y][M] = cur
    # 交叉验证: 当年(y) 应 == 次年(y+1)的上年栏
    val = {}
    for M in metrics:
        for y in YEARS:
            cur = raw.get(y, {}).get(M, (None, None))[0]
            prev_next = raw.get(y+1, {}).get(M, (None, None))[1] if y+1 in raw else None
            if cur is not None and prev_next is not None:
                diff = abs(cur - prev_next) / (abs(cur) + 1e-9)
                val[f"{M}_{y}"] = "OK" if diff < 0.005 else f"DIFF {diff*100:.2f}%"
    return raw, out, val

def main():
    d = sys.argv[1]
    raw, out, val = compile_company(d)
    print(f"===== {d} =====")
    print(f"{'年份':<6}{'营收(亿)':>12}{'成本(亿)':>12}{'归母净利(亿)':>14}{'净利率%':>9}{'毛利率%':>9}{'EPS':>8}{'归母权益(亿)':>14}")
    for y in [2021,2022,2023,2024,2025]:
        r=out[y]
        rev=r.get('rev'); cost=r.get('cost'); np_=r.get('np'); eps=r.get('eps'); eq=r.get('equity')
        gm = (rev-cost)/rev*100 if rev and cost else None
        nm = np_/rev*100 if rev and np_ else None
        def fmt(v, div=1e8, d=2):
            return f"{v/div:.{d}f}" if v is not None else "  -"
        print(f"{y:<6}{fmt(rev):>12}{fmt(cost):>12}{fmt(np_):>14}"
              f"{(f'{nm:.1f}' if nm is not None else '  -'):>9}"
              f"{(f'{gm:.1f}' if gm is not None else '  -'):>9}"
              f"{(f'{eps:.2f}' if eps is not None else '  -'):>8}"
              f"{fmt(eq):>14}")
    # ROE (平均权益)
    print("\n-- ROE (归母净利 / 平均归母权益) --")
    for y in [2021,2022,2023,2024,2025]:
        np_=out[y].get('np'); eq_y=out[y].get('equity'); eq_prev=out[y-1].get('equity') if y-1 in out else None
        if np_ and eq_y and eq_prev:
            roe=np_/((eq_y+eq_prev)/2)*100
            print(f"  {y}: ROE≈{roe:.2f}%  (权益 {eq_prev/1e8:.1f}→{eq_y/1e8:.1f}亿)")
    print("\n-- 交叉验证 (当年 vs 次年比较栏) --")
    for k,v in sorted(val.items()):
        if v!="OK": print(f"  ⚠️ {k}: {v}")
    print("  (未列出的指标均 OK)")

if __name__ == "__main__":
    main()
