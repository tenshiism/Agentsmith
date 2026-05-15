import pytest
from agent.llm_client import LLMClient


class TestLLMClientChooseAction:
    def _make_client(self):
        return LLMClient({"model": "gpt-4o", "provider": "openai", "api_key": "test"})

    @pytest.mark.asyncio
    async def test_choose_action_parses_direct_match(self, monkeypatch):
        client = self._make_client()

        async def fake_create(*args, **kwargs):
            class FakeChoice:
                class Message:
                    content = "a"
                message = Message()
            class FakeResp:
                choices = [FakeChoice()]
            return FakeResp()

        monkeypatch.setattr(client._client.chat.completions, "create", fake_create)
        result = await client.choose_action(
            [{"role": "system", "content": "play"}],
            ["a", "b", "up", "down"],
        )
        assert result == "a"

    @pytest.mark.asyncio
    async def test_choose_action_parses_partial_match(self, monkeypatch):
        client = self._make_client()

        async def fake_create(*args, **kwargs):
            class FakeChoice:
                class Message:
                    content = "I think we should press up"
                message = Message()
            class FakeResp:
                choices = [FakeChoice()]
            return FakeResp()

        monkeypatch.setattr(client._client.chat.completions, "create", fake_create)
        result = await client.choose_action(
            [{"role": "system", "content": "play"}],
            ["a", "b", "up", "down"],
        )
        assert result == "up"

    @pytest.mark.asyncio
    async def test_choose_action_returns_none_on_no_match(self, monkeypatch):
        client = self._make_client()

        async def fake_create(*args, **kwargs):
            class FakeChoice:
                class Message:
                    content = "hmm not sure what to do"
                message = Message()
            class FakeResp:
                choices = [FakeChoice()]
            return FakeResp()

        monkeypatch.setattr(client._client.chat.completions, "create", fake_create)
        result = await client.choose_action(
            [{"role": "system", "content": "play"}],
            ["a", "b", "up", "down"],
        )
        assert result == "none"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClient({"provider": "unknown"})
