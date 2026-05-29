import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

SUPPORTED_STT_MODELS = {
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe",
    "gpt-4o-transcribe-diarize",
}

# Models that return token-level log probabilities via `include[]=logprobs`.
# Diarize is intentionally excluded — it does not expose logprobs today.
LOGPROB_CAPABLE_MODELS = {
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe",
}


@dataclass(slots=True)
class OpenAITranscriptionEvent:
    type: str
    delta: str = ""
    text: str = ""
    raw: dict | None = None


class OpenAIStreamingTranscriptionService:
    """Thin wrapper around OpenAI's streamed audio transcription endpoint."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
        # English-only by default (ISO-639-1). Empty env still resolves to "en", not auto-detect.
        lang = (os.getenv("OPENAI_STT_LANGUAGE") or "en").strip().lower()
        self.language = lang if lang not in {"", "auto", "detect"} else "en"
        # Optional vocabulary hint only — must NOT be instructions (they leak into streamed
        # transcript text). Use OPENAI_STT_LANGUAGE=en for language; prompt for names/jargon
        # e.g. "EVR, imu.accel_x, motor stall" not "Transcribe in English only."
        raw_prompt = os.getenv("OPENAI_STT_PROMPT", "").strip()
        self.prompt = raw_prompt if raw_prompt else None
        self.timeout = float(os.getenv("OPENAI_STT_TIMEOUT_SECONDS", "120"))

    def ensure_configured(self) -> None:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

    async def stream_transcription(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        content_type: str,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> AsyncIterator[OpenAITranscriptionEvent]:
        self.ensure_configured()

        resolved_model = model or self.model
        form_data = {
            "model": resolved_model,
            "stream": "true",
        }
        # Ask OpenAI for token log probabilities so confidence can be derived from
        # the model itself rather than only from audio/text heuristics.
        if resolved_model in LOGPROB_CAPABLE_MODELS:
            form_data["include[]"] = "logprobs"
        resolved_language = language or self.language
        resolved_prompt = prompt or self.prompt
        if resolved_language:
            form_data["language"] = resolved_language
        if resolved_prompt:
            form_data["prompt"] = resolved_prompt

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        files = {
            "file": (file_name, file_bytes, content_type),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                data=form_data,
                files=files,
            ) as response:
                if response.status_code >= 400:
                    error_body = await response.aread()
                    raise RuntimeError(
                        f"OpenAI transcription failed ({response.status_code}): "
                        f"{error_body.decode('utf-8', errors='replace')}"
                    )

                data_lines: list[str] = []
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                        continue

                    if line:
                        continue

                    if not data_lines:
                        continue

                    payload = "\n".join(data_lines).strip()
                    data_lines = []

                    if payload == "[DONE]":
                        break

                    event = json.loads(payload)
                    event_type = event.get("type", "")
                    if not event_type:
                        continue

                    yield OpenAITranscriptionEvent(
                        type=event_type,
                        delta=event.get("delta", ""),
                        text=event.get("text", ""),
                        raw=event,
                    )

                if data_lines:
                    payload = "\n".join(data_lines).strip()
                    if payload and payload != "[DONE]":
                        event = json.loads(payload)
                        event_type = event.get("type", "")
                        if event_type:
                            yield OpenAITranscriptionEvent(
                                type=event_type,
                                delta=event.get("delta", ""),
                                text=event.get("text", ""),
                                raw=event,
                            )
