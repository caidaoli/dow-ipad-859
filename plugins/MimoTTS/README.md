# MimoTTS 插件

MimoTTS 是一个基于小米 MiMo TTS API 的文字转语音插件，适用于 ChatGPT-On-WeChat 项目。

## 功能特性

### 基础功能
1. **mm朗读** - 直接将文本转换为语音
2. **mm回答** - 使用AI生成回答并转换为语音
3. **mm唱歌** - AI演唱歌词内容

### 高级功能
- **自动语音回复** - 自动将BOT的文本回复转换为语音
- **风格控制** - 支持通过 `<style>` 标签控制语音风格（情绪、方言、角色扮演等）
- **多种音色** - 支持默认音色、中文女声、英文女声
- **自动清理** - 自动清理过期的音频缓存文件

## 文件结构

```
plugins/MimoTTS/
├── MimoTTS.py      # 主插件文件
├── llm_client.py   # LLM客户端（用于AI回答功能）
├── config.json     # 配置文件
└── README.md       # 说明文档
```

## 安装配置

### 1. 配置文件说明

编辑 `config.json` 文件，填写以下配置项：

```json
{
    "mimo_api_key": "your_mimo_api_key_here",
    "llm_api_key": "your_siliconflow_api_key_here",
    "voice": "mimo_default",
    "model": "mimo-v2-tts",
    "llm_model": "deepseek-ai/DeepSeek-V3",
    "llm_api_base_url": "https://api.siliconflow.cn/v1",
    "mimo_api_url": "https://api.xiaomimimo.com/v1/chat/completions",
    "file_retention_days": 1,
    "voice_cache_dir": "tmp/wx859_mimo_voice_cache",
    "trigger_words": {
        "read": "mm朗读",
        "answer": "mm回答",
        "sing": "mm唱歌",
        "list_models": "mm音色列表",
        "switch_model": "mm切换音色"
    },
    "audio_format": "mp3",
    "system_prompt": "你是一个专业、友好的AI助手。请根据用户的问题提供准确、有帮助的回答。\\n要求：\\n1. 回答要准确专业\\n2. 语言要简洁易懂\\n3. 态度要友好\\n4. 适当使用标点符号提高可读性\\n5. 回答不超过50字\\n\\n请直接输出答案内容，确保回答准确、易懂。"
}
```

### 2. 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `mimo_api_key` | MiMo TTS API密钥（必需） | - |
| `llm_api_key` | SiliconFlow LLM API密钥（用于AI回答功能） | - |
| `voice` | 语音音色 | `mimo_default` |
| `model` | TTS模型 | `mimo-v2-tts` |
| `llm_model` | LLM模型 | `deepseek-ai/DeepSeek-V3` |
| `llm_api_base_url` | LLM API基础URL | `https://api.siliconflow.cn/v1` |
| `mimo_api_url` | MiMo TTS API地址 | `https://api.xiaomimimo.com/v1/chat/completions` |
| `file_retention_days` | 音频文件保留天数 | `1` |
| `voice_cache_dir` | 音频缓存目录 | `tmp/wx859_mimo_voice_cache` |
| `trigger_words.read` | 朗读触发词 | `mm朗读` |
| `trigger_words.answer` | 回答触发词 | `mm回答` |
| `trigger_words.sing` | 唱歌触发词 | `mm唱歌` |
| `trigger_words.list_models` | 音色列表触发词 | `mm音色列表` |
| `trigger_words.switch_model` | 切换音色触发词 | `mm切换音色` |
| `trigger_words.enable_auto` | 开启自动语音回复触发词 | `mm开启语音回复` |
| `trigger_words.disable_auto` | 关闭自动语音回复触发词 | `mm关闭语音回复` |
| `audio_format` | 音频格式 | `mp3` |
| `auto_reply_enabled` | 自动语音回复开关 | `false` |
| `auto_reply_max_length` | 自动回复最大文本长度 | `200` |
| `system_prompt` | AI回答的系统提示词 | 默认提示词 |

### 3. 获取API密钥

- **MiMo API Key**: 访问 [MiMo开发者平台](https://api.xiaomimimo.com) 注册并获取
- **SiliconFlow API Key**: 访问 [SiliconFlow](https://siliconflow.cn) 注册并获取（用于AI回答功能）

## 使用方法

### 基础命令

**1. 直接朗读文本**
```
mm朗读 你好，世界！
```

**2. AI智能回答**
```
mm回答 什么是人工智能？
```

**3. AI唱歌功能**
```
mm唱歌 天青色等烟雨而我在等你
```

**4. 自动语音回复开关**
```
mm开启语音回复  # 开启自动语音回复
mm关闭语音回复  # 关闭自动语音回复
```
开启后，BOT的所有文本回复将自动转换为语音发送（限200字以内）

### 风格控制（高级功能）

MiMo TTS 支持通过 `<style>` 标签控制语音风格：

**格式：**
```
mm朗读 <style>风格</style>要朗读的内容
```

**示例：**

1. **情绪控制**
```
mm朗读 <style>开心</style>今天天气真好，心情棒极了！
```

2. **方言支持**
```
mm朗读 <style>东北话</style>哎呀妈呀，这天儿也忒冷了吧！
mm朗读 <style>粤语</style>呢个真係好正啊！
mm朗读 <style>四川话</style>巴适得板！
```

3. **角色扮演**
```
mm朗读 <style>孙悟空</style>俺老孙来也！
mm朗读 <style>林黛玉</style>花谢花飞飞满天，红消香断有谁怜？
```

4. **风格变化**
```
mm朗读 <style>悄悄话</style>我跟你说个秘密...
mm朗读 <style>夹子音</style>真的吗？好厉害哦！
```

### 可用音色

| 音色名称 | voice参数 | 说明 |
|----------|-----------|------|
| MiMo-默认 | `mimo_default` | 默认音色 |
| MiMo-中文女声 | `default_zh` | 中文女声 |
| MiMo-英文女声 | `default_en` | 英文女声 |

## 自定义AI回答风格

您可以修改 `config.json` 中的 `system_prompt` 配置来自定义AI回答的风格：

```json
{
    "system_prompt": "你是一个幽默风趣的AI助手。请用轻松愉快的语气回答问题，可以适当使用emoji表情。\\n要求：\\n1. 回答要幽默风趣\\n2. 语言要简洁易懂\\n3. 适当使用emoji\\n4. 回答不超过50字"
}
```

**注意**：配置文件中需要使用 `\\n` 表示换行符。

## 触发词自定义

您可以修改 `config.json` 中的 `trigger_words` 配置来自定义触发词：

```json
{
    "trigger_words": {
        "read": "朗读",
        "answer": "回答",
        "sing": "唱歌",
        "list_models": "音色列表",
        "switch_model": "切换音色"
    }
}
```

修改后：
- `朗读 你好` - 直接朗读
- `回答 什么是AI` - AI回答后朗读
- `唱歌 歌词内容` - AI唱歌
- `音色列表` - 查看可用音色
- `切换音色 中文女声` - 切换音色

## 注意事项

1. **API密钥安全**: 请妥善保管您的API密钥，不要泄露给他人
2. **文件清理**: 插件会自动清理超过保留天数的音频文件，默认为1天
3. **文本长度**: 建议单次转换文本不超过500字，过长文本可能影响合成效果
4. **网络要求**: 插件需要访问MiMo和SiliconFlow的API，请确保服务器网络通畅

## 故障排查

### 常见问题

**1. 提示"请先在config.json中配置MiMo API密钥"**
- 检查 `config.json` 中的 `mimo_api_key` 是否已填写

**2. 提示"请先在config.json中配置LLM API密钥"**
- 检查 `config.json` 中的 `llm_api_key` 是否已填写（仅在使用 `mm回答` 功能时需要）

**3. 生成语音失败**
- 检查API密钥是否正确
- 检查网络连接是否正常
- 查看日志文件了解详细错误信息

**4. 语音播放异常**
- 检查音频格式设置是否正确（支持 `wav` 和 `mp3`）
- 检查缓存目录是否有写入权限

## 更新日志

### v1.0 (2025-03-19)
- 初始版本发布
- 实现 `mm朗读` 和 `mm回答` 基础功能
- 支持风格控制和音色选择
- 自动清理过期音频文件

## 技术支持

如有问题，请查看：
1. 项目日志文件（`run.log`）
2. MiMo TTS API文档
3. SiliconFlow API文档
