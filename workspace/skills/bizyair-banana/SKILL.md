---
name: bizyair-banana
description: "图像生成工具。当用户要求使用 nbp/nano banana pro 或 nb2/nano banana 2 模型进行画图、生成图片时触发。支持指定分辨率和比例参数。"
metadata:
  requires:
    bins: []
    env: []
  emoji: "🍌"
---

# BizyAir Banana 指令转换器

将用户关于 BizyAir Nano Banana 1/2/Pro 图像生成的自然语言请求，转换为 BizyAir_Banana 插件能够识别的标准指令格式。

## ⚠️ 强制要求：必须使用 bash 工具执行脚本

**你不应该直接回复用户！你必须使用 bash 工具执行以下两个脚本：**

1. **先执行**: `python3 "{baseDir}/scripts/convert_command.py" "用户完整消息"`
2. **再执行**: `python3 "{baseDir}/scripts/execute_banana_command.py" "<转换后的命令>" "{session_id}" "{from_user_id}"`
3. **最后**: 将第二个脚本的输出**原样返回**（必须以 INJECT_COMMAND: 开头）

**禁止直接生成回复！禁止解释！禁止添加表情和装饰文字！**

## 支持的功能

| 用户模型意图 | 转换后的指令 | 示例 |
|---------|------------|------|
| Nano Banana 2 (默认) | `nb2画图 <提示词> [参数]` | nb2画图 一只在太空漂浮的可爱猫咪 --ar 16:9 |
| Nano Banana Pro | `nbp画图 <提示词> [参数]` | nbp画图 赛博朋克城市夜景 --4k |

### 支持参数
- **画幅比例**: `--ar 1:1`, `--ar 16:9`, `--ar 9:16`, `--ar 3:4` 等
- **分辨率**: `--1k`, `--2k`, `--4k`, `--auto`

## 指令转换规则

### 1. 意图识别
- **NB2 模型**: 用户提到 `nb2`, `nano banana 2`, `nano 2`, `nx2` 等。
- **NBP 模型**: 用户提到 `nbp`, `nano banana pro`, `nano pro`, `nxp` 等。
- **默认**: 如果用户仅说 "用 banana 画图" 或类似且未指定模型，默认使用 `nb2画图`。

### 2. 转换示例
```
用户: 使用 nano banana pro 模型帮我生成图片：一只在太空漂浮的可爱猫咪 --ar 16:9
→ 转换: nbp画图 一只在太空漂浮的可爱猫咪 --ar 16:9

用户: 用 nb2 画一个可爱的狗，分辨率要 4k
→ 转换: nb2画图 可爱的狗 --4k
```

## 执行流程

### ✅ 自动触发插件
Agent 框架支持 `INJECT_COMMAND` 机制，bizyair-banana-skill 可以**自动触发 BizyAir_Banana 插件**执行。

**执行流程**：
1. 用户发送画图请求。
2. Skill 转换命令并输出 `INJECT_COMMAND:nb2画图 ...`
3. AgentBridge 检测到 `INJECT_COMMAND` 并调用 `BizyAir_Banana` 插件。
4. 插件处理并返回图片。

### ⚠️ 关键要求：直接返回 INJECT_COMMAND 格式
当你看到 bash 工具输出 `INJECT_COMMAND:` 开头的结果时，**必须直接原样返回这个结果，不要添加任何其他内容**。

✅ **正确做法**：
```
INJECT_COMMAND:nb2画图 一只猫咪|session_id=xxx|user_id=yyy
```

## 快速测试
```bash
# 测试模型识别
python3 "{baseDir}/scripts/convert_command.py" "使用 nbp 画一只猫"
# 预期输出：COMMAND:nbp画图 一只猫
```
