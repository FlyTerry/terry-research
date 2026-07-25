#!/usr/bin/env python3
"""嘉友国际非洲物流网络图 v2 —— 节点与路线突出 + 标签优化版
"""

import shapefile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import numpy as np

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'figure.dpi': 150,
})

# ── 数据 ──────────────────────────────────────────────────────
sf = shapefile.Reader("/tmp/ne_110m_admin_0_countries.shp")
records = sf.records()
shapes = sf.shapes()

TARGET_COUNTRIES = {
    'Democratic Republic of the Congo', 'Zambia', 'United Republic of Tanzania',
    'Angola', 'Namibia', 'Zimbabwe', 'Mozambique', 'Malawi', 'Botswana',
    'South Africa', 'Republic of the Congo', 'Gabon', 'Equatorial Guinea',
    'Cameroon', 'Central African Republic', 'South Sudan', 'Uganda', 'Rwanda',
    'Burundi', 'Kenya', 'Madagascar', 'eSwatini', 'Lesotho',
}

# 重点关注国
CORE_LABELS = {
    'Democratic Republic of the Congo': ('刚果(金)', -2.5, -0.5),
    'Zambia':          ('赞比亚',    1.0,  0.5),
    'United Republic of Tanzania':        ('坦桑尼亚',  0.5, -1.0),
    'Angola':          ('安哥拉',   -0.5,  0.0),
    'Namibia':         ('纳米比亚', -1.0,  1.0),
    'Mozambique':      ('莫桑比克',  0.5,  0.0),
}

# 节点坐标
COPPER_BELT = {
    '科卢韦齐':  (-10.72, 25.47),
    '卢本巴希':  (-11.67, 27.48),
    '恩多拉':    (-12.97, 28.63),
}

# 嘉友节点 + 单独配置的 label 位置 (dlat, dlon, anchor)
JIAYOU_NODES = {
    '卡萨项目':     {'pos': (-12.28, 27.85), 'offset': (-2.5, -1.2), 'status': '2023运营'},
    '萨卡尼亚项目': {'pos': (-12.75, 28.57), 'offset': ( 1.5,  1.8), 'status': '2026运营'},
    '莫坎博项目':   {'pos': (-12.45, 28.38), 'offset': ( 0.5, -2.0), 'status': '在建·2027'},
    '迪洛洛项目':   {'pos': (-10.68, 22.33), 'offset': ( 0.0,  1.8), 'status': '待开工·~2030'},
}

PORTS = {
    '达累斯萨拉姆':  (-6.79, 39.21, 0.5, 0.5),
    '洛比托':       (-12.35, 13.55, -0.5, 0.5),
    '鲸湾':          (-22.96, 14.50, 0.0, 1.0),
    '贝拉':          (-19.83, 34.85, 0.5, 0.5),
}

OTHER_CITIES = {
    '卡皮里\n姆波希': (-13.98, 28.68, 1.5, 0.5),
}

# 路线
ROUTES = [
    {  # 东路主通道
        'points': [(-11.67, 27.48), (-12.28, 27.85), (-12.75, 28.57),
                   (-12.97, 28.63), (-13.50, 29.50), (-12.00, 31.50),
                   (-10.00, 33.50), (-8.50, 35.50), (-6.79, 39.21)],
        'color': '#E85D3A', 'width': 3.0, 'style': '-', 'alpha': 0.9,
    },
    {  # 莫坎博支线
        'points': [(-12.97, 28.63), (-12.45, 28.38)],
        'color': '#F09070', 'width': 2.2, 'style': '--', 'alpha': 0.75,
    },
    {  # 西路
        'points': [(-10.72, 25.47), (-10.68, 22.33), (-11.00, 19.00),
                   (-12.00, 16.00), (-12.35, 13.55)],
        'color': '#185FA5', 'width': 3.0, 'style': '-', 'alpha': 0.9,
    },
    {  # 南路
        'points': [(-12.97, 28.63), (-17.00, 24.00), (-19.00, 20.00), (-22.96, 14.50)],
        'color': '#888888', 'width': 1.5, 'style': ':', 'alpha': 0.5,
    },
    {  # 贝拉
        'points': [(-12.97, 28.63), (-16.00, 30.00), (-19.83, 34.85)],
        'color': '#AAAAAA', 'width': 1.2, 'style': ':', 'alpha': 0.4,
    },
]

TAZARA = {
    'points': [(-13.98, 28.68), (-13.00, 30.50), (-11.50, 33.50),
               (-10.00, 35.00), (-8.50, 36.50), (-6.79, 39.21)],
    'color': '#D4A017', 'width': 1.8,
}

LOBITO = {
    'points': [(-10.72, 25.47), (-10.68, 22.33), (-11.00, 19.00),
               (-12.00, 16.00), (-12.35, 13.55)],
    'color': '#4488CC', 'width': 1.4,
}

# ── 制图 ──────────────────────────────────────────────────────
def build_patch(shape):
    parts = list(shape.parts) + [len(shape.points)]
    paths = []
    for i in range(len(parts) - 1):
        pts = shape.points[parts[i]:parts[i+1]]
        if len(pts) < 2:
            continue
        vertices = [(p[0], p[1]) for p in pts]
        codes = [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 1)
        paths.append(Path(vertices, codes))
    return Path.make_compound_path(*paths)

def add_country_label(ax, shape, text, color='#5D6D7E', size=10, weight='normal'):
    """在国家几何中心加文本"""
    try:
        cx = sum(p[0] for p in shape.points) / len(shape.points)
        cy = sum(p[1] for p in shape.points) / len(shape.points)
        # 简单质心（粗糙但够用）
        ax.text(cx, cy, text, fontsize=size, ha='center', va='center',
                color=color, fontweight=weight, zorder=3,
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='none', alpha=0.45))
    except:
        pass

def main():
    fig, ax = plt.subplots(figsize=(18, 16))
    ax.set_xlim(8, 46)
    ax.set_ylim(-28, 2)
    ax.set_aspect('equal')
    ax.set_facecolor('#DCE8F0')   # 坐标轴底色 = 海洋色，不被任何矩形覆盖

    # 国家（直接铺在海洋底色上，国家未覆盖区域即为海洋）
    for i, rec in enumerate(records):
        name = rec[3]
        if name not in TARGET_COUNTRIES:
            continue
        patch = build_patch(shapes[i])
        ax.add_patch(PathPatch(patch, facecolor='#F5F2EC',
                               edgecolor='#C8C4B8', linewidth=0.7, zorder=2))

    # 重点国家名标注
    for i, rec in enumerate(records):
        name = rec[3]
        if name in CORE_LABELS:
            label, dx, dy = CORE_LABELS[name]
            add_country_label(ax, shapes[i], label, color='#5D6D7E', size=11)
            break  # simplified, just one per country

    # 用国家质心做 label（找一遍）
    name_to_centroid = {}
    for i, rec in enumerate(records):
        name = rec[3]
        if name in CORE_LABELS:
            shape = shapes[i]
            try:
                cx = sum(p[0] for p in shape.points) / len(shape.points)
                cy = sum(p[1] for p in shape.points) / len(shape.points)
                name_to_centroid[name] = (cx, cy)
            except:
                pass

    for name, (label, dx, dy) in CORE_LABELS.items():
        if name in name_to_centroid:
            cx, cy = name_to_centroid[name]
            # 简单质心修正：放到几何中心略偏的内陆
            ax.text(cx + dx, cy + dy, label, fontsize=11, ha='center', va='center',
                    color='#5D6D7E', fontweight='bold', zorder=3,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              edgecolor='none', alpha=0.55))

    # 铁路（先画铁路，让路线覆盖在上面）
    for rail, dashes in [(TAZARA, (8, 4)), (LOBITO, (6, 3))]:
        ax.plot([p[1] for p in rail['points']], [p[0] for p in rail['points']],
                color=rail['color'], linewidth=rail['width'], linestyle='--',
                dashes=dashes, alpha=0.75, zorder=4)

    # 路线
    for route in ROUTES:
        ax.plot([p[1] for p in route['points']], [p[0] for p in route['points']],
                color=route['color'], linewidth=route['width'],
                linestyle=route['style'], alpha=route['alpha'], zorder=5,
                solid_capstyle='round', solid_joinstyle='round')

    # 140km断点标注（避开节点标签群）
    ax.annotate('', xy=(28.68, -13.98), xytext=(28.68, -13.98),
                xycoords='data', textcoords='data')
    ax.text(30.5, -16.0, '※ 恩多拉—卡皮里 140km\n断点 (ZRL运营, 嘉友无权益)', fontsize=9.5,
            color='#B71C1C', ha='center', va='center', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#FFEBEE',
                      edgecolor='#B71C1C', alpha=0.95), zorder=12)
    # 断点连接线
    ax.annotate('', xy=(28.7, -14.5), xytext=(30.4, -15.7),
                arrowprops=dict(arrowstyle='-', color='#B71C1C', lw=1.0,
                                linestyle='--', alpha=0.7), zorder=11)

    # 嘉友节点（每节点独立 label box + 引线）
    for label, info in JIAYOU_NODES.items():
        lat, lon = info['pos']
        dlat, dlon = info['offset']
        # 星标
        ax.scatter(lon, lat, marker='*', s=420, c='#D32F2F', edgecolors='white',
                   linewidths=1.5, zorder=10)
        # 标签 + 状态
        status_colors = {'2023运营': '#2E7D32', '2026运营': '#1565C0',
                         '在建·2027': '#E65100', '待开工·~2030': '#757575'}
        sc = status_colors.get(info['status'], '#555')
        ax.text(lon + dlon, lat + dlat, f'{label}\n[{info["status"]}]',
                fontsize=9.5, ha='center', va='center', fontweight='bold',
                color='#B71C1C', zorder=11,
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                          edgecolor=sc, alpha=0.95, linewidth=1.2))
        # 引线（指向节点星标）
        ax.annotate('', xy=(lon, lat), xytext=(lon + dlon * 0.6, lat + dlat * 0.6),
                    arrowprops=dict(arrowstyle='-', color=sc, lw=0.8,
                                    alpha=0.7), zorder=9)

    # 铜矿带城市
    for label, (lat, lon) in COPPER_BELT.items():
        ax.scatter(lon, lat, marker='o', s=110, c='#2C3E50', edgecolors='white',
                   linewidths=1.8, zorder=10)
        # 卢本巴希放上方避开卡萨，恩多拉放下方避开萨卡尼亚
        offsets = {'卢本巴希': (-0.6, -1.6), '恩多拉': (-0.6, -1.5), '科卢韦齐': (0.0, -1.4)}
        dlat, dlon = offsets[label]
        ax.text(lon + dlon, lat + dlat, label, fontsize=10.5, fontweight='bold',
                color='#2C3E50', ha='center', va='center', zorder=11,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                          edgecolor='#BDC3C7', alpha=0.85))

    # 海港
    for label, (lat, lon, dlat, dlon) in PORTS.items():
        ax.scatter(lon, lat, marker='s', s=130, c='#1565C0', edgecolors='white',
                   linewidths=1.8, zorder=10)
        ax.text(lon + dlon, lat + dlat, label, fontsize=10, fontweight='bold',
                color='#0D47A1', ha='center', va='center', zorder=11,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#E3F2FD',
                          edgecolor='#1565C0', alpha=0.9))

    # 卡皮里姆波希
    for label, (lat, lon, dlat, dlon) in OTHER_CITIES.items():
        ax.scatter(lon, lat, marker='o', s=60, c='#666666', edgecolors='white',
                   linewidths=1.2, zorder=10)
        ax.text(lon + dlon, lat + dlat, label, fontsize=9, color='#555555',
                ha='center', va='center', zorder=11,
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='#999', alpha=0.85))

    # 比例尺
    scale_lon_start = 9.5
    scale_lon_end = 14.0
    scale_lat = -26.5
    ax.plot([scale_lon_start, scale_lon_end], [scale_lat, scale_lat],
            color='#2C3E50', linewidth=2.5, zorder=12)
    ax.plot([scale_lon_start, scale_lon_start], [scale_lat - 0.2, scale_lat + 0.2],
            color='#2C3E50', linewidth=1.5, zorder=12)
    ax.plot([scale_lon_end, scale_lon_end], [scale_lat - 0.2, scale_lat + 0.2],
            color='#2C3E50', linewidth=1.5, zorder=12)
    # 1° ~ 111km, 4.5° ~ 500km
    ax.text((scale_lon_start + scale_lon_end) / 2, scale_lat + 0.5, '~ 500 KM',
            fontsize=9, ha='center', va='bottom', color='#2C3E50', fontweight='bold')

    # 路线里程标注
    route_milestones = [
        (28.4, -13.4, '~1,860km\n(铁路 1,860km)'),
        (16.0, -12.0, '~1,300km\n(铁路)'),
    ]
    # 算了，里程放在路线中段容易乱，不加

    # 图例
    legend_elements = [
        mpatches.Patch(facecolor='white', edgecolor='#2C3E50', linewidth=0.5, label='═══ 路线 ═══'),
        mpatches.Patch(color='#E85D3A', alpha=0.9, label='东路·达累斯萨拉姆通道 (嘉友90%控股)'),
        mpatches.Patch(color='#F09070', alpha=0.75, label='莫坎博替代线 (在建)'),
        mpatches.Patch(color='#185FA5', alpha=0.9, label='西路·洛比托走廊 (51%合伙·待开工)'),
        mpatches.Patch(color='#888888', alpha=0.5, label='南路·鲸湾港 (远期)'),
        plt.Line2D([0], [0], color='#D4A017', linewidth=1.8, linestyle='--', dashes=(8, 4),
                    label='坦赞铁路 (嘉友5%参股·2028-29通车)'),
        plt.Line2D([0], [0], color='#4488CC', linewidth=1.4, linestyle='--', dashes=(6, 3),
                    label='洛比托铁路 (LAR·嘉友0%股权)'),
        mpatches.Patch(facecolor='white', edgecolor='#2C3E50', linewidth=0.5, label='═══ 节点 ═══'),
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='#D32F2F',
                    markersize=14, linewidth=0, label='嘉友物流节点 (陆港/收费站)'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#2C3E50',
                    markersize=9, linewidth=0, label='铜矿带城市 (主要货源)'),
        plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#1565C0',
                    markersize=9, linewidth=0, label='远洋出海口'),
    ]
    legend = ax.legend(handles=legend_elements, loc='lower left',
                       fontsize=8.5, framealpha=0.94, edgecolor='#C8C4B8',
                       facecolor='white', ncol=2,
                       title='嘉友国际非洲物流网络 · 节点与路线图',
                       title_fontsize=10.5, borderpad=0.8, labelspacing=0.5)
    legend._legend_box.align = 'left'

    # 标题
    ax.set_title('嘉友国际 (603871.SH) 非洲物流节点与出海通道', fontsize=18, fontweight='bold',
                 color='#2C3E50', pad=18, loc='center')

    # 来源
    ax.text(0.99, 0.005,
            'Terry Research · 2026年7月 制图 | 底图: Natural Earth 110m | 节点坐标: 嘉友国际年报/公告交叉核对',
            transform=ax.transAxes, fontsize=7.5, color='#888888', ha='right', va='bottom',
            style='italic')

    # 坐标轴处理
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor('#B0ADA5')
        spine.set_linewidth(0.8)

    # 关键补充
    # 1. 距离参考：约 1,860km（坦赞铁路总长）
    ax.text(43, -25, '参考：坦赞铁路全长 1,860km\n      洛比托走廊安哥拉段 1,300km',
            fontsize=8, ha='right', va='bottom', color='#777777',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#FAFAFA',
                      edgecolor='#D5D2C5', alpha=0.9))

    plt.tight_layout(pad=1.5)
    out_path = '/Users/chengdandan/Documents/terry-research/assets/jiayou-africa-routes-nodes.png'
    plt.savefig(out_path, dpi=200, bbox_inches='tight',
                facecolor='#F0EDE4', edgecolor='none')
    print(f'✅ 保存: {out_path}')
    plt.close()

if __name__ == '__main__':
    main()
