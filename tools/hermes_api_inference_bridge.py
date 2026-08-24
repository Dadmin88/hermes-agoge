from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def _usage_dict(usage: object) -> dict[str, object] | None:
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        value = usage.model_dump()
        return value if type(value) is dict else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-root", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        raise RuntimeError("workers must be between 1 and 16")

    hermes_root = Path(args.hermes_root).resolve()
    sys.path.insert(0, str(hermes_root))
    provider = args.provider.strip().lower()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if type(payload) is not dict or type(payload.get("requests")) is not list:
        raise RuntimeError("bridge input must contain a requests array")

    fixed_temperature: float | None = None
    default_max_tokens: int | None = None
    default_headers: dict[str, str] = {}
    if provider == "nous":
        from hermes_cli.auth import resolve_nous_runtime_credentials

        credentials = resolve_nous_runtime_credentials()
        if not credentials:
            raise RuntimeError("Nous runtime credentials are unavailable")
        runtime_key = credentials.get("api_key")
        base_url = str(credentials.get("base_url") or "").rstrip("/")
        if not runtime_key or not base_url:
            raise RuntimeError("Nous runtime credential resolution is incomplete")
    else:
        from hermes_cli.auth import resolve_api_key_provider_credentials
        from providers import get_provider_profile

        profile = get_provider_profile(provider)
        if profile is None or profile.api_mode != "chat_completions":
            raise RuntimeError(
                f"Hermes API bridge requires a chat-completions provider adapter: {provider}"
            )
        if profile.auth_type != "api_key":
            raise RuntimeError(
                f"Hermes API bridge provider auth type needs a dedicated adapter: {provider}"
            )
        credentials = resolve_api_key_provider_credentials(provider)
        runtime_key = credentials.get("api_key")
        base_url = str(credentials.get("base_url") or "").rstrip("/")
        if not runtime_key or not base_url:
            raise RuntimeError(f"{provider} runtime credential resolution is incomplete")
        fixed_temperature = profile.fixed_temperature
        default_max_tokens = profile.default_max_tokens
        default_headers = dict(profile.default_headers or {})

    from openai import OpenAI, OpenAIError

    client = OpenAI(
        api_key=runtime_key,
        base_url=base_url,
        default_headers=default_headers or None,
        max_retries=0,
        timeout=90.0,
    )

    def invoke(request: object) -> dict[str, Any]:
        if type(request) is not dict:
            return {"ok": False, "error": "request-not-object"}
        request_id = request.get("request_id")
        model = request.get("model")
        messages = request.get("messages")
        max_tokens = request.get("max_tokens", 128)
        temperature = request.get("temperature", 0)
        timeout_seconds = request.get("timeout_seconds", 30.0)
        if type(request_id) is not str or not request_id:
            return {"ok": False, "error": "invalid-request-id"}
        if type(model) is not str or not model:
            return {"request_id": request_id, "ok": False, "error": "invalid-model"}
        if type(messages) is not list or not messages:
            return {"request_id": request_id, "ok": False, "error": "invalid-messages"}
        if (
            isinstance(timeout_seconds, bool)
            or type(timeout_seconds) not in {int, float}
            or not 0 < float(timeout_seconds) <= 120
        ):
            return {"request_id": request_id, "ok": False, "error": "invalid-timeout"}
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=int(max_tokens if max_tokens is not None else (default_max_tokens or 128)),
                temperature=float(fixed_temperature if fixed_temperature is not None else temperature),
                stream=False,
                timeout=float(timeout_seconds),
            )
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            choice = response.choices[0] if response.choices else None
            message = choice.message if choice is not None else None
            content = message.content if message is not None else None
            if type(content) is not str:
                content = "" if content is None else str(content)
            return {
                "request_id": request_id,
                "ok": True,
                "model": getattr(response, "model", None) or model,
                "content": content,
                "finish_reason": getattr(choice, "finish_reason", None),
                "usage": _usage_dict(getattr(response, "usage", None)),
                "latency_ms": elapsed_ms,
            }
        except (OpenAIError, OSError, RuntimeError, TypeError, ValueError) as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return {
                "request_id": request_id,
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:800],
                "latency_ms": elapsed_ms,
            }

    requests = payload["requests"]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(invoke, requests))
    print(
        json.dumps(
            {
                "schema": "agoge.hermes-api-inference-bridge.v1",
                "provider": provider,
                "count": len(results),
                "results": results,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
