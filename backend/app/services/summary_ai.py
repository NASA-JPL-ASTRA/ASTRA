"""
Note summary assistant helpers.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.services.structure_note_engine import utc_iso_timestamp


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-5-mini")


def transcript_text(notes: list[dict]) -> str:
    lines: list[str] = []
    for note in sorted(notes, key=lambda item: item["timestamp"]):
        speaker = note.get("speaker") or "Unknown"
        timestamp = note["timestamp"]
        lines.append(f"[{timestamp}] {speaker}: {note['content']}")
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


async def _call_openai(instructions: str, input_text: str, model: str | None = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    payload = {
        "model": model or DEFAULT_SUMMARY_MODEL,
        "instructions": instructions,
        "input": input_text,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    texts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(content["text"])
    if texts:
        return "\n".join(texts).strip()

    raise RuntimeError("OpenAI response did not include text output")


def _local_rewrite(summary: str, prompt: str) -> str:
    body = summary.strip() or "No summary content is available yet."
    return "\n".join([
        body,
        "",
        "AI edit note",
        "",
        f"- Requested change: {prompt.strip()}",
        f"- Drafted locally at {utc_iso_timestamp()} because the AI service is not configured.",
    ])


async def chat_about_summary(
    *,
    notes: list[dict],
    prompt: str,
    title: str | None,
    summary: str | None,
    manual_summary: str | None,
    model: str | None,
    messages: list[dict],
) -> dict[str, str | None]:
    transcript = transcript_text(notes)
    current_summary = summary or "No summary content is available yet."
    operator_manual_summary = (manual_summary or summary or "").strip()

    instructions = (
        "You are the ASTRA note summary assistant. Improve the note summary using "
        "the transcript as ground truth and the operator-written manual summary as "
        "high-priority context. Do not invent unsupported facts. Return a "
        "JSON object with keys: message (string) and updated_summary (string or null). "
        "Set updated_summary when the user asks for a rewrite, formatting change, "
        "translation, shorter version, action extraction, or any summary replacement. "
        "The updated_summary must be Markdown suitable for the Test summary block. "
        "When producing updated_summary, preserve and integrate the operator manual "
        "summary. Do not drop manual notes just because they are not present in the "
        "transcript; treat them as operator-authored observations unless they directly "
        "contradict transcript evidence. If Markdown image references or placeholders "
        "appear in the manual summary, keep them intact."
    )
    history = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')}"
        for item in messages[-8:]
    )
    input_text = "\n\n".join([
        f"Title: {title or 'Meeting Summary'}",
        f"Current summary:\n{current_summary}",
        f"Operator manual summary to preserve and summarize:\n{operator_manual_summary or 'No manual summary provided.'}",
        f"Transcript:\n{transcript or 'No transcript available.'}",
        f"Recent chat:\n{history or 'No previous messages.'}",
        f"User request:\n{prompt}",
    ])

    try:
        raw = await _call_openai(instructions, input_text, model)
        parsed = _extract_json_object(raw)
        if parsed:
            return {
                "message": str(parsed.get("message") or "").strip() or "Preview draft ready.",
                "updated_summary": (
                    str(parsed["updated_summary"]).strip()
                    if parsed.get("updated_summary")
                    else None
                ),
            }
        return {"message": raw, "updated_summary": None}
    except Exception as exc:
        updated = _local_rewrite(current_summary, prompt)
        return {
            "message": (
                "I prepared a local preview because the AI service is not available. "
                f"Backend detail: {exc}"
            ),
            "updated_summary": updated,
        }
