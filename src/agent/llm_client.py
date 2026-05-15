import os
import json
from typing import Optional
import re


class LLMClient:
    def __init__(self, config: dict):
        self.model = config.get("model", "gpt-4o")
        self.temperature = config.get("temperature", 0.7)
        self.provider = config.get("provider", "openai")
        self._client = None

        if self.provider == "openai":
            import openai
            self._client = openai.AsyncOpenAI(api_key=config.get("api_key") or os.getenv("OPENAI_API_KEY"))
        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=config.get("api_key") or os.getenv("ANTHROPIC_API_KEY"))
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

        if self.provider == "openai":
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
        if self.provider == "openai":
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
