import json
from pathlib import Path

from core.config import config_manager

_LOCALES: dict = {}
_TRANSLATIONS: dict = {}


def _locales_path() -> Path:
    return Path(__file__).parent.parent / "assets" / "locales"


def load_language(lang: str = None):
    global _TRANSLATIONS
    if lang is None:
        lang = config_manager.get("language", "zh-CN")

    base_path = _locales_path()

    _TRANSLATIONS = {}
    default_file = base_path / "zh-CN.json"
    try:
        if default_file.exists():
            with open(default_file, "r", encoding="utf-8") as f:
                _TRANSLATIONS = json.load(f)
    except Exception:
        _TRANSLATIONS = {}

    lang_file = base_path / f"{lang}.json"
    try:
        if lang != "zh-CN" and lang_file.exists():
            with open(lang_file, "r", encoding="utf-8") as f:
                _TRANSLATIONS.update(json.load(f))
    except Exception:
        pass


def tr(key: str, **kwargs) -> str:
    if not _TRANSLATIONS:
        load_language()
    text = _TRANSLATIONS.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def set_language(lang: str):
    config_manager.set("language", lang)
    load_language(lang)
