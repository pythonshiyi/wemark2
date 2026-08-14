import json
import time
import uuid
from pathlib import Path
from typing import List, Optional

from core.logger import get_logger

logger = get_logger("conversation")

CONVERSATIONS_DIR = Path.home() / ".wemark2" / "conversations"


def _ensure_dir():
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _conv_path(conv_id: str) -> Path:
    return CONVERSATIONS_DIR / f"{conv_id}.json"


def new_id() -> str:
    return f"conv_{uuid.uuid4().hex[:16]}"


def list_conversations() -> List[dict]:
    _ensure_dir()
    result = []
    for f in sorted(CONVERSATIONS_DIR.glob("conv_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            result.append({
                "id": data.get("id", f.stem),
                "title": data.get("title", "未命名对话"),
                "created_at": data.get("created_at", 0),
                "message_count": len(data.get("messages", [])),
            })
        except Exception as e:
            logger.error(f"Failed to load conversation {f}: {e}")
    return result


def load_conversation(conv_id: str) -> Optional[list]:
    path = _conv_path(conv_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except Exception as e:
        logger.error(f"Failed to load conversation {conv_id}: {e}")
        return None


def save_conversation(conv_id: str, messages: list, title: str = "") -> bool:
    _ensure_dir()
    if not title and messages:
        for m in messages:
            if m.get("role") == "user":
                title = m.get("content", "")[:40]
                break
    if not title:
        title = "未命名对话"
    path = _conv_path(conv_id)
    created_at = 0
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                created_at = json.load(f).get("created_at", 0)
        except Exception:
            pass
    if not created_at:
        created_at = int(time.time())
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "id": conv_id,
                "title": title,
                "created_at": created_at,
                "messages": messages,
            }, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save conversation {conv_id}: {e}")
        return False


def rename_conversation(conv_id: str, new_title: str) -> bool:
    path = _conv_path(conv_id)
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["title"] = new_title
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to rename conversation {conv_id}: {e}")
        return False


def delete_conversation(conv_id: str):
    path = _conv_path(conv_id)
    if path.exists():
        path.unlink()


def delete_all():
    _ensure_dir()
    for f in CONVERSATIONS_DIR.glob("conv_*.json"):
        f.unlink()
