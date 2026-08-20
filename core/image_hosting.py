import json
import os
import re
import threading
import urllib.parse
from pathlib import Path

import httpx

from core.config import config_manager
from core.logger import get_logger

logger = get_logger("image_hosting")

CACHE_FILE = Path.home() / ".wemark2" / "image_host_cache.json"

_cache_loaded = False
_cache: dict = {}
_lock = threading.Lock()

_LOCAL_SRC_RE = re.compile(r'src="([^"]*)"')
_SKIP_SRC_PREFIXES = ("http://", "https://", "data:", "file://")


def _load_cache():
    global _cache_loaded
    if _cache_loaded:
        return
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _cache.update(json.load(f))
    except Exception as e:
        logger.error(f"Failed to load image host cache: {e}")
    finally:
        _cache_loaded = True


def _save_cache():
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save image host cache: {e}")


def get_uploader() -> str:
    return config_manager.get("image_host.uploader", "none")


def is_enabled() -> bool:
    return get_uploader() in ("catbox", "custom")


def clear_cache():
    global _cache_loaded
    with _lock:
        _cache.clear()
        _cache_loaded = True
        try:
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
        except Exception:
            pass


def upload_image(path: str, timeout: float = 30.0) -> str:
    uploader = get_uploader()
    if uploader == "catbox":
        return _upload_catbox(path, timeout)
    if uploader == "custom":
        return _upload_custom(path, timeout)
    raise RuntimeError("未配置图床，请在设置中选择图床服务")


def _upload_catbox(path: str, timeout: float) -> str:
    with open(path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(path), f, "application/octet-stream")}
        data = {"reqtype": "fileupload"}
        resp = httpx.post(
            "https://catbox.moe/user/api.php",
            files=files,
            data=data,
            timeout=timeout,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith(("http://", "https://")):
        raise RuntimeError(f"catbox 返回异常: {url[:100]}")
    return url


def _extract_url(text: str, data: dict) -> str:
    for key in ("url", "data", "link", "src", "file", "image", "path"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith(("http://", "https://")):
            return v
        if isinstance(v, dict):
            for k2 in ("url", "link", "src", "path", "file"):
                v2 = v.get(k2)
                if isinstance(v2, str) and v2.startswith(("http://", "https://")):
                    return v2
    if text.startswith(("http://", "https://")):
        return text
    return ""


def _upload_custom(path: str, timeout: float) -> str:
    url = config_manager.get("image_host.custom_url", "")
    field = config_manager.get("image_host.custom_field", "file")
    if not url:
        raise RuntimeError("未配置自定义图床上传地址")
    with open(path, "rb") as f:
        files = {field or "file": (os.path.basename(path), f, "application/octet-stream")}
        resp = httpx.post(url, files=files, timeout=timeout)
    resp.raise_for_status()
    text = resp.text.strip()
    data = None
    try:
        data = resp.json()
    except Exception:
        pass
    result = _extract_url(text, data or {})
    if not result:
        raise RuntimeError(f"自定义图床返回异常: {text[:100]}")
    return result


def upload_with_cache(path: str, timeout: float = 30.0) -> str:
    path = os.path.abspath(path)
    _load_cache()
    with _lock:
        cached = _cache.get(path)
    if cached:
        return cached
    url = upload_image(path, timeout)
    with _lock:
        _cache[path] = url
        _save_cache()
    return url


def replace_local_images(html: str, base_path: str = None, timeout: float = 30.0) -> tuple:
    uploaded = 0
    failed = 0

    def _repl(m: re.Match) -> str:
        nonlocal uploaded, failed
        src = m.group(1)
        if not src or src.startswith(_SKIP_SRC_PREFIXES):
            return m.group(0)
        p = Path(urllib.parse.unquote(src))
        if not p.is_absolute():
            p = Path(base_path) / p if base_path else p
        if not p.exists():
            return m.group(0)
        try:
            url = upload_with_cache(str(p), timeout)
            uploaded += 1
            return m.group(0).replace(f'src="{src}"', f'src="{url}"', 1)
        except Exception as e:
            failed += 1
            logger.error(f"Upload failed for {p}: {e}")
            return m.group(0)

    return _LOCAL_SRC_RE.sub(_repl, html), uploaded, failed