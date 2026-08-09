"""OpenRouter teacher client for CAD-QA rejection sampling.

Calls deepseek/deepseek-v4-flash with a row prompt + the row's tool schema;
returns the completion text and per-call usage/cost for spend monitoring.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from pydantic import BaseModel, Field

from tool_calls import ToolName, tool_schema

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
API_BASE = "https://openrouter.ai/api/v1"


class TeacherCall(BaseModel):
    text: str = Field(default="", description="Answer content (may be empty if reasoning-only).")
    reasoning: str = Field(default="", description="Hidden reasoning phase (deepseek message.reasoning).")
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)


class TeacherError(RuntimeError):
    pass


class InsufficientBalanceError(TeacherError):
    pass


class TeacherClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 1.0,
        max_tokens: int = 8192,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or _key_from_env_file()
        if not self.api_key:
            raise TeacherError("OPENROUTER_API_KEY not set")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self._pricing: dict[str, float] | None = None

    # -- pricing ------------------------------------------------------------

    def _load_pricing(self) -> dict[str, float]:
        if self._pricing is None:
            r = self.session.get(f"{API_BASE}/models", timeout=30)
            r.raise_for_status()
            for m in r.json().get("data", []):
                if m.get("id") == self.model:
                    p = m.get("pricing", {})
                    self._pricing = {
                        "prompt": float(p.get("prompt", 0.0) or 0.0),
                        "completion": float(p.get("completion", 0.0) or 0.0),
                    }
                    break
            if self._pricing is None:
                self._pricing = {"prompt": 0.0, "completion": 0.0}
        return self._pricing

    def balance(self) -> float:
        r = self.session.get(f"{API_BASE}/credits", timeout=30)
        r.raise_for_status()
        return float(r.json().get("data", {}).get("total_credits", 0.0))

    # -- calls --------------------------------------------------------------

    def complete(self, prompt: str) -> TeacherCall:
        r = self.session.post(
            f"{API_BASE}/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            timeout=180,
        )
        if r.status_code == 402:
            raise InsufficientBalanceError("OpenRouter balance exhausted")
        if r.status_code == 429:
            raise TeacherError(f"rate limited: {r.text[:200]}")
        if r.status_code >= 400:
            raise TeacherError(f"OpenRouter {r.status_code}: {r.text[:300]}")
        data = r.json()
        usage = data.get("usage", {})
        pricing = self._load_pricing()
        cost = (
            usage.get("prompt_tokens", 0) * pricing["prompt"]
            + usage.get("completion_tokens", 0) * pricing["completion"]
        ) / 1_000_000
        msg = data["choices"][0]["message"]
        text = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        if not text.strip():
            # native tool-call response (content empty, args in tool_calls)
            tc = msg.get("tool_calls")
            if tc:
                fn = tc[0].get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                text = json.dumps({"name": fn.get("name"), "arguments": args})
            elif not reasoning.strip():
                raise TeacherError("empty completion")
        return TeacherCall(
            text=text,
            reasoning=reasoning,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=cost,
        )


def build_teacher_prompt(row_prompt: str, tool: ToolName, hop_count: int | None = None) -> str:
    schema = tool_schema(tool)
    hop_line = f"\nThis question requires {hop_count} logical reasoning hops." if hop_count is not None else ""
    return (
        "You are solving a CAD (CadQuery) question. Read the script carefully and reason step by step.\n"
        "Be CONCISE: keep the reasoning under 250 words — just the essential steps, then the answer.\n"
        f"{hop_line}\n"
        "\n[question]\n"
        f"{row_prompt}\n"
        "\n[answer contract]\n"
        f'Your final response MUST end with exactly one JSON tool call in this envelope:\n'
        f'{{"name": "{tool.value}", "arguments": {{...}}}}  # arguments must match the schema below\n'
        f"Tool schema: {json.dumps(schema['parameters'], sort_keys=True)}\n"
        "\nReason first, then emit the tool call as the last JSON object in your reply.\n"
    )


def _key_from_env_file() -> str | None:
    """Fallback: read OPENROUTER_API_KEY from the repo .env file."""
    for candidate in (Path(__file__).resolve().parent.parent.parent.parent / ".env", Path.cwd() / ".env"):
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None
