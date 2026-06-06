"""对话历史管理 —— SQLite 持久化存储，每个 chat 独立。"""

import sqlite3
import os
import threading
from config import MAX_HISTORY_ROUNDS, DEFAULT_MODEL

# 数据库路径
# Railway: 持久卷挂载在 /data，优先使用
# 本地: 项目目录下的 conversations.db
if os.path.isdir("/data"):
    DB_PATH = os.path.join("/data", "conversations.db")
else:
    DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "conversations.db"))

# 线程本地存储，每个线程一个连接（避免 SQLite 多线程问题）
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接。"""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _init_tables(_local.conn)
    return _local.conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """初始化数据库表。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            seq INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_config (
            chat_id INTEGER PRIMARY KEY,
            model_id TEXT,
            system_prompt TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_chat_seq
        ON messages(chat_id, seq)
    """)
    conn.commit()


# ─── 公开 API（与原来接口完全兼容）──────────────────────────

def get_model(chat_id: int) -> str:
    """获取该对话当前使用的模型。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT model_id FROM chat_config WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row["model_id"] if row else DEFAULT_MODEL


def set_model(chat_id: int, model_id: str) -> None:
    """切换该对话的模型，自动清空历史。"""
    conn = _get_conn()
    conn.execute("""
        INSERT INTO chat_config (chat_id, model_id)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET model_id = excluded.model_id
    """, (chat_id, model_id))
    clear_history(chat_id)


def get_system_prompt(chat_id: int) -> str:
    """获取该对话的 system prompt，不存在则返回默认值。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT system_prompt FROM chat_config WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row["system_prompt"] if row and row["system_prompt"] else "你是一个有帮助的AI助手。"


def set_system_prompt(chat_id: int, prompt: str) -> None:
    """设置该对话的 system prompt。"""
    conn = _get_conn()
    conn.execute("""
        INSERT INTO chat_config (chat_id, system_prompt)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET system_prompt = excluded.system_prompt
    """, (chat_id, prompt))


def add_message(chat_id: int, role: str, content: str) -> None:
    """添加一条消息到对话历史中。"""
    conn = _get_conn()
    # 获取下一个 seq
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), -1) + 1 AS nxt FROM messages WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    seq = row["nxt"]

    conn.execute(
        "INSERT INTO messages (chat_id, role, content, seq) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, seq),
    )

    # 只保留最近 N 轮（一轮 = user + assistant 各一条）
    max_msgs = MAX_HISTORY_ROUNDS * 2
    conn.execute("""
        DELETE FROM messages WHERE chat_id = ? AND seq <= (
            SELECT COALESCE(MAX(seq), 0) - ? FROM messages WHERE chat_id = ?
        )
    """, (chat_id, max_msgs, chat_id))
    conn.commit()


def get_history(chat_id: int) -> list[dict]:
    """获取该对话的完整消息列表（含 system prompt）。"""
    conn = _get_conn()
    messages = [{"role": "system", "content": get_system_prompt(chat_id)}]
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY seq",
        (chat_id,),
    ).fetchall()
    for r in rows:
        messages.append({"role": r["role"], "content": r["content"]})
    return messages


def clear_history(chat_id: int) -> None:
    """清空该对话的历史，但保留 system prompt 和模型设置。"""
    conn = _get_conn()
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()


def get_history_length(chat_id: int) -> int:
    """返回当前对话的轮数（非 system 消息数 / 2）。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM messages WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row["cnt"] // 2 if row else 0
