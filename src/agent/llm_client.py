import os
import asyncio
import time
import re
import requests
from dotenv import load_dotenv
from pathlib import Path
from utils.debug_log import log_call
from .model_pricing import MODEL_PRICING

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


API_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "kobold": "http://localhost:5001/v1",
}

PROVIDER_ALIASES = {
    "koboldcpp": "kobold",
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
                retry_after = dict(e.response.headers).get("Retry-After", "?")
                print(f"[LLM] Rate limited (retry-after: {retry_after}s), retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
        except ValueError as e:
            if "Empty response" in str(e) and attempt < max_retries - 1:
                wait = min(empty_base * (2 ** attempt), empty_max)
                print(f"[LLM] Empty response, retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                if wait > 0:
                    time.sleep(wait)
            else:
                raise


class LLMClient:
    def __init__(self, config: dict):
        self.model = config.get("model", "google/gemma-4-26b-a4b-it:free")
        self.temperature = config.get("temperature", 0.7)
        self.provider = PROVIDER_ALIASES.get(
            config.get("provider", "openrouter").lower().replace(" ", ""),
            config.get("provider", "openrouter").lower().replace(" ", "")
        )
        self.base_url = config.get("base_url") or API_BASE_URLS.get(self.provider)
        key_env = API_KEY_ENV.get(self.provider, "")
        self.api_key = config.get("api_key") or (os.getenv(key_env) if key_env else None)
        self._action_max_tokens = 10
        self._commentary_max_tokens = 120

        if self.provider not in API_BASE_URLS and self.provider != "anthropic":
            raise ValueError(f"Unknown provider: {self.provider}")
        if not self.base_url:
            self.base_url = API_BASE_URLS.get(self.provider)

        self._needs_key = not any(h in (self.base_url or "") for h in _LOCAL_BASES)
        self.timeout = config.get("timeout", 120 if not self._needs_key else 30)
        self.max_retries = config.get("max_retries", 5)
        self.retry_rate_base = config.get("retry_rate_base", 2.0)
        self.retry_rate_max = config.get("retry_rate_max", 30.0)
        self.retry_empty_base = config.get("retry_empty_base", 2.0)
        self.retry_empty_max = config.get("retry_empty_max", 15.0)
        self.cancel_check = None

    def set_retry_params(self, rate_base: float, rate_max: float):
        self.retry_rate_base = rate_base
        self.retry_rate_max = rate_max

    def set_model(self, provider: str, model: str, base_url: str = ""):
        self.provider = PROVIDER_ALIASES.get(provider.lower().replace(" ", ""), provider.lower().replace(" ", ""))
        self.model = model
        self.base_url = base_url or API_BASE_URLS.get(self.provider, "")
        key_env = API_KEY_ENV.get(self.provider, "")
        self.api_key = os.getenv(key_env) if key_env else None

        if self.provider not in API_BASE_URLS and self.provider != "anthropic":
            raise ValueError(f"Unknown provider: {self.provider}")
        if not self.base_url:
            self.base_url = API_BASE_URLS.get(self.provider)

        self._needs_key = not any(h in (self.base_url or "") for h in _LOCAL_BASES)
        self.timeout = 120 if not self._needs_key else 30

    def set_cancel_check(self, fn):
        self.cancel_check = fn

    def _call_openai(self, messages: list, max_tokens: int = 120, temperature: float | None = None) -> tuple[str, dict]:
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
            usage = data.get("usage", {})
            cost = usage.get("cost")
            if cost is None:
                prices = MODEL_PRICING.get(self.model, {})
                if not prices:
                    print(f"[LLM] Warning: unknown model '{self.model}' — skipping cost calculation")
                pt = usage.get("prompt_tokens", 0)
                ct = usage.get("completion_tokens", 0)
                cost = pt * prices.get("prompt", 0) + ct * prices.get("completion", 0)
            return content.strip(), {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "cost": cost,
            }
        return _retry_with_backoff(
            _do_call,
            max_retries=self.max_retries,
            rate_base=self.retry_rate_base,
            rate_max=self.retry_rate_max,
            empty_base=self.retry_empty_base,
            empty_max=self.retry_empty_max,
            cancel_check=self.cancel_check,
        )

    def _call_anthropic(self, messages: list, max_tokens: int = 120, temperature: float | None = None) -> tuple[str, dict]:
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
        data = resp.json()
        usage = data.get("usage", {})
        pt = usage.get("input_tokens", 0)
        ct = usage.get("output_tokens", 0)
        prices = MODEL_PRICING.get(self.model, {})
        if not prices:
            print(f"[LLM] Warning: unknown model '{self.model}' — skipping cost calculation")
        cost = pt * prices.get("prompt", 0) + ct * prices.get("completion", 0)
        return data["content"][0]["text"].strip(), {
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "cost": cost,
        }

    async def choose_action(self, messages: list, action_names: list[str]) -> tuple[str, dict]:
        action_list = ", ".join(action_names)
        system_instruction = (
            f"{messages[0]['content']}\n\n"
            f"Available actions: {action_list}\n"
            f"Respond with EXACTLY one action name from the list, or 'none' to do nothing. "
            f"Output ONLY the action name, nothing else."
        )
        messages[0]["content"] = system_instruction

        if self.provider in ("openai", "openrouter"):
            text, usage = await asyncio.to_thread(self._call_openai, messages, 10)
        elif self.provider == "anthropic":
            text, usage = await asyncio.to_thread(self._call_anthropic, messages, 10)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        raw = text
        text = text.lower()
        for name in action_names:
            if re.search(rf"\b{re.escape(name)}\b", text):
                log_call("ACTION", getattr(self, '_frame', 0), messages, raw, name, 0)
                return name, usage
        log_call("ACTION", getattr(self, '_frame', 0), messages, raw, "none", 0)
        return "none", usage

    async def commentate(self, messages: list, max_tokens: int = 0) -> tuple[str, dict]:
        mt = max_tokens or self._commentary_max_tokens
        if self.provider in ("openai", "openrouter", "kobold"):
            text, usage = await asyncio.to_thread(self._call_openai, messages, mt, 0.9)
        elif self.provider == "anthropic":
            text, usage = await asyncio.to_thread(self._call_anthropic, messages, mt, 0.9)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        log_call("COMMENTARY", getattr(self, '_frame', 0), messages, text, text[:100], 0)
        return text, usage
