import json
import requests
import re
from typing import Optional, Tuple

class LLMClient:
    def __init__(self, api_key: str = None, config: dict = None):
        self.api_key = api_key
        self.config = config or {}
        # 使用SiliconFlow API，与SiliconSpeech插件一致
        self.api_url = self.config.get("llm_api_base_url", "https://api.siliconflow.cn/v1") + "/chat/completions"

    @staticmethod
    def _clean_answer_text(text: str) -> str:
        """清理回答文本，保留中文、数字、英文字母和常用标点"""
        try:
            # 移除多余空格，但保留单个空格
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 处理编码问题，移除无效字符
            text = ''.join(char for char in text if ord(char) < 65536)
            
            # 移除不常用的特殊字符，但保留字母、数字、中文和常用标点
            text = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9，。、；：？！,.;:?! ]', '', text)
            
            return text
            
        except Exception as e:
            print(f"[LLMClient] Error in _clean_answer_text: {str(e)}")
            return text  # 出错时返回原文本而不是空字符串

    def generate_answer(self, user_input: str, max_length: int = 50) -> Tuple[Optional[str], Optional[str]]:
        """生成简短回答，返回(原始文本, 清理后的文本)"""
        try:
            # 检查API密钥
            if not self.api_key:
                print("[LLMClient] API key not provided")
                return None, None
            
            # 从配置中读取系统提示词，使用默认值
            default_prompt = """你是一个专业、友好的AI助手。请根据用户的问题提供准确、有帮助的回答。
要求：
1. 回答要准确专业
2. 语言要简洁易懂
3. 态度要友好
4. 适当使用标点符号提高可读性
5. 回答不超过50字

请直接输出答案内容，确保回答准确、易懂。"""
            system_prompt = self.config.get("system_prompt", default_prompt)
            # 处理转义的换行符
            system_prompt = system_prompt.replace("\\n", "\n")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]

            # 构建API请求
            payload = {
                "model": self.config.get("llm_model", "deepseek-ai/DeepSeek-V3"),
                "messages": messages,
                "stream": False,
                "max_tokens": 150,
                "stop": None,
                "temperature": 0.7,
                "top_p": 0.7,
                "top_k": 50,
                "frequency_penalty": 0.5,
                "n": 1,
                "response_format": {
                    "type": "text"
                }
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 发送请求
            print(f"[LLMClient] Sending request to LLM API, model: {payload['model']}")
            response = requests.post(self.api_url, headers=headers, json=payload)
            print(f"[LLMClient] API response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[LLMClient] API error: {response.text[:500]}")  # 截断错误信息
                return None, None
                
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                original_text = result["choices"][0]["message"]["content"]
                print(f"[LLMClient] LLM generated text: {original_text[:100]}...")  # 截断显示
                
                # 清理文本
                clean_text = self._clean_answer_text(original_text)
                return original_text, clean_text
            print("[LLMClient] No choices in API response")
            return None, None

        except Exception as e:
            print(f"[LLMClient] Error generating answer: {str(e)}")
            return None, None


if __name__ == "__main__":
    import os
    
    # 尝试从配置文件加载API密钥
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    api_key = ""
    config = {}
    
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            api_key = config.get("llm_api_key", "")
            print(f"[Test] Loaded API key from config.json")
        else:
            print(f"[Test] Config file not found at {config_path}")
            print("[Test] Please provide an API key to test:")
            api_key = input().strip()
    except Exception as e:
        print(f"[Test] Error loading config: {e}")
        print("[Test] Please provide an API key to test:")
        api_key = input().strip()
    
    # 创建客户端并测试
    client = LLMClient(api_key=api_key, config=config)
    test_input = "什么是人工智能"
    result = client.generate_answer(test_input)
    print(f"Input: {test_input}")
    print(f"Generated answer: {result[0] if result else None}")
    print(f"Clean answer: {result[1] if result else None}")
