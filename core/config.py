import copy
import json
import threading
from pathlib import Path
from typing import Any, Dict

from core.logger import get_logger

logger = get_logger("config")

DEFAULT_CONFIG: Dict[str, Any] = {
    "window": {
        "width": 1400, "height": 900, "x": 100, "y": 100,
        "ai_dock_width": 300, "preview_dock_width": 450,
        "ai_dock_area": "left",
    },
    "editor": {
        "font_size": 16,
        "font_family": "Consolas",
        "line_spacing": 1.8,
        "paragraph_spacing": "normal",
        "tab_width": 4,
        "word_wrap": True,
        "show_line_numbers": True,
        "auto_pair": True,
        "snippet_expand": True,
        "auto_save": True,
        "auto_save_interval": 60,
    },
    "typewriter": {
        "focus_mode": False,
        "typewriter_scroll": False,
        "focus_opacity": 160,
        "scroll_position": 0.35,
    },
    "template": {"default": "default", "last_used": "default", "custom_css": ""},
    "preview": {"auto_refresh": True, "refresh_delay": 250},
    "ai": {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "temperature": 1.3,
        "top_p": 1.0,
        "reasoning_effort": "high",
        "thinking_enabled": True,
        "max_tokens": 4096,
        "max_conversation_turns": 20,
    },
    "language": "zh-CN",
    "theme": "light",
    "recent_files": [],
    "outline_visible": False,
    "image_host": {
        "uploader": "none",
        "custom_url": "",
        "custom_field": "file",
        "auto_upload_on_insert": False,
        "auto_upload_on_export": True,
    },
}


def _config_path() -> Path:
    d = Path.home() / ".wemark2"
    d.mkdir(parents=True, exist_ok=True)
    return d / "config.json"


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v) if isinstance(v, dict) else v
    return result


class ConfigManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._config = self._load()

    def _load(self) -> Dict[str, Any]:
        path = _config_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    user = json.load(f)
                return _deep_merge(DEFAULT_CONFIG, user)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return copy.deepcopy(DEFAULT_CONFIG)

    def save(self) -> bool:
        try:
            with self._lock:
                data = json.dumps(self._config, ensure_ascii=False, indent=2)
            with open(_config_path(), "w", encoding="utf-8") as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def _save_locked(self) -> bool:
        try:
            data = json.dumps(self._config, ensure_ascii=False, indent=2)
            with open(_config_path(), "w", encoding="utf-8") as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, key: str, default=None):
        with self._lock:
            keys = key.split(".")
            val = self._config
            for k in keys:
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    return default
            if isinstance(val, dict):
                return copy.deepcopy(val)
            return val

    def set(self, key: str, value) -> bool:
        with self._lock:
            keys = key.split(".")
            ref = self._config
            for k in keys[:-1]:
                if k not in ref:
                    ref[k] = {}
                ref = ref[k]
            ref[keys[-1]] = value
            return self._save_locked()

    def update(self, updates: Dict[str, Any]) -> bool:
        with self._lock:
            self._config = _deep_merge(self._config, updates)
            return self._save_locked()

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._config)


config_manager = ConfigManager()
