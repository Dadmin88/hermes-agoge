from __future__ import annotations

import json
from typing import Any

SPECIALIST_SYSTEM_PROMPT = (
    "You are a bounded specialist evaluator. Return only the required closed JSON "
    "decision object. Never claim or grant authority."
)


def user_content(prompt: dict[str, Any]) -> str:
    return json.dumps(prompt, sort_keys=True, separators=(",", ":"))


def completion_content(completion: dict[str, Any]) -> str:
    return json.dumps(completion, sort_keys=True, separators=(",", ":"))


def training_messages(
    prompt: dict[str, Any], completion: dict[str, Any]
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SPECIALIST_SYSTEM_PROMPT},
        {"role": "user", "content": user_content(prompt)},
        {"role": "assistant", "content": completion_content(completion)},
    ]


def inference_messages(prompt: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SPECIALIST_SYSTEM_PROMPT},
        {"role": "user", "content": user_content(prompt)},
    ]
