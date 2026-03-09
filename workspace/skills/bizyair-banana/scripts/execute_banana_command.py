#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BizyAir Banana 指令执行器 - 输出 INJECT_COMMAND 格式供框架自动触发插件

用法:
    python3 execute_banana_command.py "nb2画图 一只猫咪" "<session_id>" "<from_user_id>"
"""

import sys
import os

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def execute_command(command, session_id=None, from_user_id=None):
    """
    生成 INJECT_COMMAND 格式输出
    """
    
    # 检查命令有效性
    valid_prefixes = ['nb2画图', 'NB2画图', 'nbp画图', 'NBP画图']
    is_valid = any(command.startswith(prefix) for prefix in valid_prefixes)
    
    if not is_valid:
        return f"[ERROR] 无效的命令: {command}"
    
    # 生成 INJECT_COMMAND 格式
    # 格式: INJECT_COMMAND:<command>|session_id=<sid>|user_id=<uid>
    parts = []
    if session_id:
        parts.append(f"session_id={session_id}")
    if from_user_id:
        parts.append(f"user_id={from_user_id}")
        
    inject_cmd = f"INJECT_COMMAND:{command}"
    if parts:
        inject_cmd += "|" + "|".join(parts)
    
    return inject_cmd

def main():
    if len(sys.argv) < 2:
        print("[ERROR] 请提供命令参数", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else None
    from_user_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = execute_command(command, session_id, from_user_id)
    print(result)

if __name__ == "__main__":
    main()
