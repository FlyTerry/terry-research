#!/usr/bin/env python3
"""提升原图清晰度：2x 超分 + 锐化 + 对比度增强"""
from PIL import Image, ImageFilter, ImageEnhance

SRC = '/Users/chengdandan/.workbuddy/clipboard-images/clipboard-2026-07-25T03-26-12-923Z-74ae0126.png'
OUT = '/Users/chengdandan/Documents/terry-research/assets/jiayou-corridor-drc-zambia-ports.png'

img = Image.open(SRC).convert('RGB')
W, H = img.size
print(f'原图: {W}x{H}')

# 1. 2x 放大（LANCZOS 保真）
img_2x = img.resize((W*2, H*2), Image.LANCZOS)

# 2. 锐化
img_2x = img_2x.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))

# 3. 对比度微增强
enhancer = ImageEnhance.Contrast(img_2x)
img_2x = enhancer.enhance(1.15)

# 4. 保存
img_2x.save(OUT, 'PNG', optimize=True)
print(f'输出: {img_2x.size[0]}x{img_2x.size[1]}')

# 验证
import os
sz = os.path.getsize(OUT)
print(f'文件: {sz/1024:.0f} KB')
