#!/usr/bin/env python3
"""去水印 v2：单遍大模糊合成
"""
from PIL import Image, ImageFilter, ImageDraw
import numpy as np

SRC = '/Users/chengdandan/.workbuddy/clipboard-images/clipboard-2026-07-25T03-26-12-923Z-74ae0126.png'
OUT = '/Users/chengdandan/Documents/terry-research/assets/jiayou-corridor-drc-zambia-ports.png'

img = Image.open(SRC).convert('RGB')
W, H = img.size
print(f'原图: {W}x{H}')

# 1. 创建水印蒙版（黑=保留原图, 白=替换）
mask = Image.new('L', (W, H), 0)
draw = ImageDraw.Draw(mask)
# 右下角水印区域 - 雪球logo + 傅俊文署名
# 保守估计，覆盖比水印稍大的矩形
draw.rectangle([(640, 455), (W, H)], fill=255)

# 2. 模糊原图作为填充源
# 大半径确保完全消除水印细节
blurred = img.filter(ImageFilter.GaussianBlur(radius=30))

# 3. 合成：mask 区域用模糊版，其它用原图
# 注意：Image.composite 的 mask 白=用 image1, 黑=用 image2
result = Image.composite(blurred, img, mask)

# 4. 用周围主色再次优化水印中心区域
# 取水印区左侧的"干净"区像素作为参考色
img_arr = np.array(img)
ref_strip = img_arr[450:510, 600:640, :]  # 水印左侧的列
mean_color = ref_strip.reshape(-1, 3).mean(axis=0)
print(f'主参考色: RGB={mean_color.astype(int).tolist()}')

# 5. 二次蒙版：水印中心区域（避开边缘渐变带）纯填充主色
center_mask = Image.new('L', (W, H), 0)
cdraw = ImageDraw.Draw(center_mask)
cdraw.rectangle([(670, 470), (W, H)], fill=255)

solid_overlay = Image.new('RGB', (W, H),
                          (int(mean_color[0]), int(mean_color[1]), int(mean_color[2])))
result.paste(solid_overlay, (0, 0), center_mask)

# 6. 边缘再轻模糊一次
edge_mask = Image.new('L', (W, H), 0)
edraw = ImageDraw.Draw(edge_mask)
edraw.rectangle([(640, 455), (W, H)], fill=255)
final = result.filter(ImageFilter.GaussianBlur(radius=4))
# 只在边缘 mask 区域应用模糊
result = Image.composite(final, result, edge_mask)

result.save(OUT, 'PNG', optimize=True)
print(f'✅ 已保存: {OUT} ({result.size[0]}x{result.size[1]})')
