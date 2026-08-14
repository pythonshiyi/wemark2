from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.ai_client import AIClient, UsageInfo, ChatResponse, RETRYABLE_STATUS


class TestUsageInfo:
    def test_defaults_to_zero(self):
        u = UsageInfo()
        assert u.prompt_tokens == 0
        assert u.completion_tokens == 0
        assert u.total_tokens == 0

    def test_can_set_values(self):
        u = UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert u.prompt_tokens == 10
        assert u.completion_tokens == 20
        assert u.total_tokens == 30


class TestChatResponse:
    def test_defaults(self):
        r = ChatResponse(content="Hello")
        assert r.content == "Hello"
        assert r.reasoning_content == ""
        assert r.usage is None

    def test_with_reasoning(self):
        r = ChatResponse(content="Answer", reasoning_content="Thinking...")
        assert r.reasoning_content == "Thinking..."

    def test_with_usage(self):
        usage = UsageInfo(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        r = ChatResponse(content="Hi", usage=usage)
        assert r.usage.total_tokens == 15


class TestAIClientInitialization:
    def test_available_false_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("core.ai_client.config_manager") as mock_cfg:
            mock_cfg.get.return_value = {"api_key": ""}
            client = AIClient()
            assert client.available is False


class TestFetchModels:
    def test_fetch_models_returns_list(self, monkeypatch):
        client = AIClient()
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = {
                "data": [{"id": "model-1"}, {"id": "model-2"}]
            }
            mock_client.return_value.__enter__.return_value = mock_instance
            models = client.fetch_models("https://api.example.com")
            assert models == ["model-1", "model-2"]

    def test_fetch_models_empty_on_error(self, monkeypatch):
        client = AIClient()
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = Exception("Connection error")
            mock_client.return_value.__enter__.return_value = mock_instance
            models = client.fetch_models("https://api.example.com")
            assert models == []

    def test_fetch_models_empty_on_non_200(self, monkeypatch):
        client = AIClient()
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value.status_code = 401
            mock_client.return_value.__enter__.return_value = mock_instance
            models = client.fetch_models("https://api.example.com")
            assert models == []

    def test_fetch_models_with_api_key(self, monkeypatch):
        client = AIClient()
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = {"data": [{"id": "m1"}]}
            mock_client.return_value.__enter__.return_value = mock_instance
            models = client.fetch_models("https://api.example.com", "my-key")
            assert models == ["m1"]
            call_kwargs = mock_instance.get.call_args[1]
            assert "Authorization" in call_kwargs.get("headers", {})

    def test_fetch_models_without_auth_for_ollama(self, monkeypatch):
        client = AIClient()
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = {"data": [{"id": "m1"}]}
            mock_client.return_value.__enter__.return_value = mock_instance
            models = client.fetch_models("http://localhost:11434", "ollama")
            assert models == ["m1"]

    def test_fetch_models_no_data_key(self, monkeypatch):
        client = AIClient()
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value.status_code = 200
            mock_instance.get.return_value.json.return_value = {"models": []}
            mock_client.return_value.__enter__.return_value = mock_instance
            models = client.fetch_models("https://api.example.com")
            assert models == []


class TestRetryConstants:
    def test_retryable_status_codes(self):
        assert 429 in RETRYABLE_STATUS
        assert 500 in RETRYABLE_STATUS
        assert 502 in RETRYABLE_STATUS
        assert 503 in RETRYABLE_STATUS
        assert 504 in RETRYABLE_STATUS
        assert 404 not in RETRYABLE_STATUS
        assert 401 not in RETRYABLE_STATUS


class TestModelProperty:
    def test_model_property(self):
        client = AIClient()
        model = client.model
        assert isinstance(model, str)
        assert len(model) > 0

    def test_reasoning_effort_property(self):
        client = AIClient()
        effort = client.reasoning_effort
        assert isinstance(effort, str) and len(effort) > 0

    def test_thinking_enabled_property(self):
        client = AIClient()
        assert isinstance(client.thinking_enabled, bool)


class TestChatRaisesWithoutClient:
    def test_chat_raises_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Override config to have no API key
        with patch("core.ai_client.config_manager") as mock_cfg:
            mock_cfg.get.return_value = {}
            client = AIClient()
            client._client = None
            with pytest.raises(RuntimeError, match="AI 客户端未配置"):
                client.chat(messages=[{"role": "user", "content": "hi"}])
