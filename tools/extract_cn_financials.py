#!/usr/bin/env python3
# 从 A 股年报 PDF 提取合并利润表/资产负债表关键指标（中文，鲁棒版）
# 用法: python3 tools/extract_cn_financials.py <company_dir> [years...]
import sys, os, re, json, glob
import pdfplumber

NUM_RE = re.compile(r"\(?-?[0-9][0-9,]*\.?[0-9]*\)?")

def parse_num(s):
    if not s: return None
    s = str(s).strip().replace(",", "")
    if s in ("", "-", "—", "－", "—"):
        return None
    # 含中文/字母的单元格是标签, 不当数字(避免"1.归属于..."被当成 1.0)
    if re.search(r"[\u4e00-\u9fff A-Za-z%]", s):
        return None
    neg = s.startswith("(") and s.endswith(")")
    m = NUM_RE.search(s)
    if not m: return None
    tok = m.group(0).replace("(", "").replace(")", "")
    if tok in ("", ".", "-"): return None
    v = float(tok)
    return -v if neg else v

def year_of(s):
    m = re.search(r"(20\d{2})", s or "")
    return int(m.group(1)) if m else None

def find_block(pdf, title, stop_titles, anchor_labels=None, require=None, page_texts=None):
    """定位真实报表区块的页码列表(高效: 先文本预筛, 只对候选页抽表)。
    require: 页文本须全部包含的子串(锁定真正合并报表, 排除摘要/目录)。
    """
    n = len(pdf.pages)
    if page_texts is None:
        page_texts = [pdf.pages[i].extract_text() or "" for i in range(n)]
    start = None
    # 1) require 优先: 页文本含全部子串
    if require:
        for i in range(n):
            if all(q in page_texts[i] for q in require):
                start = i; break
    # 2) anchor 回退
    if start is None and anchor_labels:
        for i in range(n):
            if any(a in page_texts[i] for a in anchor_labels):
                start = i; break
    # 3) title 回退
    if start is None:
        for i in range(n):
            if title in page_texts[i]:
                start = i; break
    if start is None:
        return []
    pages = [start]
    for i in range(start + 1, n):
        if any(st in page_texts[i] for st in stop_titles):
            # 边界页可能同时含本表尾部(如归母净利润/每股收益)与下一张表标题;
            # 一并纳入(文档顺序下本表行在前, pick 取首个匹配仍为本表值)
            pages.append(i)
            break
        pages.append(i)
    return pages

def extract_table_rows(pdf, pages):
    rows = []
    for i in pages:
        for tbl in pdf.pages[i].extract_tables():
            for r in tbl:
                if r and any(c for c in r):
                    rows.append(r)
    return rows

def header_year_cols(rows):
    """从行中找含'年度'/年份的表头行, 返回 {year: col_index}。"""
    best = {}
    for r in rows:
        if not r: continue
        yrs = [(year_of(c), j) for j, c in enumerate(r) if year_of(c)]
        if len(yrs) >= 2:
            best = {y: j for y, j in yrs}
            break
    return best

def pick(rows, *keywords, prefer=None):
    """返回首个标签含全部 keywords 的行; prefer 子串优先。标签可能在任意单元格。"""
    def rowtext(r):
        return " ".join(str(c) for c in r if c)
    cands = [r for r in rows if r and all(k in rowtext(r) for k in keywords)]
    if not cands:
        cands = [r for r in rows if r and any(k in rowtext(r) for k in keywords)]
    if not cands:
        return None
    if prefer:
        for r in cands:
            if prefer in rowtext(r):
                return r
    return cands[0]

def extract_report(path, nominal_year):
    out = {}
    def get(r):
        """取一行中的前两个数值(当年, 上年)。避开合并表头列错位。"""
        if not r: return (None, None)
        nums = [parse_num(c) for c in r if parse_num(c) is not None]
        if len(nums) >= 2:
            return (nums[0], nums[1])
        if len(nums) == 1:
            return (nums[0], None)
        return (None, None)
    def pick_np(rows):
        # 优先"归属于母公司股东/所有者的净利润"; 排除"扣除非经常性损益"
        for r in rows:
            rt = " ".join(str(c) for c in r if c)
            if "归属于" in rt and ("股东的净利润" in rt or "所有者的净利润" in rt) \
               and "扣除" not in rt and "综合收益" not in rt:
                return r
        return None
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        page_texts = [pdf.pages[i].extract_text() or "" for i in range(n)]
        # ---- 合并利润表 ----
        blk = find_block(pdf, "合并利润表",
                         ["母公司利润表", "合并现金流量表", "财务报表附注"],
                         anchor_labels=["其中：营业收入", "归属于上市公司股东的净利润"],
                         require=["其中：营业收入", "其中：营业成本"],
                         page_texts=page_texts)
        if blk:
            rows = extract_table_rows(pdf, blk)
            out["rev"] = get(pick(rows, "营业收入", prefer="其中：营业收入"))
            out["cost"] = get(pick(rows, "营业成本", prefer="其中：营业成本"))
            out["np"] = get(pick_np(rows))
            out["eps"] = get(pick(rows, "基本每股收益"))
            out["pl_year"] = nominal_year
        # ---- 合并资产负债表: 归母权益 ----
        # require 用真实报表独有的科目(资产总计+负债合计), 排除"主要会计数据"摘要页
        # (摘要页只有"总资产"/"归属于...权益合计"及同比%列, 无"资产总计""负债合计")
        blk2 = find_block(pdf, "合并资产负债表",
                          ["母公司资产负债表", "合并利润表", "合并现金流量表"],
                          anchor_labels=["资产总计", "负债合计"],
                          require=["资产总计", "负债合计"],
                          page_texts=page_texts)
        if blk2:
            rows2 = extract_table_rows(pdf, blk2)
            r_eq = pick(rows2, "归属于母公司股东", "权益合计") or pick(rows2, "归属于母公司所有", "权益合计")
            if r_eq:
                out["equity"] = get(r_eq)
    return out

def main():
    d = sys.argv[1]
    years = [int(y) for y in sys.argv[2:]] if len(sys.argv) > 2 else None
    res = {}
    for f in sorted(glob.glob(os.path.join(d, "*.pdf"))):
        base = os.path.basename(f)
        m = re.search(r"(20\d{2})", base)
        if not m or "半年报" in base: continue
        y = int(m.group(1))
        if years and y not in years: continue
        res[y] = extract_report(f, y)
    print(json.dumps(res, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
