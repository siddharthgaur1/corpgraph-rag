"""Thin Claude wrapper: every rag/* step just needs .complete(prompt) -> str."""
from __future__ import annotations

import os


class ClaudeLLM:
    def __init__(self, model: str = "claude-sonnet-5", api_key: str | None = None):
        import anthropic

        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, prompt: str, max_tokens: int = 1024) -> str:
        resp = self._client.messages.create(
            model=self.model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
