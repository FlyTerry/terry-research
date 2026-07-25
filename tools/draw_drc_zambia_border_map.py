#!/usr/bin/env python3
"""嘉友国际 刚-赞边境三节点局部图 v2 —— 精简清晰版
"""
import shapefile, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS'],
    'axes.unicode_minus': False, 'figure.dpi': 180,
})

sf = shapefile.Reader("/tmp/ne_110m_admin_0_countries.shp")
records = sf.records()
shapes = sf.shapes()

# ── 范围 ──
XLIM, YLIM = (26.5, 30.2), (-14.5, -10.5)

# ── build_patch ──
def build_patch(shape):
    parts = list(shape.parts) + [len(shape.points)]
    paths = []
    for i in range(len(parts)-1):
        pts = shape.points[parts[i]:parts[i+1]]
        if len(pts) < 2: continue
        vertices = [(p[0], p[1]) for p in pts]  # (lon, lat)
        codes = [Path.MOVETO] + [Path.LINETO]*(len(vertices)-1)
        paths.append(Path(vertices, codes))
    return Path.make_compound_path(*paths)

def main():
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(*XLIM); ax.set_ylim(*YLIM)
    ax.set_aspect('equal')
    ax.set_facecolor('#DCE8F0')       # 海洋
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor('#AAA69F'); spine.set_linewidth(0.6)

    # ── 国家 ──
    TARGET = {'Democratic Republic of the Congo', 'Zambia'}
    for i, rec in enumerate(records):
        if rec[3] not in TARGET: continue
        patch = build_patch(shapes[i])
        ax.add_patch(PathPatch(patch, facecolor='#F7F4EC',
                               edgecolor='#B5B0A5', linewidth=0.7, zorder=2))
    ax.text(27.2, -11.0, '刚果（金）', fontsize=13, fontweight='bold',
            color='#7F8C8D', ha='center', va='center', zorder=3, alpha=0.7)
    ax.text(29.2, -12.8, '赞比亚', fontsize=13, fontweight='bold',
            color='#7F8C8D', ha='center', va='center', zorder=3, alpha=0.7)

    # ── 国境线 ──
    ax.axvline(x=28.3, color='#555555', linewidth=1.5, linestyle='--',
               dashes=(8,5), alpha=0.5, zorder=4)
    ax.text(28.42, -11.8, '国 境', fontsize=9.5, color='#444444',
            ha='left', va='center', fontweight='bold', zorder=5, alpha=0.7)

    # ── 既有公路（灰色）──
    GRAY_ROADS = [
        [(-11.67, 27.48), (-11.93, 27.63), (-12.25, 27.83)],      # 卢本巴希→卡松巴莱萨
        [(-12.80, 28.22), (-12.88, 28.42), (-12.97, 28.63)],       # 基特韦→恩多拉
        [(-12.97, 28.63), (-13.50, 28.65), (-13.98, 28.68)],       # 恩多拉→卡皮里
    ]
    for pts in GRAY_ROADS:
        ax.plot([p[1] for p in pts], [p[0] for p in pts],
                color='#AAAAAA', linewidth=1.8, linestyle='-', alpha=0.5, zorder=5)

    # ── 嘉友项目公路（粗彩色线）──
    ROADS = [
        ([(-12.25, 27.83), (-12.30, 28.00), (-12.45, 28.12),
          (-12.55, 28.25), (-12.60, 28.38), (-12.68, 28.48), (-12.75, 28.57)],
         '#D32F2F', 3.5, '卡萨项目 150km 公路 (2023运营)'),
        ([(-12.97, 28.63), (-12.85, 28.60), (-12.75, 28.57)],
         '#E85D3A', 3.2, '萨卡尼亚PPP 恩-萨段 17.26km (2026收费)'),
        ([(-12.97, 28.63), (-12.85, 28.52), (-12.75, 28.42),
          (-12.65, 28.32), (-12.55, 28.25)],
         '#D4845A', 2.5, '萨卡尼亚PPP 恩-穆段 41.7km (在建)'),
        ([(-12.55, 28.25), (-12.50, 28.32), (-12.45, 28.38)],
         '#E65100', 3.2, '莫坎博项目 25.75km (在建)'),
    ]
    for pts, color, width, _ in ROADS:
        ax.plot([p[1] for p in pts], [p[0] for p in pts],
                color=color, linewidth=width, linestyle='-', alpha=0.9,
                zorder=5, solid_capstyle='round', solid_joinstyle='round')

    # ── 公里标 ──
    km_labels = [
        (27.85, -11.98, '~150km', '#D32F2F'),
        (28.60, -12.90, '17.3', '#E85D3A'),
        (28.44, -12.75, '41.7', '#D4845A'),
        (28.32, -12.40, '25.8', '#E65100'),
    ]
    for lon, lat, txt, c in km_labels:
        ax.text(lon, lat, txt, fontsize=8.5, color=c, ha='center', va='center',
                fontweight='bold', zorder=8,
                bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                          edgecolor=c, alpha=0.9))

    # ── 口岸菱形（窄体） ──
    crossings = [
        (-12.25, 27.83, '卡松巴莱萨口岸'),
        (-12.75, 28.57, '萨卡尼亚口岸'),
        (-12.42, 28.35, '莫坎博口岸'),
    ]
    for lat, lon, _ in crossings:
        ax.scatter(lon, lat, marker='D', s=45, c='#444444', edgecolors='white',
                   linewidths=1.0, zorder=9)
    # 统一在右侧标"边境口岸"，避免三个独立 label 挤在一起
    ax.text(29.0, -11.2, '◆ = 边境口岸', fontsize=7.5, color='#555',
            ha='left', va='center', zorder=9,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.7))

    # ── 嘉友节点（label 放外围 + 引线指向位置）──
    # (node_lat, node_lon, label_lat, label_lon, text, color)
    nodes = [
        (-12.28, 27.85, -11.40, 27.00,
         '卡萨项目\n★ 2023已运营\n150km公路+陆港\n利润分配: 90%→80%\n特许权25年',
         '#D32F2F'),
        (-12.75, 28.57, -13.60, 29.35,
         '萨卡尼亚PPP\n★ 2026收费运营\n恩多拉段17.3+穆富利拉段41.7km\n嘉友90%股权·22年\n总投资$76M',
         '#E85D3A'),
        (-12.45, 28.38, -13.10, 27.10,
         '莫坎博项目\n★ 在建·预计2027\n穆富利拉→莫坎博 25.75km\n嘉友90%股权·22年\n主通道替代线',
         '#E65100'),
    ]
    for nlat, nlon, llat, llon, text, color in nodes:
        # 星标
        ax.scatter(nlon, nlat, marker='*', s=350, c=color, edgecolors='white',
                   linewidths=1.5, zorder=10)
        # 标签放在外围
        ax.text(llon, llat, text, fontsize=7.2, color='#333', ha='left', va='top',
                zorder=11, linespacing=1.25,
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                          edgecolor=color, alpha=0.95, linewidth=1.5))
        # 引线：从标签中心指向节点
        mid_lat = (nlat + llat) / 2
        mid_lon = (nlon + llon) / 2
        ax.annotate('', xy=(nlon, nlat), xytext=(mid_lon, mid_lat),
                    arrowprops=dict(arrowstyle='-', color=color, lw=1.0,
                                    alpha=0.6, connectionstyle='arc3,rad=0.1'),
                    zorder=8)

    # ── 城市（单行纯名，每个独立偏移）──
    cities = [
        (-11.67, 27.48, (-0.6, -0.5), '卢本巴希 (铜矿带)'),
        (-12.25, 27.83, (-0.5,  0.4), '卡松巴莱萨'),
        (-12.97, 28.63, ( 0.2, -0.4), '恩多拉 (铜矿带)'),
        (-12.55, 28.25, (-0.2, -0.5), '穆富利拉'),
        (-12.80, 28.22, ( 0.0, -0.6), '基特韦'),
        (-13.98, 28.68, ( 0.2,  0.6), '卡皮里姆波希 →坦赞铁路'),
    ]
    for lat, lon, (dy, dx), label in cities:
        ax.scatter(lon, lat, marker='o', s=45, c='#2C3E50', edgecolors='white',
                   linewidths=1.2, zorder=9)
        ax.text(lon+dx, lat+dy, label, fontsize=7.5, color='#2C3E50',
                ha='center', va='center', zorder=10,
                bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                          edgecolor='#BDC3C7', alpha=0.85))

    # ── 140km 断点提示 ──
    ax.annotate('→ 至卡皮里接坦赞铁路\n  断点 140km (ZRL)', xy=(28.75, -13.5),
                fontsize=8, color='#B71C1C', ha='left', va='center', fontweight='bold',
                zorder=12,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFEBEE',
                          edgecolor='#C62828', alpha=0.95))

    # ── 图例 ──
    legend_items = [
        mpatches.Patch(color='#D32F2F', alpha=0.9, label='卡萨项目 (2023运营)'),
        mpatches.Patch(color='#E85D3A', alpha=0.9, label='萨卡尼亚PPP (2026收费)'),
        mpatches.Patch(color='#E65100', alpha=0.9, label='莫坎博项目 (在建)'),
        mpatches.Patch(color='#AAAAAA', alpha=0.5, label='既有公路'),
        plt.Line2D([0],[0], marker='D', c='w', markerfacecolor='#444', markersize=8,
                    linewidth=0, label='边境口岸'),
    ]
    ax.legend(handles=legend_items, loc='upper left', fontsize=7.5,
              framealpha=0.92, edgecolor='#C8C4B8', facecolor='white',
              title='嘉友国际 · 刚-赞边境三节点', title_fontsize=9,
              borderpad=0.6, labelspacing=0.4)

    # ── 标题 ──
    ax.set_title('刚果（金）—赞比亚边境 · 嘉友国际三大物流节点', fontsize=14,
                 fontweight='bold', color='#2C3E50', pad=12)

    # ── 来源 ──
    ax.text(0.99, 0.01,
            'Terry Research · 2026-07 制图 | 底图: Natural Earth | 坐标: 年报公告',
            transform=ax.transAxes, fontsize=6, color='#999', ha='right', va='bottom')

    # ── 比例尺 ──
    km = 50; deg = km/111.0
    x0, y0 = 27.0, -14.25
    ax.plot([x0, x0+deg], [y0, y0], color='#2C3E50', lw=2.5, zorder=12)
    ax.plot([x0, x0], [y0-0.02, y0+0.02], color='#2C3E50', lw=1.5, zorder=12)
    ax.plot([x0+deg, x0+deg], [y0-0.02, y0+0.02], color='#2C3E50', lw=1.5, zorder=12)
    ax.text(x0+deg/2, y0+0.06, f'{km}KM', fontsize=8, ha='center', va='bottom',
            color='#2C3E50', fontweight='bold')

    plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02)
    out = '/Users/chengdandan/Documents/terry-research/assets/jiayou-corridor-drc-zambia-ports.png'
    plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='#DCE8F0')
    plt.close()
    print(f'✅ {out}')

if __name__ == '__main__':
    main()
