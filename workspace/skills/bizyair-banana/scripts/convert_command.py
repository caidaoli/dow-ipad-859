#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BizyAir Banana 指令转换器
将用户的自然语言转换为 BizyAir_Banana 插件的标准指令格式

用法:
    python3 convert_command.py "使用 nbp 画一只在太空漂浮的猫咪 --ar 16:9"
    
输出:
    COMMAND:nbp画图 一只在太空漂浮的猫咪 --ar 16:9
"""

import sys
import re

def convert_to_banana_command(user_input):
    """
    将用户输入转换为 BizyAir_Banana 插件指令
    """
    user_input = user_input.strip()
    
    # 定义模型标识
    nbp_keywords = [r'nbp', r'nano\s*banana\s*pro', r'nano\s*pro', r'nb\s*pro', r'nxp']
    nb2_keywords = [r'nb2', r'nano\s*banana\s*2', r'nano\s*2', r'nb\s*2', r'nx2']
    
    # 基础画图关键词
    draw_keywords = [r'画图', r'生成图片', r'生图', r'画一个', r'生成图像', r'作画']
    
    # 默认命令前缀
    prefix = "nb2画图"
    
    # 检查是否是 NBP
    for pattern in nbp_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            prefix = "nbp画图"
            break
            
    # 如果明确提到了 NB2，即使之前匹配了 NBP（虽然不太可能），也尊重 NB2
    # 这里逻辑是：如果用户提供了具体的模型名，我们就用那个。
    # 如果用户没提供，但提到了 "banana"，默认用 nb2。
    
    # 提取提示词的具体逻辑
    prompt = user_input
    
    # 移除模型关键词
    for pattern in nbp_keywords + nb2_keywords:
        prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE)
        
    # 移除画图关键词
    for pattern in draw_keywords:
        prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE)
        
    # 移除 "使用", "用", "帮忙", "帮我" 等语气词
    prompt = re.sub(r'使用|用|帮忙|帮我|给我|生成|请|模型|插件', '', prompt).strip()
    
    # 处理冒号
    prompt = re.sub(r'^[：:\s]+', '', prompt).strip()
    
    # 处理参数提取 (如果用户已经在输入中带了 --ar, --1k 等，保留它们)
    # 这里的策略是清洗掉模型/动作词后，剩下的就是 prompt + params
    
    # 特殊情况：如果用户没带参数，但用了自然语言描述比例，如 "横屏"
    ratio_map = {
        r'横屏|横版|宽屏': '--ar 16:9',
        r'竖屏|竖版|手机': '--ar 9:16',
        r'正方形|方图': '--ar 1:1',
        r'3比4|3:4': '--ar 3:4',
        r'4比3|4:3': '--ar 4:3'
    }
    
    params = []
    for pattern, param in ratio_map.items():
        if re.search(pattern, prompt):
            if '--ar' not in prompt and '--ratio' not in prompt:
                params.append(param)
            prompt = re.sub(pattern, '', prompt).strip()
            
    res_map = {
        r'4k|高清|超清': '--4k',
        r'2k': '--2k',
        r'1k': '--1k',
        r'自动分辨率': '--auto'
    }
    for pattern, param in res_map.items():
        if re.search(pattern, prompt, re.IGNORECASE):
            if not re.search(r'--(1k|2k|4k|auto)', prompt, re.IGNORECASE):
                params.append(param)
            prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE).strip()

    # 再次清理 prompt 中可能残留的标点和空格
    prompt = re.sub(r'^[，,\s]+|[，,\s]+$', '', prompt)
    
    final_command = f"{prefix} {prompt}"
    if params:
        final_command += " " + " ".join(params)
        
    return final_command.strip()

def main():
    if len(sys.argv) < 2:
        print("[ERROR] 请提供用户输入", file=sys.stderr)
        sys.exit(1)
    
    user_input = sys.argv[1]
    result = convert_to_banana_command(user_input)
    
    if result:
        print(f"COMMAND:{result}")
    else:
        print("[ERROR] 无法识别用户意图", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
