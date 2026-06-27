#!/usr/bin/env python3
"""
批量删除所有报告中的目标价格推测内容
"""
import os
import re

# 定义要处理的文件目录
report_dir = "/Users/chengdandan/Documents/terry-research"

# 定义要删除的目标价格模式
target_price_patterns = [
    r'<p><strong>目标价位：</strong>.*?</p>',
    r'<p><strong>目标价</strong>：.*?</p>',
    r'<p><strong>目标价格</strong>：.*?</p>',
    r'<p><strong>目标价：</strong>.*?</p>',
    r'<li><strong>目标价格</strong>：.*?</li>',
    r'<th>目标价</th>',
    r'<th>目标价（元/股）</th>',
]

# 查找所有HTML文件
html_files = [f for f in os.listdir(report_dir) if f.endswith('.html')]

print(f"找到 {len(html_files)} 个HTML文件")
print("开始处理...")

# 处理每个文件
for filename in html_files:
    filepath = os.path.join(report_dir, filename)
    
    # 读取文件内容
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    modifications = 0
    
    # 删除目标价格内容
    for pattern in target_price_patterns:
        # 使用正则表达式删除匹配的内容
        new_content = re.sub(pattern, '', content)
        if new_content != content:
            modifications += 1
        content = new_content
    
    # 如果有修改，写回文件
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {filename} - 删除了 {modifications} 处目标价格内容")
    else:
        print(f"⏭️  {filename} - 无目标价格内容")

print("\n处理完成！")
