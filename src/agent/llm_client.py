import os
import asyncio
import time
import re
import requests
from dotenv import load_dotenv
from pathlib import Path
from utils.debug_log import log_call

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


API_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_LOCAL_BASES = ("localhost", "127.0.0.1", "0.0.0.0")


def _retry_with_backoff(fn, max_retries=5, rate_base=2.0, rate_max=30.0, empty_base=2.0, empty_max=15.0, cancel_check=None):
    for attempt in range(max_retries):
        if cancel_check and cancel_check():
            raise RuntimeError("AI call cancelled by stop")
        try:
            return fn()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait = min(rate_base * (2 ** attempt), rate_max)
                headers = dict(e.response.headers)
                retry_after = headers.get("Retry-After", headers.get("retry-after", "?"))
                print(f"[LLM] Rate limited (retry-after: {retry_after}s), retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
        except ValueError as e:
            if "Empty response" in str(e) and attempt < max_retries - 1:
                wait = min(empty_base * (2 ** attempt), empty_max)
                print(f"[LLM] Empty response, retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


class LLMClient:
    def __init__(self, config: dict):
        self.model = config.get("model", "nvidia/nemotron-nano-12b-v2-vl:free")
        self.temperature = config.get("temperature", 0.7)
        self.provider = config.get("provider", "openai")
        self.base_url = config.get("base_url") or API_BASE_URLS.get(self.provider)
        self.api_key = config.get("api_key") or os.getenv(API_KEY_ENV.get(self.provider, ""))

        if self.provider == "anthropic":
            pass
        elif self.base_url:
            self.provider = "openai"
        elif self.provider in API_BASE_URLS:
            self.base_url = API_BASE_URLS[self.provider]
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        self._needs_key = not any(h in (self.base_url or "") for h in _LOCAL_BASES)
        self.timeout = config.get("timeout", 120 if not self._needs_key else 30)
        self.retry_rate_base = config.get("retry_rate_base", 2.0)
        self.retry_rate_max = config.get("retry_rate_max", 30.0)
        self.retry_empty_base = config.get("retry_empty_base", 2.0)
        self.retry_empty_max = config.get("retry_empty_max", 15.0)
        self.cancel_check = None

    def set_retry_params(self, rate_base: float, rate_max: float):
        self.retry_rate_base = rate_base
        self.retry_rate_max = rate_max

    def set_model(self, provider: str, model: str, base_url: str = ""):
        self.provider = provider
        self.model = model
        self.base_url = base_url or API_BASE_URLS.get(provider, "")
        self.api_key = os.getenv(API_KEY_ENV.get(self.provider, ""))

        if self.provider == "anthropic":
            pass
        elif self.base_url:
            self.provider = "openai"
        elif self.provider in API_BASE_URLS:
            self.base_url = API_BASE_URLS[self.provider]
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        self._needs_key = not any(h in (self.base_url or "") for h in _LOCAL_BASES)
        self.timeout = 120 if not self._needs_key else 30

    def set_cancel_check(self, fn):
        self.cancel_check = fn

    def _call_openai(self, messages: list, max_tokens: int = 120, temperature: float | None = None) -> str:
        def _do_call():
            headers = {"Content-Type": "application/json"}
            if self._needs_key and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature if temperature is not None else self.temperature,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data or not isinstance(data, dict):
                raise ValueError(f"Invalid API response: {resp.text}")
            choices = data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                raise ValueError(f"No choices in response: {data}")
            choice = choices[0]
            if not isinstance(choice, dict):
                raise ValueError(f"Invalid choice in response: {choice}")
            msg = choice.get("message") or {}
            content = msg.get("content")
            if not content:
                raise ValueError(f"Empty response from model: {data}")
            return content.strip()
        return _retry_with_backoff(
            _do_call,
            rate_base=self.retry_rate_base,
            rate_max=self.retry_rate_max,
            empty_base=self.retry_empty_base,
            empty_max=self.retry_empty_max,
            cancel_check=self.cancel_check,
        )

    def _call_anthropic(self, messages: list, max_tokens: int = 120, temperature: float | None = None) -> str:
        if self.cancel_check and self.cancel_check():
            raise RuntimeError("AI call cancelled by stop")
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "system": messages[0]["content"],
                "messages": messages[1:],
                "max_tokens": max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()

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
            text = await asyncio.to_thread(self._call_openai, messages, 10)
        elif self.provider == "anthropic":
            text = await asyncio.to_thread(self._call_anthropic, messages, 10)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        raw = text
        text = text.lower()
        for name in action_names:
            if re.search(rf"\b{re.escape(name)}\b", text):
                log_call("ACTION", getattr(self, '_frame', 0), messages, raw, name, 0)
                return name
        log_call("ACTION", getattr(self, '_frame', 0), messages, raw, "none", 0)
        return "none"

    async def commentate(self, messages: list, max_tokens: int = 120) -> str:
        if self.provider in ("openai", "openrouter"):
            text = await asyncio.to_thread(self._call_openai, messages, max_tokens, 0.9)
        elif self.provider == "anthropic":
            text = await asyncio.to_thread(self._call_anthropic, messages, max_tokens, 0.9)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        log_call("COMMENTARY", getattr(self, '_frame', 0), messages, text, text[:100], 0)
        return text
