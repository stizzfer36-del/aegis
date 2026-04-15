from __future__ import annotations

import json
from collections.abc import Iterator

import httpx


class OpenRouterProvider:
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aegis.local",
                "X-Title": "AEGIS",
            },
            timeout=120.0,
        )

    def complete(
        self,
        messages: list[dict],
        model: str = "anthropic/claude-opus-4-5",
        max_tokens: int = 4096,
        temperature: float = 0.2,
        **kwargs,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        payload.update(kwargs)
        resp = self._client.post("/chat/completions", json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter API error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def stream(self, messages: list[dict], model: str = "anthropic/claude-opus-4-5", **kwargs) -> Iterator[str]:
        payload = {"model": model, "messages": messages, "stream": True}
        payload.update(kwargs)
        with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"OpenRouter API error {resp.status_code}: {resp.text}")
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                chunk = delta.get("content")
                if chunk:
                    yield chunk
