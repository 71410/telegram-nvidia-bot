"""加载配置：从 .env 文件读取环境变量。"""

import os
from dotenv import load_dotenv

load_dotenv()

# 必须的环境变量
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

# NVIDIA NIM 配置
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "qwen/qwen3.5-397b-a17b"

# 可用模型列表（经实测能在免费 API 上正常调用的模型）
AVAILABLE_MODELS = {
    "qwen3.5": {
        "id": "qwen/qwen3.5-397b-a17b",
        "name": "Qwen 3.5 397B",
        "desc": "阿里最新旗舰，中文最强",
    },
    "llama3.3-70b": {
        "id": "meta/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B",
        "desc": "Meta 最新 70B，综合强",
    },
    "llama3.1-70b": {
        "id": "meta/llama-3.1-70b-instruct",
        "name": "Llama 3.1 70B",
        "desc": "经典大杯，稳定可靠",
    },
    "llama3.1-8b": {
        "id": "meta/llama-3.1-8b-instruct",
        "name": "Llama 3.1 8B",
        "desc": "轻量快速，响应迅速",
    },
    "llama3.2-3b": {
        "id": "meta/llama-3.2-3b-instruct",
        "name": "Llama 3.2 3B",
        "desc": "极速小巧",
    },
    "llama3.2-vision-11b": {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Llama 3.2 11B Vision",
        "desc": "视觉多模态，看图识物 🖼️",
    },
    "llama3.2-vision-90b": {
        "id": "meta/llama-3.2-90b-vision-instruct",
        "name": "Llama 3.2 90B Vision",
        "desc": "旗舰视觉模型，图片分析 🖼️",
    },
}

# 机器人配置
MAX_HISTORY_ROUNDS = 20          # 每个对话最多保留的轮数
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
