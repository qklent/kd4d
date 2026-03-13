from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from ..config import settings
from ..models.schemas import ChatCompletionRequest


class LLMClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.timeout = timeout or settings.llm_timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

    async def complete(
        self, messages: list[dict[str, str]], request: ChatCompletionRequest
    ) -> dict:
        payload = self._build_payload(messages, request, stream=False)
        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def stream(
        self, messages: list[dict[str, str]], request: ChatCompletionRequest
    ) -> AsyncIterator[dict]:
        payload = self._build_payload(messages, request, stream=True)
        async with self._client.stream(
            "POST", "/chat/completions", json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data.strip() == "[DONE]":
                    break
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _build_payload(
        messages: list[dict[str, str]],
        request: ChatCompletionRequest,
        stream: bool,
    ) -> dict:
        payload: dict = {
            "model": request.model,
            "messages": messages,
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload
