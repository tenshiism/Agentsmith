import pytest
import requests
from agent.llm_client import LLMClient


class TestLLMClientChooseAction:
    def _make_client(self):
        return LLMClient({"model": "test-model", "provider": "openai", "api_key": "test", "base_url": "http://localhost:9999/v1"})

    def _fake_response(self, content: str, status=200):
        resp = requests.Response()
        resp.status_code = status
        resp._content = (
            '{"choices": [{"message": {"content": "' + content + '"}}]}'
        ).encode()
        return resp

    @pytest.mark.asyncio
    async def test_choose_action_parses_direct_match(self, monkeypatch):
        client = self._make_client()

        def fake_post(*args, **kwargs):
            return self._fake_response("a")

        monkeypatch.setattr(requests, "post", fake_post)
        result = await client.choose_action(
            [{"role": "system", "content": "play"}],
            ["a", "b", "up", "down"],
        )
        assert result == "a"

    @pytest.mark.asyncio
    async def test_choose_action_parses_partial_match(self, monkeypatch):
        client = self._make_client()

        def fake_post(*args, **kwargs):
            return self._fake_response("I think we should press up")

        monkeypatch.setattr(requests, "post", fake_post)
        result = await client.choose_action(
            [{"role": "system", "content": "play"}],
            ["a", "b", "up", "down"],
        )
        assert result == "up"

    @pytest.mark.asyncio
    async def test_choose_action_returns_none_on_no_match(self, monkeypatch):
        client = self._make_client()

        def fake_post(*args, **kwargs):
            return self._fake_response("hmm not sure what to do")

        monkeypatch.setattr(requests, "post", fake_post)
        result = await client.choose_action(
            [{"role": "system", "content": "play"}],
            ["a", "b", "up", "down"],
        )
        assert result == "none"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClient({"provider": "unknown"})
