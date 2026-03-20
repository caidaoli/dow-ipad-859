# encoding:utf-8
import os
from plugins import *
from plugins import EventAction
import plugins
import json
import requests
import time
import random
import threading
import datetime
import base64
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.tmp_dir import TmpDir
from .llm_client import LLMClient

# 尝试导入音频转换库
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("[MimoTTS] pydub not installed, audio format conversion may not work properly")

@plugins.register(
    name="MimoTTS",
    desire_priority=100,
    desc="输入'mm朗读 文本内容'或'mm回答 问题'即可将文本转换为语音",
    version="1.0",
    author="JY",
    namecn="MiMo文字转语音"
)
class MimoTTS(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        # 注册自动语音回复事件处理器（参考md_plugin.py）
        self.handlers[Event.ON_DECORATE_REPLY] = self.on_decorate_reply
        
        # 加载配置
        self.config = self.load_config()
        
        # 初始化LLMClient，传入API密钥和完整配置
        # MimoTTS使用SiliconFlow的LLM API
        self.llm_client = LLMClient(api_key=self.config.get("llm_api_key"), config=self.config)
        
        # 启动文件清理线程
        self.start_cleanup_thread()
        
        # 打印自动回复状态
        auto_reply_status = "开启" if self.config.get("auto_reply_enabled", False) else "关闭"
        logger.info(f"[MimoTTS] Plugin initialized. Auto-reply: {auto_reply_status}")

    def load_config(self):
        """
        加载配置文件
        :return: 配置字典
        """
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info("[MimoTTS] Config loaded successfully.")
                return config
            else:
                logger.warning(f"[MimoTTS] Config file not found at {config_path}, using default values.")
                # 返回默认配置
                return {
                    "mimo_api_key": "",
                    "llm_api_key": "",
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
                    "switch_model": "mm切换音色",
                    "enable_auto": "mm开启语音回复",
                    "disable_auto": "mm关闭语音回复"
                },
                "audio_format": "wav",
                "auto_reply_enabled": False,
                "auto_reply_max_length": 200,
                "voice_models": [
                        {"name": "MiMo默认", "voice": "mimo_default"},
                        {"name": "中文女声", "voice": "default_zh"},
                        {"name": "英文女声", "voice": "default_en"}
                    ]
                }
        except Exception as e:
            logger.error(f"[MimoTTS] Error loading config: {e}")
            # 返回默认配置
            return {
                "mimo_api_key": "",
                "llm_api_key": "",
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
                    "switch_model": "mm切换音色",
                    "enable_auto": "mm开启语音回复",
                    "disable_auto": "mm关闭语音回复"
                },
                "audio_format": "wav",
                "auto_reply_enabled": False,
                "auto_reply_max_length": 200,
                "voice_models": [
                    {"name": "MiMo默认", "voice": "mimo_default"},
                    {"name": "中文女声", "voice": "default_zh"},
                    {"name": "英文女声", "voice": "default_en"}
                ]
            }

    def on_decorate_reply(self, e_context: EventContext):
        """
        自动语音回复功能 - 参考md_plugin.py的实现
        当auto_reply_enabled为true时，自动将上游BOT的文本回复转换为语音
        """
        # 检查自动回复是否开启
        if not self.config.get("auto_reply_enabled", False):
            return
        
        reply = e_context['reply']
        if not reply:
            return
        
        # 只处理文本类型的回复
        if reply.type != ReplyType.TEXT:
            return
        
        content = reply.content
        if not content or not isinstance(content, str):
            return
        
        # 检查是否是插件自己的回复（避免循环）
        # 如果内容以特定标记开头，说明是插件自己生成的，跳过
        if content.startswith('🎵') or content.startswith('<style>'):
            return
        
        # 检查文本长度是否超过设定值
        max_length = self.config.get("auto_reply_max_length", 200)
        if len(content) > max_length:
            logger.info(f"[MimoTTS] Auto-reply skipped: text too long ({len(content)} > {max_length})")
            return
        
        # 检查是否包含表情符号等不适合TTS的内容
        if content.strip() in ['🤖', '💬', '🌌'] or len(content.strip()) < 2:
            return
        
        logger.info(f"[MimoTTS] Auto-converting text to speech: {content[:50]}...")
        
        try:
            # 检查API密钥
            if not self.config.get("mimo_api_key"):
                logger.warning("[MimoTTS] Auto-reply skipped: no API key")
                return
            
            # 清理文本
            clean_text = self._clean_text_for_tts(content)
            if not clean_text or len(clean_text) < 2:
                logger.warning("[MimoTTS] Auto-reply skipped: empty text after cleaning")
                return
            
            # 检查是否有自动语音回复的风格设置
            auto_style = self.config.get("auto_reply_style")
            if auto_style:
                # 将风格标签添加到文本开头
                clean_text = f"<{auto_style}>{clean_text}"
                logger.info(f"[MimoTTS] Auto-reply with style <{auto_style}>: {clean_text[:50]}...")
            
            # 生成语音
            audio_path = self.generate_audio(clean_text)
            
            if audio_path:
                # 将回复类型改为语音
                reply.type = ReplyType.VOICE
                reply.content = audio_path
                e_context.action = EventAction.BREAK_PASS
                logger.info(f"[MimoTTS] Auto-reply voice generated: {audio_path}")
            else:
                logger.error("[MimoTTS] Auto-reply failed: voice generation failed")
        except Exception as e:
            logger.error(f"[MimoTTS] Auto-reply error: {e}")
            # 出错时不阻断，让原文本发送
    
    def _clean_text_for_tts(self, text: str) -> str:
        """清理文本以便TTS转换"""
        import re
        # 移除URL
        text = re.sub(r'https?://\S+', '', text)
        # 移除Markdown格式符号
        text = re.sub(r'[*#`【】\[\]()（）]', '', text)
        # 移除多余的空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _save_config(self):
        """保存配置到文件"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            logger.info("[MimoTTS] Config saved successfully.")
        except Exception as e:
            logger.error(f"[MimoTTS] Error saving config: {e}")

    def _truncate_log(self, data, max_length=500):
        """
        截断日志数据，避免输出过长内容（如base64音频数据）
        :param data: 要记录的数据
        :param max_length: 最大长度
        :return: 截断后的字符串
        """
        try:
            text = str(data)
            if len(text) > max_length:
                return text[:max_length] + f"... [截断，原始长度: {len(text)}]"
            return text
        except:
            return "[无法序列化的数据]"

    def start_cleanup_thread(self):
        """
        启动文件清理线程
        """
        cleanup_thread = threading.Thread(target=self.cleanup_files_periodically, daemon=True)
        cleanup_thread.start()
        logger.info("[MimoTTS] File cleanup thread started.")

    def cleanup_files_periodically(self):
        """
        定期清理旧文件
        """
        while True:
            try:
                # 清理文件
                self.cleanup_old_files()
                # 每天运行一次
                time.sleep(86400)  # 24小时 = 86400秒
            except Exception as e:
                logger.error(f"[MimoTTS] Error in cleanup thread: {e}")
                # 出错后等待一小时再试
                time.sleep(3600)

    def cleanup_old_files(self):
        """
        清理旧的音频文件
        """
        try:
            # 使用专门的音频缓存目录
            voice_cache_dir = self.config.get("voice_cache_dir", "tmp/wx859_mimo_voice_cache")
            
            # 检查目录是否存在
            if not os.path.exists(voice_cache_dir):
                logger.info(f"[MimoTTS] Voice cache directory does not exist: {voice_cache_dir}")
                return
            
            # 获取当前时间
            current_time = datetime.datetime.now()
            
            # 获取文件保留天数
            retention_days = self.config.get("file_retention_days", 1)
            
            # 遍历音频缓存目录中的文件
            files_removed = 0
            for filename in os.listdir(voice_cache_dir):
                if filename.startswith("mimo_speech_"):
                    file_path = os.path.join(voice_cache_dir, filename)
                    
                    # 获取文件修改时间
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # 计算文件年龄（天）
                    file_age_days = (current_time - file_mtime).days
                    
                    # 如果文件年龄超过保留天数，则删除
                    if file_age_days >= retention_days:
                        try:
                            os.remove(file_path)
                            files_removed += 1
                            logger.info(f"[MimoTTS] Removed old audio file: {filename}")
                        except Exception as e:
                            logger.error(f"[MimoTTS] Error removing file {file_path}: {e}")
            
            logger.info(f"[MimoTTS] Cleaned up {files_removed} old audio files from {voice_cache_dir}")
        except Exception as e:
            logger.error(f"[MimoTTS] Error cleaning up old files: {e}")

    def _convert_style_tags(self, text):
        """
        将简化的风格标签 <风格名> 转换为 MiMo API 标准格式 <style>风格名</style>
        例如: <开心> -> <style>开心</style>
              <东北话> -> <style>东北话</style>
        :param text: 原始文本
        :return: 转换后的文本
        """
        import re
        # 匹配 <风格名> 格式的标签，但排除已有的 <style>...</style> 标签
        # 匹配规则: <开头，接着是非>的字符（风格名），然后是>
        pattern = r'<(?!style>)([^<>]+)>'
        
        def replace_tag(match):
            style_name = match.group(1).strip()
            # 忽略空标签或可能的HTML标签
            if not style_name or ' ' in style_name or style_name.lower() in ['br', 'hr', 'img', 'div', 'span']:
                return match.group(0)
            return f'<style>{style_name}</style>'
        
        converted_text = re.sub(pattern, replace_tag, text)
        
        if converted_text != text:
            logger.info(f"[MimoTTS] Converted style tags: {text[:50]}... -> {converted_text[:50]}...")
        
        return converted_text

    def generate_audio(self, text):
        """
        调用MiMo TTS API生成语音
        :param text: 要转换为语音的文本
        :return: 音频文件保存路径或None（如果生成失败）
        """
        try:
            # 转换简化的风格标签为标准格式
            text = self._convert_style_tags(text)
            
            # 获取API配置
            api_url = self.config.get("mimo_api_url", "https://api.xiaomimimo.com/v1/chat/completions")
            api_key = self.config.get("mimo_api_key", "")
            
            # 构建请求头
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            
            # 构建请求体
            # 根据MiMo API文档，语音合成的目标文本需放在role为assistant的消息中
            # user角色的消息为可选参数，用于调整语音合成的语气与风格
            payload = {
                "model": self.config.get("model", "mimo-v2-tts"),
                "messages": [
                    {
                        "role": "user",
                        "content": "请朗读以下内容"
                    },
                    {
                        "role": "assistant",
                        "content": text
                    }
                ],
                "audio": {
                    "format": self.config.get("audio_format", "wav"),
                    "voice": self.config.get("voice", "mimo_default")
                }
            }
            
            # 发送请求
            logger.info(f"[MimoTTS] Sending request to {api_url}")
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"[MimoTTS] API request failed with status {response.status_code}: {response.text}")
                return None
            
            # 解析响应，获取音频数据
            result = response.json()
            
            # 从 choices[0].message.audio.data 获取音频数据 (MiMo API格式)
            audio_base64 = None
            try:
                audio_base64 = result["choices"][0]["message"]["audio"]["data"]
            except (KeyError, IndexError):
                pass
            
            # 如果上述路径没有，尝试从其他可能的路径获取
            if not audio_base64:
                try:
                    audio_base64 = result["audio"]["data"]
                except KeyError:
                    pass
            
            if not audio_base64:
                # 截断日志，避免base64音频数据刷屏 - 清理choices中的音频数据
                result_log = result.copy()
                if "choices" in result_log and len(result_log["choices"]) > 0:
                    if "message" in result_log["choices"][0] and "audio" in result_log["choices"][0]["message"]:
                        result_log["choices"][0]["message"]["audio"] = "[音频数据已省略]"
                logger.error(f"[MimoTTS] No audio data in response: {self._truncate_log(result_log)}")
                return None
            
            # 解码Base64编码的音频数据
            audio_bytes = base64.b64decode(audio_base64)
            
            # 检测音频格式（通过文件头）
            # MP3文件头: 0xFF 0xFB 或 0xFF 0xF3 (MPEG-1/2 Layer 3)
            # WAV文件头: "RIFF"
            is_mp3 = audio_bytes[:2] == b'\xff\xfb' or audio_bytes[:2] == b'\xff\xf3' or audio_bytes[:2] == b'\xff\xfa'
            is_wav = audio_bytes[:4] == b'RIFF'
            
            actual_format = "mp3" if is_mp3 else ("wav" if is_wav else "unknown")
            logger.info(f"[MimoTTS] Detected audio format: {actual_format}")
            
            # 使用专门的音频缓存目录
            voice_cache_dir = self.config.get("voice_cache_dir", "tmp/wx859_mimo_voice_cache")
            
            # 确保目录存在
            os.makedirs(voice_cache_dir, exist_ok=True)
            
            # 生成唯一的文件名（微信要求mp3格式）
            timestamp = int(time.time())
            random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6))
            audio_name = f"mimo_speech_{timestamp}_{random_str}.mp3"
            audio_path = os.path.join(voice_cache_dir, audio_name)
            
            # 如果已经是mp3格式，直接保存
            if is_mp3:
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"[MimoTTS] Audio saved directly as mp3: {audio_path}")
                return audio_path
            
            # 如果是wav格式，需要转换
            if is_wav:
                temp_wav_path = audio_path.replace('.mp3', '_temp.wav')
                with open(temp_wav_path, "wb") as f:
                    f.write(audio_bytes)
                
                # 验证文件大小
                if os.path.getsize(temp_wav_path) == 0:
                    logger.error("[MimoTTS] Generated audio file size is 0")
                    os.remove(temp_wav_path)
                    return None
                
                # 转换为mp3格式
                if PYDUB_AVAILABLE:
                    try:
                        audio = AudioSegment.from_wav(temp_wav_path)
                        audio.export(audio_path, format="mp3")
                        os.remove(temp_wav_path)
                        logger.info(f"[MimoTTS] Audio converted from wav to mp3: {audio_path}")
                    except Exception as convert_error:
                        logger.error(f"[MimoTTS] Audio conversion failed: {convert_error}")
                        os.rename(temp_wav_path, audio_path)
                        logger.warning(f"[MimoTTS] Using original format with mp3 extension: {audio_path}")
                else:
                    os.rename(temp_wav_path, audio_path)
                    logger.warning(f"[MimoTTS] pydub not available, renamed to mp3: {audio_path}")
                return audio_path
            
            # 未知格式，直接保存为mp3尝试
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            logger.warning(f"[MimoTTS] Unknown audio format, saved as mp3: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"[MimoTTS] Error generating audio: {e}")
            return None

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return
            
        content = e_context["context"].content
        reply = Reply()
        reply.type = ReplyType.TEXT

        # 从配置中获取触发词
        trigger_read = self.config.get("trigger_words", {}).get("read", "mm朗读")
        trigger_answer = self.config.get("trigger_words", {}).get("answer", "mm回答")
        trigger_sing = self.config.get("trigger_words", {}).get("sing", "mm唱歌")
        trigger_list_models = self.config.get("trigger_words", {}).get("list_models", "mm音色列表")
        trigger_switch_model = self.config.get("trigger_words", {}).get("switch_model", "mm切换音色")
        trigger_enable_auto = self.config.get("trigger_words", {}).get("enable_auto", "mm开启语音回复")
        trigger_disable_auto = self.config.get("trigger_words", {}).get("disable_auto", "mm关闭语音回复")

        # 处理自动语音回复开关命令
        content_stripped = content.strip()
        if content_stripped.startswith(trigger_enable_auto):
            self.config["auto_reply_enabled"] = True
            
            # 检查是否指定了风格标签
            style_match = None
            remaining = content_stripped[len(trigger_enable_auto):].strip()
            if remaining:
                import re
                # 匹配 <风格名> 格式
                style_match = re.match(r'^<([^<>]+)>$', remaining)
                if style_match:
                    style_name = style_match.group(1).strip()
                    self.config["auto_reply_style"] = style_name
                    style_msg = f"\n语音风格: <{style_name}>"
                else:
                    # 如果格式不对，清除之前的风格设置
                    if "auto_reply_style" in self.config:
                        del self.config["auto_reply_style"]
                    style_msg = ""
            else:
                # 没有指定风格，清除之前的风格设置
                if "auto_reply_style" in self.config:
                    del self.config["auto_reply_style"]
                style_msg = ""
            
            self._save_config()
            reply.content = f"✅ 已开启自动语音回复功能{style_msg}\n现在BOT的文本回复将自动转换为语音发送\n（文字长度不超过200字）"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        
        elif content.strip() == trigger_disable_auto:
            self.config["auto_reply_enabled"] = False
            # 关闭时同时清除风格设置
            if "auto_reply_style" in self.config:
                del self.config["auto_reply_style"]
            self._save_config()
            reply.content = "❌ 已关闭自动语音回复功能\nBOT将恢复正常文本回复"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        
        # 处理触发词命令
        if content.startswith(f"{trigger_list_models}"):
            # 获取当前使用的voice
            current_voice = self.config.get("voice", "")
            # 获取语音模型列表
            voice_models = self.config.get("voice_models", [])
            
            # 构建返回消息
            reply_text = "MimoTTS可用语音模型：\n"
            for i, model in enumerate(voice_models, 1):
                # 如果是当前使用的模型，添加👉标记
                prefix = "👉" if model["voice"] == current_voice else " "
                reply_text += f"{prefix}{i}. {model['name']}\n"
            
            reply.content = reply_text.strip()
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        
        elif content.startswith(f"{trigger_switch_model} "):
            # 获取目标模型名称或序号
            target_input = content[len(trigger_switch_model) + 1:].strip()
            
            # 获取语音模型列表
            voice_models = self.config.get("voice_models", [])
            
            # 查找目标模型
            target_model = None
            
            # 首先尝试按序号查找（如果输入是数字）
            if target_input.isdigit():
                try:
                    index = int(target_input) - 1  # 转换为0基索引
                    if 0 <= index < len(voice_models):
                        target_model = voice_models[index]
                        logger.info(f"[MimoTTS] Switching to model by index: {index + 1} -> {target_model['name']}")
                except (ValueError, IndexError):
                    pass
            
            # 如果不是数字或按序号没找到，则按名称查找
            if target_model is None:
                for model in voice_models:
                    if model["name"] == target_input:
                        target_model = model
                        logger.info(f"[MimoTTS] Switching to model by name: {target_input}")
                        break
            
            if target_model:
                # 更新voice
                self.config["voice"] = target_model["voice"]
                # 保存配置
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=4)
                
                reply.content = f"已切换到语音模型: {target_model['name']}"
            else:
                # 提供更详细的错误信息
                if target_input.isdigit():
                    reply.content = f"序号 {target_input} 超出范围，请使用 1-{len(voice_models)} 之间的数字"
                else:
                    available_names = ", ".join([model["name"] for model in voice_models])
                    reply.content = f"未找到语音模型: {target_input}\n可用音色: {available_names}\n或使用序号: 1-{len(voice_models)}"
            
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        
        elif content.startswith(f"{trigger_sing} "):
            # 获取歌词内容
            text = content[len(trigger_sing) + 1:].strip()
            
            if not text:
                reply.content = f"请在'{trigger_sing}'后输入要演唱的歌词"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            
            # 添加唱歌风格标签
            text = f"<style>唱歌</style>{text}"
            
            # 调用朗读功能（实际会调用generate_audio，自动添加唱歌标签）
            display_text = clean_text = text
            
            try:
                # 检查API密钥是否已配置
                if not self.config.get("mimo_api_key"):
                    reply.content = "请先在config.json中配置MiMo API密钥 (mimo_api_key)"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                
                logger.info(f"[MimoTTS] Singing text: {display_text}")
                
                # 调用MiMo API生成语音（唱歌）
                audio_path = self.generate_audio(clean_text)
                
                if audio_path:
                    # 先发送文字消息
                    text_reply = Reply()
                    text_reply.type = ReplyType.TEXT
                    text_reply.content = "🎵 " + display_text
                    e_context["reply"] = text_reply
                    e_context.action = EventAction.CONTINUE

                    # 然后发送语音消息
                    voice_reply = Reply()
                    voice_reply.type = ReplyType.VOICE
                    voice_reply.content = audio_path
                    e_context["reply"] = voice_reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                else:
                    reply.content = "生成歌曲失败，请检查配置并稍后重试"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
            except Exception as e:
                logger.error(f"[MimoTTS] Error in sing: {e}")
                reply.content = "唱歌失败，请稍后重试"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
        
        elif content.startswith(f"{trigger_read} ") or content.startswith(f"{trigger_answer} "):
            # 获取命令类型和文本
            is_read = content.startswith(f"{trigger_read} ")
            is_answer = content.startswith(f"{trigger_answer} ")
            
            # 根据不同命令类型获取文本内容
            if is_read:
                text = content[len(trigger_read) + 1:].strip()
            else:  # is_answer
                text = content[len(trigger_answer) + 1:].strip()
            
            if not text:
                reply.content = f"请在'{trigger_read}'或'{trigger_answer}'后输入要转换的文本内容"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

            try:
                # 检查API密钥是否已配置
                if not self.config.get("mimo_api_key"):
                    reply.content = "请先在config.json中配置MiMo API密钥 (mimo_api_key)"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                
                # 提取风格标签（用于mm回答功能）
                style_tag = None
                if is_answer:
                    import re
                    # 匹配开头的风格标签，如 <开心>、<悲伤>、<东北话> 等
                    style_match = re.match(r'^<([^<>]+)>(.+)', text, re.DOTALL)
                    if style_match:
                        style_tag = style_match.group(1).strip()
                        text_without_style = style_match.group(2).strip()
                        logger.info(f"[MimoTTS] Extracted style tag: <{style_tag}>, question: {text_without_style}")
                    else:
                        text_without_style = text
                else:
                    text_without_style = text
                
                # 根据不同命令类型处理文本
                if is_answer:
                    # 使用LLM生成回答（传入去掉风格标签的问题）
                    display_text, clean_text = self.llm_client.generate_answer(text_without_style, max_length=50)
                    # 将风格标签添加到回答前面
                    if style_tag and display_text:
                        display_text = f"<{style_tag}>{display_text}"
                        clean_text = f"<{style_tag}>{clean_text}"
                else:  # is_read
                    # 直接使用输入文本
                    display_text = clean_text = text

                if not display_text or not clean_text:
                    reply.content = "生成文本失败，请稍后重试"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return

                logger.info(f"[MimoTTS] Generated text: {display_text}")
                logger.info(f"[MimoTTS] Clean text for TTS: {clean_text}")
                
                if not clean_text or clean_text.strip() in ['🤖', '💬', '🌌']:  # 检查清理后的文本是否为空或只有表情
                    reply.content = "生成的文本格式不正确，请重试"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                    
                # 调用MiMo API生成语音
                audio_path = self.generate_audio(clean_text)
                
                if audio_path:
                    # 先发送文字消息，使用原始文本（带表情）
                    text_reply = Reply()
                    text_reply.type = ReplyType.TEXT
                    text_reply.content = display_text
                    e_context["reply"] = text_reply
                    e_context.action = EventAction.CONTINUE  # 继续处理

                    # 然后发送语音消息
                    voice_reply = Reply()
                    voice_reply.type = ReplyType.VOICE
                    voice_reply.content = audio_path
                    e_context["reply"] = voice_reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                else:
                    reply.content = "生成语音失败，请检查配置并稍后重试"
            except Exception as e:
                logger.error(f"[MimoTTS] Error: {e}")
                reply.content = "处理失败，请稍后重试"
        else:
            return

        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def get_help_text(self, **kwargs):
        # 从配置中获取触发词
        trigger_read = self.config.get("trigger_words", {}).get("read", "mm朗读")
        trigger_answer = self.config.get("trigger_words", {}).get("answer", "mm回答")
        trigger_sing = self.config.get("trigger_words", {}).get("sing", "mm唱歌")
        trigger_list_models = self.config.get("trigger_words", {}).get("list_models", "mm音色列表")
        trigger_switch_model = self.config.get("trigger_words", {}).get("switch_model", "mm切换音色")
        trigger_enable_auto = self.config.get("trigger_words", {}).get("enable_auto", "mm开启语音回复")
        trigger_disable_auto = self.config.get("trigger_words", {}).get("disable_auto", "mm关闭语音回复")
        
        # 获取当前使用的音色
        current_voice = self.config.get("voice", "mimo_default")
        voice_models = self.config.get("voice_models", [])
        
        # 获取自动回复状态
        auto_reply_status = "✅ 开启" if self.config.get("auto_reply_enabled", False) else "❌ 关闭"
        
        # 获取自动回复风格
        auto_reply_style = self.config.get("auto_reply_style")
        style_info = f" (风格: <{auto_reply_style}>)" if auto_reply_style else ""
        
        # 找到当前音色的名称
        current_voice_name = "未知"
        for model in voice_models:
            if model["voice"] == current_voice:
                current_voice_name = model["name"]
                break
        
        # 构建音色列表
        voice_list = ""
        for model in voice_models:
            prefix = "👉" if model["voice"] == current_voice else " "
            voice_list += f"{prefix}{model['name']}\n"
        
        return f"""🎤 **MimoTTS 语音转换插件**

**当前音色：** {current_voice_name}
**自动语音回复：** {auto_reply_status}{style_info}

---

### 📝 **基础功能**

**1. 直接朗读文本**
发送「{trigger_read} 文本内容」即可将文本转换为语音
例如：{trigger_read} 你好，欢迎使用MiMo语音转换功能

**2. AI智能回答**
发送「{trigger_answer} 问题内容」即可获得AI回答并转换为语音
例如：{trigger_answer} 什么是人工智能

**带风格的智能回答：**
发送「{trigger_answer} <风格>问题内容」可获得带风格的AI回答
例如：{trigger_answer} <开心>今天天气怎么样
例如：{trigger_answer} <东北话>推荐几个好玩的地方

**3. AI唱歌功能**
发送「{trigger_sing} 歌词内容」即可让AI用歌声演唱
例如：{trigger_sing} 天青色等烟雨而我在等你，月色被打捞起晕开了结局

---

### 🤖 **自动语音回复功能**

**当前状态：** {auto_reply_status}{style_info}

**开启自动语音回复：**
发送「{trigger_enable_auto}」
开启后，BOT的所有文本回复将自动转换为语音发送（限200字以内）

**带风格的自动语音回复：**
发送「{trigger_enable_auto} <风格名>」
例如：{trigger_enable_auto} <林黛玉>
例如：{trigger_enable_auto} <东北话>
开启后，所有语音回复都将使用该风格

**关闭自动语音回复：**
发送「{trigger_disable_auto}」
关闭后，BOT恢复正常文本回复

---

### 🎨 **音色管理功能**

**3. 查看可用音色**
发送「{trigger_list_models}」查看所有可用的语音音色

**4. 切换音色**
发送「{trigger_switch_model} 音色名称」或「{trigger_switch_model} 序号」切换到指定音色
例如：{trigger_switch_model} 中文女声 或 {trigger_switch_model} 2

---

### 🎵 **可用音色列表**
{voice_list}

---

### 💡 **高级功能 - 风格控制**

您可以在文本开头添加风格标签来控制语音风格：

**简化格式（推荐）：** `<风格名>要朗读的内容`

**标准格式：** `<style>风格名</style>要朗读的内容`

**支持的风格：**
- 语速控制：变快/变慢
- 情绪变化：开心/悲伤/生气
- 角色扮演：孙悟空/林黛玉
- 风格变化：悄悄话/夹子音/台湾腔
- 方言：东北话/四川话/河南话/粤语

**示例：**
- `<开心>明天就是周五了，真开心！`
- `<东北话>哎呀妈呀，这天儿也忒冷了吧！`
- `<粤语>呢个真係好正啊！`
- `<孙悟空>俺老孙来也！`

---

### ⚙️ **配置说明**
使用前请确保在 config.json 中正确配置：
- MiMo API密钥 (mimo_api_key)
- LLM API密钥 (llm_api_key)
- 语音音色 (voice)
- 音频格式 (audio_format)
- 音频缓存目录 (voice_cache_dir)
"""
