import json
import logging
from pathlib import Path

ADMIN_CHAT_FILE = Path(__file__).with_name("admin_chat.json")


def load_admin_chat_id() -> int:
    try:
        if not ADMIN_CHAT_FILE.exists():
            return 0
        raw = ADMIN_CHAT_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return 0

        data = json.loads(raw)

        # поддерживаем 2 формата:
        # 1) {"admin_chat_id": 123}
        # 2) просто число: 123
        if isinstance(data, dict):
            return int(data.get("admin_chat_id", 0) or 0)
        return int(data or 0)

    except Exception:
        logging.exception("Failed to load admin_chat_id")
        return 0


def save_admin_chat_id(chat_id: int) -> None:
    try:
        tmp = ADMIN_CHAT_FILE.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"admin_chat_id": int(chat_id)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(ADMIN_CHAT_FILE)
    except Exception:
        logging.exception("Failed to save admin_chat_id")
