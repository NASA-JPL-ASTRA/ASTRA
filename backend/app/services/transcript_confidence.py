import io
import math
import re
import struct
import wave
from dataclasses import dataclass
from typing import Any, Iterable, Optional


_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_HALLUCINATION_PHRASES = (
    "thank you for watching",
    "don't forget to subscribe",
    "like and subscribe",
    "字幕",
)


@dataclass(frozen=True)
class AudioQualityStats:
    duration_seconds: float
    rms: float
    peak: float
    snr_db: float
    clipping_ratio: float


def clamp_confidence(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def extract_logprobs(raw: Any) -> list[float]:
    """Collect logprob-like values from OpenAI event payloads when present."""
    values: list[float] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"logprob", "avg_logprob"} and isinstance(value, (int, float)):
                    # Log probabilities are <= 0. Ignore probability-like scores here.
                    if value <= 0 and math.isfinite(value):
                        values.append(float(value))
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(raw)
    return values


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[idx]


def _score_between(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _pcm16_samples(file_bytes: bytes) -> tuple[list[float], float] | None:
    try:
        with wave.open(io.BytesIO(file_bytes), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
            raw = wav.readframes(frames)
    except (wave.Error, EOFError):
        return None

    if sample_width != 2 or sample_rate <= 0 or channels <= 0:
        return None

    ints = [sample[0] for sample in struct.iter_unpack("<h", raw)]
    if channels > 1:
        mono: list[float] = []
        for i in range(0, len(ints), channels):
            frame = ints[i : i + channels]
            if frame:
                mono.append(sum(frame) / (len(frame) * 32768.0))
        samples = mono
    else:
        samples = [value / 32768.0 for value in ints]

    duration = len(samples) / sample_rate
    return samples, duration


def audio_quality_stats(
    file_bytes: bytes,
    fallback_duration_seconds: Optional[float] = None,
) -> AudioQualityStats | None:
    parsed = _pcm16_samples(file_bytes)
    if not parsed:
        return None

    samples, parsed_duration = parsed
    if not samples:
        return None

    duration = parsed_duration or fallback_duration_seconds or 0.0
    sum_sq = 0.0
    peak = 0.0
    clipped = 0
    frame_size = max(1, int(len(samples) / max(1, round(duration / 0.02))))
    frame_rms: list[float] = []

    for i in range(0, len(samples), frame_size):
        frame = samples[i : i + frame_size]
        if not frame:
            continue
        frame_sum_sq = 0.0
        for sample in frame:
            abs_sample = abs(sample)
            peak = max(peak, abs_sample)
            if abs_sample >= 0.98:
                clipped += 1
            sum_sq += sample * sample
            frame_sum_sq += sample * sample
        frame_rms.append(math.sqrt(frame_sum_sq / len(frame)))

    rms = math.sqrt(sum_sq / len(samples))
    noise_floor = max(_percentile(frame_rms, 0.1), 1e-5)
    speech_level = max(_percentile(frame_rms, 0.9), noise_floor)
    snr_db = 20 * math.log10(speech_level / noise_floor)
    clipping_ratio = clipped / len(samples)

    return AudioQualityStats(
        duration_seconds=duration,
        rms=rms,
        peak=peak,
        snr_db=snr_db,
        clipping_ratio=clipping_ratio,
    )


def _audio_score(stats: AudioQualityStats | None) -> float:
    if stats is None:
        return 0.65

    snr_score = _score_between(stats.snr_db, 6.0, 22.0)
    if stats.rms < 0.006:
        level_score = 0.25
    elif stats.rms < 0.015:
        level_score = 0.6
    elif stats.rms < 0.18:
        level_score = 0.95
    elif stats.rms < 0.35:
        level_score = 0.75
    else:
        level_score = 0.5

    clipping_penalty = min(0.35, stats.clipping_ratio * 18)
    return max(0.0, min(1.0, 0.65 * snr_score + 0.35 * level_score - clipping_penalty))


def _duration_score(duration_seconds: Optional[float]) -> float:
    if duration_seconds is None or duration_seconds <= 0:
        return 0.65
    if duration_seconds < 0.25:
        return 0.25
    if duration_seconds < 0.5:
        return 0.55
    if duration_seconds <= 10:
        return 0.95
    if duration_seconds <= 15:
        return 0.75
    return 0.6


def _text_score(transcript: str, duration_seconds: Optional[float]) -> float:
    text = transcript.strip()
    if not text:
        return 0.0

    words = _WORD_RE.findall(text.lower())
    if not words:
        return 0.25

    score = 0.88
    if len(text) < 4 or len(words) == 1:
        score -= 0.25

    if duration_seconds and duration_seconds > 0:
        chars_per_second = len(text) / duration_seconds
        if chars_per_second < 1.5:
            score -= 0.15
        elif chars_per_second > 32:
            score -= 0.25

    most_common_ratio = max(words.count(word) for word in set(words)) / len(words)
    if len(words) >= 4 and most_common_ratio > 0.45:
        score -= 0.25

    lowered = text.lower()
    if any(phrase in lowered for phrase in _HALLUCINATION_PHRASES):
        score -= 0.35

    return max(0.0, min(1.0, score))


def _logprob_confidence(logprobs: Iterable[float]) -> Optional[float]:
    probs = [math.exp(max(-10.0, min(0.0, value))) for value in logprobs]
    if not probs:
        return None
    return max(0.0, min(1.0, sum(probs) / len(probs)))


def estimate_transcript_confidence(
    *,
    transcript: str,
    file_bytes: bytes | None = None,
    duration_seconds: Optional[float] = None,
    openai_logprobs: Iterable[float] = (),
) -> float:
    stats = audio_quality_stats(file_bytes or b"", duration_seconds) if file_bytes else None
    resolved_duration = (
        stats.duration_seconds if stats and stats.duration_seconds > 0 else duration_seconds
    )
    audio_score = _audio_score(stats)
    duration_score = _duration_score(resolved_duration)
    text_score = _text_score(transcript, resolved_duration)
    model_score = _logprob_confidence(openai_logprobs)

    if model_score is not None:
        confidence = 0.6 * model_score + 0.25 * audio_score + 0.15 * text_score
    else:
        confidence = 0.45 * audio_score + 0.2 * duration_score + 0.35 * text_score

    return clamp_confidence(confidence)
