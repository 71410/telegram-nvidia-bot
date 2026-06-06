"""Telegram AI 机器人 —— 基于 NVIDIA NIM API。"""

import sys
import os
import logging
import asyncio
import base64

# 修复 Windows GBK 控制台 emoji 编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatAction

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_MAX_MESSAGE_LENGTH,
    NVIDIA_API_KEY,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)
from conversation import (
    add_message,
    get_history,
    clear_history,
    get_history_length,
    get_model,
    set_model,
)
from nvidia_client import chat as nvidia_chat, chat_with_image

# 判断模型是否为视觉模型的辅助集合
VISION_MODEL_IDS = {
    "meta/llama-3.2-11b-vision-instruct",
    "meta/llama-3.2-90b-vision-instruct",
}

# 日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── 命令处理器 ────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """发送欢迎消息和使用说明。"""
    chat_id = update.effective_chat.id
    model_key = _get_model_key(get_model(chat_id))
    model_name = AVAILABLE_MODELS[model_key]["name"]
    welcome_text = (
        "👋 你好！我是 AI 聊天机器人 🤖\n\n"
        "⚡ 由 NVIDIA NIM 驱动\n"
        f"🧠 当前模型：{model_name}\n\n"
        "📋 命令列表：\n"
        "  /models — 查看所有可用模型\n"
        "  /model <名字> — 切换模型\n"
        "  /new — 开始新对话\n"
        "  /status — 查看当前状态\n\n"
        "💬 支持多轮对话，我会记住上下文。\n"
        "免费 API 每分钟约 40 次请求，请勿频繁发送。"
    )
    await update.message.reply_text(welcome_text)


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """清空当前对话，开始新会话。"""
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text("✅ 对话已清空，让我们重新开始吧！")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """显示当前对话状态。"""
    chat_id = update.effective_chat.id
    rounds = get_history_length(chat_id)
    model_key = _get_model_key(get_model(chat_id))
    model_name = AVAILABLE_MODELS[model_key]["name"]
    await update.message.reply_text(
        f"📊 当前状态\n"
        f"模型：{model_name}\n"
        f"对话轮数：{rounds}\n"
        f"发送 /models 查看所有可用模型\n"
        f"发送 /new 可开始新对话"
    )


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """列出所有可用模型。"""
    chat_id = update.effective_chat.id
    current_key = _get_model_key(get_model(chat_id))
    lines = ["🧠 可用模型：", ""]
    for key, info in AVAILABLE_MODELS.items():
        marker = " 👈 当前" if key == current_key else ""
        lines.append(f"  • `{key}` — {info['name']}")
        lines.append(f"    {info['desc']}{marker}")
    lines.append("")
    lines.append("发送 `/model <名字>` 切换模型，如：`/model llama3.1-8b`")
    await update.message.reply_text("\n".join(lines))


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """切换当前对话使用的模型。"""
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "请指定模型名字，如：`/model llama3.1-8b`\n"
            "发送 `/models` 查看所有可用模型"
        )
        return
    key = context.args[0].strip().lower()
    if key not in AVAILABLE_MODELS:
        keys_list = ", ".join(f"`{k}`" for k in AVAILABLE_MODELS)
        await update.message.reply_text(
            f"未知模型：`{key}`\n可用：{keys_list}\n"
            f"发送 `/models` 查看详情"
        )
        return
    set_model(chat_id, AVAILABLE_MODELS[key]["id"])
    await update.message.reply_text(
        f"✅ 已切换至 {AVAILABLE_MODELS[key]['name']}\n对话已清空。"
    )


# ─── 消息处理器 ────────────────────────────────────────────

def split_long_message(text: str, max_len: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """将超长文本按 Telegram 限制分段。"""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while len(text) > max_len:
        # 尝试在换行处断开
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户文字消息：调用 NVIDIA API 并回复。"""
    chat_id = update.effective_chat.id
    user_message = update.message.text.strip()

    if not user_message:
        return

    # 保存用户消息到对话历史
    add_message(chat_id, "user", user_message)

    # 发送 "正在输入..." 状态
    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        # 获取完整对话历史 + 当前模型，调用 NVIDIA API
        messages = get_history(chat_id)
        model = get_model(chat_id)
        reply = await nvidia_chat(messages, model=model)

        # 保存 AI 回复到对话历史
        add_message(chat_id, "assistant", reply)

        # 分段发送回复（Telegram 单条消息限制 4096 字符）
        for chunk in split_long_message(reply):
            await update.message.reply_text(chunk)

    except ValueError as e:
        # 配置错误
        await update.message.reply_text(str(e))
    except RuntimeError as e:
        # API 调用错误
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text("😵 发生未知错误，请稍后再试。")


# ─── 主入口 ────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的图片：下载图片，调用视觉模型分析。"""
    chat_id = update.effective_chat.id
    caption = update.message.caption or "请描述这张图片"

    # 选择视觉模型：当前模型如果是 vision 则直接用，否则用 11B vision
    current_model = get_model(chat_id)
    if current_model in VISION_MODEL_IDS:
        model = current_model
    else:
        model = "meta/llama-3.2-11b-vision-instruct"

    # 保存用户文本到对话历史
    add_message(chat_id, "user", f"[图片] {caption}")

    # 下载图片
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        photo = update.message.photo[-1]  # 最大尺寸
        tg_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await tg_file.download_as_bytearray()

        # 转 base64
        img_b64 = base64.b64encode(photo_bytes).decode("utf-8")

        # 调用视觉模型
        messages = get_history(chat_id)
        reply = await chat_with_image(messages, img_b64, model=model)

        # 保存回复
        add_message(chat_id, "assistant", reply)

        model_key = _get_model_key(model)
        model_name = AVAILABLE_MODELS[model_key]["name"]

        for chunk in split_long_message(reply):
            await update.message.reply_text(chunk)

    except ValueError as e:
        await update.message.reply_text(str(e))
    except RuntimeError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.error(f"Photo handling error: {e}")
        await update.message.reply_text(f"😵 图片处理失败：{e}")


# ─── 辅助函数 ──────────────────────────────────────────────

def _get_model_key(model_id: str) -> str:
    """根据模型的完整 ID 反查短键名。"""
    for key, info in AVAILABLE_MODELS.items():
        if info["id"] == model_id:
            return key
    return list(AVAILABLE_MODELS.keys())[0]  # 兜底


# ─── 主入口 ────────────────────────────────────────────────

def main() -> None:
    """启动 Bot。"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("123456789"):
        print("❌ 请先在 .env 文件中设置 TELEGRAM_BOT_TOKEN")
        return
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("nvapi-your"):
        print("⚠️  请先在 .env 文件中设置 NVIDIA_API_KEY")
        print("   机器人会启动，但 AI 功能需要 API Key")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # 注册命令
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("models", models_command))
    app.add_handler(CommandHandler("model", model_command))

    # 注册消息处理器（必须在命令处理器之后）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("🤖 Bot 启动中...")
    print("✅ Bot 已启动！按 Ctrl+C 停止。")
    app.run_polling()


if __name__ == "__main__":
    main()
