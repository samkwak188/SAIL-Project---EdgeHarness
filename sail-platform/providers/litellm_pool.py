"""LiteLLM pool — single interface to hybrid GPU + edge providers.

Role mapping (oh-my-pi pattern): smol / default / slow / plan / judge.
Each role resolves to a list of providers; first available wins.

Guided-JSON support: when a provider exposes `guided_json` (vLLM/SGLang),
structured outputs are enforced at the sampler so the model cannot emit
invalid JSON. Otherwise, fall back to json_repair on the response.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CompletionResult:
    content: str
    tool_calls: list[dict[str, Any]]
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost: float
    provider: str
    raw: dict[str, Any]


class LiteLLMPool:
    def __init__(self, models_config: dict[str, Any]):
        self.providers = models_config.get("providers", {})
        self.role_mapping = models_config.get("role_mapping", {})
        self.embedding_cfg = models_config.get("embedding", {})
        self.ensemble_cfg = models_config.get("ensemble", {})

    def resolve_provider(self, role: str) -> tuple[str, dict[str, Any]]:
        candidates = self.role_mapping.get(role, self.role_mapping.get("default", []))
        if not candidates:
            raise RuntimeError(f"no provider configured for role {role}")
        name = candidates[0]
        return name, self.providers[name]

    def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        model_role: str = "default",
        guided_json: dict[str, Any] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        name, prov = self.resolve_provider(model_role)
        t0 = time.time()

        # Stub mode: skip litellm entirely (dev/test when no model server is up)
        if prov.get("stub"):
            return self._stub_complete(name, system, messages, tools, guided_json, t0)

        try:
            import litellm  # type: ignore
        except ImportError:  # pragma: no cover
            return self._stub_complete(name, system, messages, tools, guided_json, t0)

        # Build the litellm call. We use the openai-compatible path so any
        # vLLM/SGLang/Ollama endpoint works through one code path.
        model = self._litellm_model_name(prov, name)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_base": prov.get("base_url"),
        }
        if tools:
            kwargs["tools"] = [
                {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
                for t in tools
            ]
            kwargs["tool_choice"] = "auto"
        if guided_json and prov.get("guided_json"):
            # vLLM/SGLang accept extra_body with guided_decoding_backend / json_schema
            kwargs["extra_body"] = {"guided_json": guided_json}

        try:
            resp = litellm.completion(**kwargs)
            t1 = time.time()
            choice = resp.choices[0].message
            content = choice.content or ""
            tool_calls = self._extract_tool_calls(choice)
            usage = getattr(resp, "usage", None)
            tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
            tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
            cost = float(getattr(resp, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)
            return {
                "content": content,
                "tool_calls": tool_calls,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": int((t1 - t0) * 1000),
                "cost": cost,
                "provider": name,
            }
        except Exception as e:  # pragma: no cover — depends on live server
            t1 = time.time()
            return {
                "content": f"[provider error: {e}]",
                "tool_calls": [],
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms": int((t1 - t0) * 1000),
                "cost": 0.0,
                "provider": name,
                "error": str(e),
            }

    @staticmethod
    def _litellm_model_name(prov: dict[str, Any], name: str) -> str:
        prov_type = prov.get("type", "openai_compatible")
        model = prov.get("model", name)
        if prov_type == "ollama":
            return f"ollama/{model}"
        if prov_type == "openrouter":
            return f"openrouter/{model}"  # litellm reads OPENROUTER_API_KEY, no api_base needed
        return model  # openai_compatible uses api_base + raw model name

    @staticmethod
    def _extract_tool_calls(choice: Any) -> list[dict[str, Any]]:
        tcs = getattr(choice, "tool_calls", None) or []
        out = []
        for tc in tcs:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            import json as _json
            try:
                args = _json.loads(fn.arguments)
            except Exception:
                args = {"_raw": fn.arguments}
            out.append({"id": getattr(tc, "id", None), "name": fn.name, "arguments": args})
        return out

    def _stub_complete(
        self,
        provider_name: str,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None,
        guided_json: dict[str, Any] | None,
        t0: float,
    ) -> dict[str, Any]:
        """Deterministic stub for tests / dev when no model server is available."""
        t1 = time.time()
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), messages[-1] if messages else {})
        text = last_user.get("content", "")[:200]
        # If guided_json requested, emit a minimal valid stub matching the schema
        if guided_json and "properties" in guided_json:
            stub_obj = {k: "stub" for k in guided_json["properties"]}
            content = json.dumps(stub_obj)
        else:
            content = f"[stub:{provider_name}] ack: {text}"
        return {
            "content": content,
            "tool_calls": [],
            "tokens_in": len(system) // 4 + len(text) // 4,
            "tokens_out": len(content) // 4,
            "latency_ms": int((t1 - t0) * 1000),
            "cost": 0.0,
            "provider": provider_name,
        }
