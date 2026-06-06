"""NVIDIA NIM API 封装 —— OpenAI 兼容接口。"""

import logging
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

_client = OpenAI(
    base_url=NVIDIA_BASE_URL,
    api_key=NVIDIA_API_KEY,
    timeout=60.0,  # 大模型推理可能较慢
)


async def chat(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """发送消息到 NVIDIA NIM API，返回模型回复文本。

    Args:
        messages: 包含 system/user/assistant 角色的消息列表。
        model: 模型名称。

    Returns:
        模型的回复文本。

    Raises:
        ValueError: 未配置 API Key。
        RuntimeError: API 调用失败。
    """
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("nvapi-your"):
        raise ValueError(
            "❌ NVIDIA API Key 未配置。请在 .env 文件中设置 NVIDIA_API_KEY=你的key"
        )

    try:
        # OpenAI SDK 的 create 是阻塞调用，这里用 asyncio.to_thread 不阻塞事件循环
        import asyncio
        response = await asyncio.to_thread(
            _client.chat.completions.create,
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    except ValueError:
        raise  # 配置错误直接抛出

    except RateLimitError:
        raise RuntimeError(
            "⏳ NVIDIA API 速率限制（约40次/分钟），请稍后再试。"
        )

    except APITimeoutError:
        raise RuntimeError(
            "⏰ NVIDIA API 请求超时，请稍后再试。"
        )

    except APIConnectionError:
        raise RuntimeError(
            "🔌 无法连接到 NVIDIA API，请检查网络。"
        )

    except APIError as e:
        logger.error(f"NVIDIA API error: {e}")
        raise RuntimeError(
            f"🤖 NVIDIA API 返回错误，请稍后再试。"
        )


async def chat_with_image(
    messages: list[dict],
    image_base64: str,
    mime_type: str = "image/jpeg",
    model: str = DEFAULT_MODEL,
) -> str:
    """发送带图片的消息到 NVIDIA NIM，返回模型回复。

    将最后一条 user 消息转为多模态格式，附加图片。

    Args:
        messages: 对话历史（含 system/user/assistant 角色）。
        image_base64: 图片的 base64 编码（不含 data: URI 前缀）。
        mime_type: 图片 MIME 类型。
        model: 模型名称。

    Returns:
        模型的回复文本。
    """
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("nvapi-your"):
        raise ValueError(
            "❌ NVIDIA API Key 未配置。请在 .env 文件中设置 NVIDIA_API_KEY=你的key"
        )

    # 构造多模态消息列表：除最后一条 user 消息外保持不变，
    # 最后一条 user 消息改为 text + image 的 content 数组格式
    multimodal_messages = list(messages)
    last_user_msg = multimodal_messages[-1]
    text_content = last_user_msg["content"] if isinstance(last_user_msg["content"], str) else ""

    multimodal_messages[-1] = {
        "role": "user",
        "content": [
            {"type": "text", "text": text_content},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
            },
        ],
    }

    try:
        import asyncio
        response = await asyncio.to_thread(
            _client.chat.completions.create,
            model=model,
            messages=multimodal_messages,
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    except ValueError:
        raise
    except RateLimitError:
        raise RuntimeError("⏳ NVIDIA API 速率限制（约40次/分钟），请稍后再试。")
    except APITimeoutError:
        raise RuntimeError("⏰ NVIDIA API 请求超时，请稍后再试。")
    except APIConnectionError:
        raise RuntimeError("🔌 无法连接到 NVIDIA API，请检查网络。")
    except APIError as e:
        logger.error(f"NVIDIA API error: {e}")
        raise RuntimeError(f"🤖 NVIDIA API 返回错误，请稍后再试。")
