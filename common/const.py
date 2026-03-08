# bot_type
ZHIPU_AI = "zhipuai"
OPEN_AI = "openAI"
CHATGPT = "chatGPT"
BAIDU = "baidu"
XUNFEI = "xunfei"
CHATGPTONAZURE = "chatGPTOnAzure"
LINKAI = "linkai"
CLAUDEAI = "claude" # 使用cookie的历史模型
CLAUDEAPI= "claudeAPI" # 通过Claude api调用模型
QWEN = "qwen"  # 旧版通义模型
QWEN_DASHSCOPE = "dashscope"   # 通义新版sdk和api key
GEMINI = "gemini"
MOONSHOT = "moonshot"
MiniMax = "minimax"
COZE = "coze"
QIANFAN = "qianfan"  # 百度千帆平台
DIFY = "dify"
SILICONFLOW = "siliconflow"  # 确保这个值与 config.json 中的 bot_type 一致
DEEPSEEK = "deepseek"  # 添加DeepSeek类型
MODELSCOPE = "modelscope"  # 添加ModelScope类型
DOUBAO = "doubao"  # 字节跳动豆包
LONGCAT = "longcat"  # LongCat API

# openAI models
GPT_OSS_120B = "gpt-oss-120b"
GPT_51 = "gpt-5.1"
GPT_52 = "gpt-5.2"
GPT_54 = "gpt-5.4"
GEMINI_3_FLASH = "gemini-3-flash-preview" 
GEMINI_31_FLASH_LITE = "gemini-3.1-flash-lite-preview"
GROK_41_FAST = "grok-4-1-fast-reasoning"
GROK_41 = "grok-4.1"
GROK_42 = "grok-4.20-beta"
LINKAI_35 = "linkai-3.5"

WHISPER_1 = "whisper-1"
TTS_1 = "tts-1"
TTS_1_HD = "tts-1-hd"

# longcat models
LONGCAT_THINKING_2601 = "LongCat-Flash-Thinking-2601"
LONGCAT_THINKING = "LongCat-Flash-Thinking"
LONGCAT_FLASH_CHAT = "LongCat-Flash-Chat"
LONGCAT_FLASH_LITE = "LongCat-Flash-Lite"

# dashscope models
QWEN_35_PLUS = "qwen3.5-plus"
QWEN_35_PLUS_2602 = "qwen3.5-plus-2026-02-15"
QWEN_35_FLASH = "qwen3.5-flash"
QWEN_35_FLASH_2602 = "qwen3.5-flash-2026-02-23"
QWEN_35_397B = "qwen3.5-397b-a17b"
QWEN_35_27B = "qwen3.5-27b"
QWEN_DS = "deepseek-v3.2"
QWEN_GLM = "glm-5"
QWEN_K25 = "kimi-k2.5"
QWEN_M25 = "MiniMax-M2.5"

# zhipuai models
GLM_47_FLASH = "glm-4.7-flash"
GLM_45_FLASH = "glm-4.5-flash"
GLM_46V_FLASH = "glm-4.6v-flash"
GLM_4V_FLASH = "glm-4v-flash"
GLM_41V_FLASH = "glm-4.1v-thinking-flash"

# siliconflow models
SF_DEEPSEEK_V32 = "deepseek-ai/DeepSeek-V3.2"
SF_MiniMax_M21 = "Pro/MiniMaxAI/MiniMax-M2.1"
SF_KIMI_K2 = "moonshotai/Kimi-K2-Instruct-0905"
SF_GLM_46 = "zai-org/GLM-4.6"
SF_QWEN3 = "Qwen/Qwen3-235B-A22B-Instruct-2507"
SF_STEP35 = "stepfun-ai/Step-3.5-Flash"
SF_LING_FLASH_2 = "inclusionAI/Ling-flash-2.0"

# modelscope models
QWEN35_397B = "Qwen/Qwen3.5-397B-A17B"
KIMI_K25 = "moonshotai/Kimi-K2.5"
MiniMax_M25 = "MiniMax/MiniMax-M2.5"
DS_V32 = "deepseek-ai/DeepSeek-V3.2"
GLM_5 = "ZhipuAI/GLM-5"

# deepseek models
DEEPSEEK_CHAT = "deepseek-chat"
DEEPSEEK_REASONER = "deepseek-reasoner"

# gemini models
GEMINI_15_FLASH = "gemini-1.5-flash"
GEMINI_15_PRO = "gemini-1.5-pro"
GEMINI_20_FLASH_EXP = "gemini-2.0-flash-exp"

# dify models
DIFY_CHATFLOW = "chatflow"
DIFY_CHATBOT = "chatbot"
DIFY_AGENT = "agent"
DIFY_WORKFLOW = "workflow"

MODEL_LIST = [OPEN_AI, GPT_OSS_120B, GPT_51, GPT_52, GPT_54, GEMINI_3_FLASH, GEMINI_31_FLASH_LITE, GROK_41_FAST, GROK_41, GROK_42, LINKAI_35, 
              LONGCAT_THINKING_2601, LONGCAT_THINKING, LONGCAT_FLASH_CHAT, LONGCAT_FLASH_LITE, 
              QWEN_DASHSCOPE, QWEN_35_PLUS, QWEN_35_PLUS_2602, QWEN_35_FLASH, QWEN_35_FLASH_2602, QWEN_35_397B, QWEN_35_27B, QWEN_DS, QWEN_GLM, QWEN_K25, QWEN_M25, 
              ZHIPU_AI, GLM_47_FLASH, GLM_45_FLASH, GLM_46V_FLASH, GLM_4V_FLASH, GLM_41V_FLASH,
              SILICONFLOW, SF_DEEPSEEK_V32, SF_MiniMax_M21, SF_KIMI_K2, SF_GLM_46, SF_QWEN3, SF_STEP35, SF_LING_FLASH_2, 
              MODELSCOPE, QWEN35_397B, KIMI_K25, MiniMax_M25, DS_V32, GLM_5,
              COZE, QIANFAN, 
              DIFY, DIFY_CHATFLOW, DIFY_CHATBOT, DIFY_AGENT, DIFY_WORKFLOW,
              GEMINI, GEMINI_15_FLASH, GEMINI_15_PRO, GEMINI_20_FLASH_EXP,
              DEEPSEEK, DEEPSEEK_CHAT, DEEPSEEK_REASONER]
              

# channel
FEISHU = "feishu"
DINGTALK = "dingtalk"
