from __future__ import annotations

import json
from typing import Any

import ollama

from intern_agent.prompts import SYSTEM_PROMPT, user_prompt
from intern_agent.scout import seed_search_block
from intern_agent.tools import OUTPUT_DIR, TOOL_SCHEMAS, run_tool

MAX_TOOLS_PER_STEP = 3


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _assistant_payload(message: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": getattr(message, "content", None) or "",
    }
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        serialized = []
        for call in tool_calls:
            fn = call.function
            serialized.append(
                {
                    "type": "function",
                    "function": {
                        "name": fn.name,
                        "arguments": _parse_arguments(fn.arguments),
                    },
                }
            )
        payload["tool_calls"] = serialized
    return payload


def run_search(
    *,
    model: str,
    year: int,
    region: str,
    extra: str | None,
    max_steps: int,
) -> str:
    client = ollama.Client()
    seed = seed_search_block(year)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": user_prompt(year, region, extra) + "\n\n" + seed,
        },
    ]

    for step in range(1, max_steps + 1):
        print(f"\n── step {step}/{max_steps} ──")
        response = client.chat(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            think=False,
        )
        message = response.message
        thinking = getattr(message, "thinking", None)
        if thinking:
            print(f"(model notes) {thinking[:400]}")
        if message.content:
            print(message.content)

        tool_calls = message.tool_calls or []
        messages.append(_assistant_payload(message))

        if not tool_calls:
            findings = OUTPUT_DIR / "spring_week_internships.json"
            if not findings.exists():
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Rewrite using the exact report template from the system prompt. "
                            "Keep only tech Spring Week / Spring Insight programmes. "
                            "Call save_findings first, then output the markdown report. "
                            "Do not write a generic summary."
                        ),
                    }
                )
                continue
            return (message.content or "").strip()

        if len(tool_calls) > MAX_TOOLS_PER_STEP:
            print(
                f"(capping {len(tool_calls)} tool calls to {MAX_TOOLS_PER_STEP} this step)"
            )
            tool_calls = tool_calls[:MAX_TOOLS_PER_STEP]
            messages[-1]["tool_calls"] = messages[-1]["tool_calls"][:MAX_TOOLS_PER_STEP]

        for call in tool_calls:
            name = call.function.name
            args = _parse_arguments(call.function.arguments)
            print(f"→ {name}({json.dumps(args, ensure_ascii=False)[:240]})")
            result = run_tool(name, args)
            preview = result if len(result) < 500 else result[:500] + "…"
            print(preview)
            messages.append({"role": "tool", "content": result})

    messages.append(
        {
            "role": "user",
            "content": "You hit the step limit. Stop calling tools. Write the final report from what you already found.",
        }
    )
    response = client.chat(model=model, messages=messages, think=False)
    print(response.message.content or "")
    return (response.message.content or "").strip()
