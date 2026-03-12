"""
LLM provider abstraction used by generation services.
"""
import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


class LLMServiceError(Exception):
    """Raised when an LLM request fails or returns invalid output."""


@dataclass(slots=True)
class LLMResult:
    data: dict[str, Any]
    tokens_used: int
    model_used: str


class LLMService:
    def __init__(self) -> None:
        self._provider = settings.LLM_PROVIDER
        self._api_key = settings.OPENAI_API_KEY
        self._model = settings.OPENAI_MODEL
        self._base_url = settings.OPENAI_BASE_URL.rstrip("/")
        self._timeout = settings.LLM_TIMEOUT_SECONDS

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 1400,
    ) -> LLMResult:
        if self._provider == "mock":
            return self._generate_mock_json(user_prompt=user_prompt)
        if self._provider != "openai":
            raise LLMServiceError(f"Unsupported LLM_PROVIDER '{self._provider}'.")

        if not self._api_key:
            raise LLMServiceError("OPENAI_API_KEY is empty.")

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise LLMServiceError(f"LLM HTTP request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMServiceError(
                f"LLM provider returned {response.status_code}: {response.text[:500]}"
            )

        try:
            raw = response.json()
            message_content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(message_content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMServiceError("LLM response is not valid JSON content.") from exc

        usage = raw.get("usage") or {}
        tokens_used = int(usage.get("total_tokens") or 0)
        model_used = str(raw.get("model") or self._model)
        return LLMResult(data=parsed, tokens_used=tokens_used, model_used=model_used)

    def _generate_mock_json(self, *, user_prompt: str) -> LLMResult:
        content = {
            "title": "Mock Generated Title",
            "description": user_prompt[:180],
            "sections": ["Introduction", "Main Insights", "Conclusion"],
            "secondary_keywords": [],
            "primary_keyword": "mock keyword",
            "canonical_slug": "mock-generated-title",
        }
        return LLMResult(data=content, tokens_used=0, model_used="mock")
