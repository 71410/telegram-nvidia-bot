"""对话历史管理 —— 内存存储，每个 chat 独立。"""

from config import MAX_HISTORY_ROUNDS, DEFAULT_MODEL

# {chat_id: [{"role": "user"|"assistant"|"system", "content": "..."}, ...]}
_conversations: dict[int, list[dict]] = {}

# 每个 chat 的自定义 system prompt
_system_prompts: dict[int, str] = {}

# 每个 chat 当前使用的模型
_chat_models: dict[int, str] = {}


def get_model(chat_id: int) -> str:
    """获取该对话当前使用的模型。"""
    return _chat_models.get(chat_id, DEFAULT_MODEL)


def set_model(chat_id: int, model_id: str) -> None:
    """切换该对话的模型，自动清空历史。"""
    _chat_models[chat_id] = model_id
    clear_history(chat_id)


def get_system_prompt(chat_id: int) -> str:
    """获取该对话的 system prompt，不存在则返回默认值。"""
    return _system_prompts.get(chat_id, "你是一个有帮助的AI助手。")


def set_system_prompt(chat_id: int, prompt: str) -> None:
    """设置该对话的 system prompt，并清空历史。"""
    _system_prompts[chat_id] = prompt


def add_message(chat_id: int, role: str, content: str) -> None:
    """添加一条消息到对话历史中。"""
    if chat_id not in _conversations:
        _conversations[chat_id] = []
    _conversations[chat_id].append({"role": role, "content": content})

    # 只保留最近 N 轮（一轮 = user + assistant 各一条）
    max_len = MAX_HISTORY_ROUNDS * 2
    if len(_conversations[chat_id]) > max_len:
        _conversations[chat_id] = _conversations[chat_id][-max_len:]


def get_history(chat_id: int) -> list[dict]:
    """获取该对话的完整消息列表（含 system prompt）。"""
    messages = [{"role": "system", "content": get_system_prompt(chat_id)}]
    messages.extend(_conversations.get(chat_id, []))
    return messages


def clear_history(chat_id: int) -> None:
    """清空该对话的历史，但保留 system prompt。"""
    _conversations.pop(chat_id, None)


def get_history_length(chat_id: int) -> int:
    """返回当前对话的轮数（非 system 消息数 / 2）。"""
    return len(_conversations.get(chat_id, [])) // 2
