import os
import json
from typing import Optional
import re
from dotenv import load_dotenv

load_dotenv()


API_BASE_URLS = {
    "openai": None,
    "openrouter": "https://openrouter.ai/api/v1",
}

API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


class LLMClient:
    def __init__(self, config: dict):
        self.model = config.get("model", "qwen/qwen3.6-plus:free")
        self.temperature = config.get("temperature", 0.7)
        self.provider = config.get("provider", "openai")
        self._client = None

        base_url = API_BASE_URLS.get(self.provider)
        api_key = config.get("api_key") or os.getenv(API_KEY_ENV.get(self.provider, "OPENAI_API_KEY"))

        if self.provider in ("openai", "openrouter"):
            import openai
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def choose_action(self, messages: list, action_names: list[str]) -> str:
        action_list = ", ".join(action_names)
        system_instruction = (
            f"{messages[0]['content']}\n\n"
            f"Available actions: {action_list}\n"
            f"Respond with EXACTLY one action name from the list, or 'none' to do nothing. "
            f"Output ONLY the action name, nothing else."
        )
        messages[0]["content"] = system_instruction

        if self.provider in ("openai", "openrouter"):
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=10,
            )
            text = resp.choices[0].message.content.strip().lower()
        elif self.provider == "anthropic":
            resp = await self._client.messages.create(
                model=self.model,
                system=system_instruction,
                messages=messages[1:],
                max_tokens=10,
                temperature=self.temperature,
            )
            text = resp.content[0].text.strip().lower()

        for name in action_names:
            if re.search(rf"\b{re.escape(name)}\b", text):
                return name
        return "none"

    async def commentate(self, messages: list) -> str:
        if self.provider in ("openai", "openrouter"):
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip()
        elif self.provider == "anthropic":
            resp = await self._client.messages.create(
                model=self.model,
                system=messages[0]["content"],
                messages=messages[1:],
                max_tokens=120,
                temperature=0.9,
            )
            return resp.content[0].text.strip()
