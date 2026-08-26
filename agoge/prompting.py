from __future__ import annotations

import json
from typing import Any


def specialist_system_prompt(contract: dict[str, Any]) -> str:
    schema = contract.get("schema")
    decisions = contract.get("decision")
    reason_vocabulary = contract.get("reason_code_vocabulary", [])
    if type(schema) is not str or not schema:
        raise RuntimeError("Student output contract has no valid schema")
    if (
        type(decisions) is not list
        or not decisions
        or not all(type(item) is str and item for item in decisions)
    ):
        raise RuntimeError("Student output contract has no valid decisions")
    if type(reason_vocabulary) is not list or not all(
        type(item) is str and item for item in reason_vocabulary
    ):
        raise RuntimeError("Student output contract has an invalid reason-code vocabulary")
    decision_text = ", ".join(f'"{item}"' for item in decisions)
    reason_text = ", ".join(reason_vocabulary) if reason_vocabulary else "none declared"
    return (
        "You are Templar, a bounded low-authority evaluator inside Hermes Fleet. "
        "The user message is one sanitized Fleet event document. Do not repeat, summarize, "
        "or copy the event. Return exactly one compact JSON object with exactly these keys: "
        "schema, decision, reason_codes. The schema value must be "
        f'"{schema}". The decision value must be exactly one of {decision_text}. '
        "For ALLOW, reason_codes must be an empty array. For DENY or REVIEW, reason_codes "
        "must contain one or more codes from this exact closed vocabulary: "
        f"{reason_text}. Never invent, paraphrase, combine, rename, dot-separate, or suffix "
        "reason codes. Emit no markdown, prose, analysis, authority fields, hashes, commands, "
        "tool calls, or additional keys."
    )


def user_content(prompt: dict[str, Any]) -> str:
    return json.dumps(prompt, sort_keys=True, separators=(",", ":"))


def completion_content(completion: dict[str, Any]) -> str:
    return json.dumps(completion, sort_keys=True, separators=(",", ":"))


def training_messages(
    prompt: dict[str, Any], completion: dict[str, Any], contract: dict[str, Any]
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": specialist_system_prompt(contract)},
        {"role": "user", "content": user_content(prompt)},
        {"role": "assistant", "content": completion_content(completion)},
    ]


def inference_messages(prompt: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": specialist_system_prompt(contract)},
        {"role": "user", "content": user_content(prompt)},
    ]
