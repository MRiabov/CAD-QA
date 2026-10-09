"""OpenRouter teacher client for CAD-QA rejection sampling.

Calls deepseek/deepseek-v4.1-flash with a row prompt + the row's tool schema;
returns the completion text and per-call usage/cost for spend monitoring.

Sampling follows the DeepSeek-V4.1-Flash LLM model card: temperature=1.0, top_p=0.95.
Do NOT lower the temperature for higher success — the card's instruct/agentic
guidance recommends 1.0.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, Field

from tool_calls import ToolName, _tool_call_prompt_suffix

DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash:deepseek"  # pinned to the DeepSeek provider
DEFAULT_TEMPERATURE = 1.0  # DeepSeek-V4.1-Flash LLM model card recommendation
DEFAULT_TOP_P = 0.95  # DeepSeek-V4.1-Flash LLM model card recommendation
API_BASE = "https://openrouter.ai/api/v1"


class TeacherCall(BaseModel):
    text: str = Field(default="", description="Answer content (may be empty if reasoning-only).")
    reasoning: str = Field(default="", description="Hidden reasoning phase (deepseek message.reasoning).")
    tool_calls: list[dict] | None = Field(default=None, description="Raw native tool_calls from the provider, when used.")
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
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        max_tokens: int = 8192,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or _key_from_env_file()
        if not self.api_key:
            raise TeacherError("OPENROUTER_API_KEY not set")
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self._pricing: dict[str, float] | None = None

    # -- pricing ------------------------------------------------------------

    def _load_pricing(self) -> dict[str, float]:
        if self._pricing is None:
            base_id = self.model.split(":")[0]  # strip any :provider routing suffix
            r = self.session.get(f"{API_BASE}/models", timeout=30)
            r.raise_for_status()
            for m in r.json().get("data", []):
                if m.get("id") == base_id:
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
        """Single user-turn completion (backward-compatible wrapper)."""
        return self.complete_messages([{"role": "user", "content": prompt}])

    def complete_messages(self, messages: list[dict], tools: list[dict] | None = None) -> TeacherCall:
        """Multi-turn completion; `tools` enables native provider tool calls.

        A native tool-call response (content empty, args in tool_calls) is
        converted to the JSON envelope in `text` so callers can parse it with
        extract_tool_call; the raw `tool_calls` stay available for API
        round-trip continuation (role="tool" messages).
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
        r = self.session.post(f"{API_BASE}/chat/completions", json=payload, timeout=180)
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
        tool_calls = msg.get("tool_calls") or None
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
            tool_calls=tool_calls,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=cost,
        )


def build_teacher_prompt(row_prompt: str, tool: ToolName, hop_count: int | None = None,
                         compute_tool: bool = True) -> str:
    hop_line = f"\nThis question requires {hop_count} logical reasoning hops." if hop_count is not None else ""
    compute_section = (
        "\n[compute tool]\n"
        "You have a `run_code` tool: it executes python with numpy preloaded (as `np`) and "
        "`math`, and the value of the last expression is returned to you automatically (like "
        "a notebook cell). Use it when the question demands exact calculations (coordinates, "
        "distances, volumes, frame transforms); otherwise skip it and reason directly. You "
        "may call it multiple times and iterate until the calculation is correct.\n"
    ) if compute_tool else ""
    return (
        "You are solving a CAD (CadQuery) question. Read the script carefully and reason step by step.\n"
        f"{hop_line}\n"
        f"{compute_section}"
        "\n[question]\n"
        f"{row_prompt}\n"
        f"{_tool_call_prompt_suffix(tool)}"
    )


def _key_from_env_file() -> str | None:
    """Fallback: read OPENROUTER_API_KEY from the repo .env file."""
    for candidate in (Path(__file__).resolve().parent.parent.parent.parent / ".env", Path.cwd() / ".env"):
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None
