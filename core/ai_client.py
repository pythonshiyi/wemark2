import os
import threading
import time
from dataclasses import dataclass
from typing import Generator, List, Dict, Optional, Union

import httpx
from openai import OpenAI

from core.config import config_manager
from core.logger import get_logger

logger = get_logger("ai_client")

# 可重试的 HTTP 状态码
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
BASE_DELAY = 1.0


@dataclass
class UsageInfo:
    """Token 用量信息。"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResponse:
    """非流式聊天响应，包含主内容、思考过程和用量。"""
    content: str
    reasoning_content: str = ""
    usage: Optional[UsageInfo] = None


class AIClient:
    def __init__(self):
        self._lock = threading.Lock()
        self._client: Optional[OpenAI] = None
        self._init_client()

    def _init_client(self):
        cfg = config_manager.get("ai")
        if cfg is None:
            cfg = {}
        api_key = cfg.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
        base_url = cfg.get("base_url", "https://api.deepseek.com")
        self._model = cfg.get("model", "deepseek-v4-flash")
        self._temperature = cfg.get("temperature", 1.3)
        self._top_p = cfg.get("top_p", 1.0)
        self._reasoning_effort = cfg.get("reasoning_effort", "high")
        self._thinking_enabled = cfg.get("thinking_enabled", True)
        self._max_tokens = cfg.get("max_tokens", 4096)

        if api_key:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = None

    @property
    def available(self) -> bool:
        with self._lock:
            return self._client is not None

    @property
    def model(self) -> str:
        return self._model

    @property
    def reasoning_effort(self) -> str:
        return self._reasoning_effort

    @property
    def thinking_enabled(self) -> bool:
        return self._thinking_enabled

    def reload(self):
        self._init_client()

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = None,
        reasoning_effort: str = None,
        thinking_enabled: bool = None,
        max_tokens: int = None,
    ) -> Union[ChatResponse, Generator]:
        with self._lock:
            client = self._client
        if not client:
            raise RuntimeError("AI 客户端未配置，请在设置中填写 API Key")

        temp = temperature if temperature is not None else self._temperature
        effort = reasoning_effort if reasoning_effort is not None else self._reasoning_effort
        think = thinking_enabled if thinking_enabled is not None else self._thinking_enabled
        mt = max_tokens if max_tokens is not None else self._max_tokens

        kwargs = dict(
            model=self._model,
            input=messages,
            stream=stream,
            temperature=temp,
            top_p=self._top_p,
            max_output_tokens=mt,
        )
        kwargs["reasoning"] = {"effort": effort if think else "none"}

        response = self._call_with_retry(client, **kwargs)

        if stream:
            return self._stream_response(response)
        else:
            return self._parse_response(response)

    def _call_with_retry(self, client: OpenAI, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return client.responses.create(**kwargs)
            except Exception as e:
                last_error = e
                status = getattr(e, "status_code", None) or getattr(e, "status", None)
                if status in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"API retry {attempt + 1}/{MAX_RETRIES} after {delay:.1f}s "
                        f"(HTTP {status}): {e}"
                    )
                    time.sleep(delay)
                else:
                    raise
        raise last_error

    def _parse_response(self, response) -> ChatResponse:
        content = getattr(response, "output_text", "") or ""
        reasoning = ""
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "reasoning":
                continue
            for part in getattr(item, "summary", None) or []:
                text = getattr(part, "text", None)
                if text:
                    reasoning += text
            for part in getattr(item, "content", None) or []:
                text = getattr(part, "text", None)
                if text:
                    reasoning += text
        usage = None
        if getattr(response, "usage", None):
            usage = UsageInfo(
                prompt_tokens=getattr(response.usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "output_tokens", 0) or 0,
                total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
            )
        return ChatResponse(
            content=content,
            reasoning_content=reasoning,
            usage=usage,
        )

    def _stream_response(self, response) -> Generator[dict, None, None]:
        final_usage = None
        try:
            for event in response:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        yield {"delta_content": delta}
                elif event_type == "response.reasoning_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        yield {"delta_reasoning": delta}
                elif event_type in ("response.completed", "response.incomplete"):
                    resp = getattr(event, "response", None)
                    if resp is not None and getattr(resp, "usage", None):
                        u = resp.usage
                        final_usage = UsageInfo(
                            prompt_tokens=getattr(u, "input_tokens", 0) or 0,
                            completion_tokens=getattr(u, "output_tokens", 0) or 0,
                            total_tokens=getattr(u, "total_tokens", 0) or 0,
                        )
                elif event_type == "response.failed":
                    resp = getattr(event, "response", None)
                    error = getattr(resp, "error", None) if resp is not None else None
                    if error is not None:
                        raise RuntimeError(f"API error: {error}")
            if final_usage:
                yield {"_usage": final_usage}
        finally:
            try:
                response.close()
            except Exception:
                pass

    def fetch_models(self, base_url: str, api_key: str = None) -> List[str]:
        url = base_url.rstrip("/") + "/models"
        headers = {}
        if api_key and api_key not in ("ollama", "lm-studio"):
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and isinstance(data["data"], list):
                        return [item["id"] for item in data["data"] if "id" in item]
        except Exception as e:
            logger.error(f"Failed to fetch models: {e}")
        return []


ai_client = AIClient()
