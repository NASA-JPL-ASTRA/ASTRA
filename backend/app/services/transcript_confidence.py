"""Transcript confidence estimation.

Confidence is derived from *measurable* signals, in priority order:

1. **Model log-probabilities** (primary). When the OpenAI transcription API is
   asked for ``include[]=logprobs`` it returns a log-probability per output
   token. The sequence confidence is the geometric mean of the per-token
   probabilities::

       p_token_i = exp(logprob_i)
       model_confidence = (Π p_token_i) ** (1 / N) = exp(mean(logprob_i))

   This is the standard perplexity-based confidence and is fully explainable
   from the model's own output — no hand-written phrase lists.

2. **Audio quality** (calibration). Signal-to-noise ratio, speech level (RMS)
   and clipping are computed directly from the PCM samples.

3. **Text coherence** (calibration). Computed statistics only — degenerate
   repetition ratio and implausible speaking rate. No fixed "hallucination
   phrase" dictionary is used to score confidence.

The final score is a weighted blend; when model log-probabilities are present
they dominate, otherwise we fall back to the signal-based estimate.
"""

import io
import math
import re
import struct
import wave
from dataclasses import dataclass
from typing import Any, Iterable, Optional


_WORD_RE = re.compile(r"[A-Za-z0-9']+")

# Blend weights when model log-probabilities are available.
_W_MODEL = 0.70
_W_AUDIO_WITH_MODEL = 0.20
_W_TEXT_WITH_MODEL = 0.10

# Blend weights for the fallback estimate (no model log-probabilities).
_W_AUDIO_FALLBACK = 0.50
_W_DURATION_FALLBACK = 0.20
_W_TEXT_FALLBACK = 0.30


@dataclass(frozen=True)
class AudioQualityStats:
    duration_seconds: float
    rms: float
    peak: float
    snr_db: float
    clipping_ratio: float


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Explainable confidence result.

    ``value`` is the final 0..1 score. ``source`` records which path produced
    it (``model_logprobs`` vs ``signal_estimate``) so the UI / exports can be
    honest about provenance. Component scores are exposed for debugging.
    """

    value: float
    source: str
    model_score: Optional[float]
    audio_score: float
    text_score: float
    duration_score: float


def clamp_confidence(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def extract_logprobs(raw: Any) -> list[float]:
    """Collect log-probability values from an OpenAI streaming event payload.

    Recursively walks the event JSON and gathers any ``logprob`` / ``avg_logprob``
    numbers. Log probabilities are <= 0; positive values are ignored so we never
    mistake a plain probability for a log-probability.
    """
    values: list[float] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"logprob", "avg_logprob"} and isinstance(value, (int, float)):
                    if value <= 0 and math.isfinite(value):
                        values.append(float(value))
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(raw)
    return values


def model_confidence(logprobs: Iterable[float]) -> Optional[float]:
    """Sequence confidence = geometric mean of per-token probabilities.

    ``exp(mean(logprob))``. Returns ``None`` when no log-probabilities are
    available so the caller can fall back to the signal-based estimate.
    """
    collected = [lp for lp in logprobs if math.isfinite(lp) and lp <= 0]
    if not collected:
        return None
    # Clamp extreme values to keep a single very unlikely token from zeroing
    # the whole utterance.
    mean_logprob = sum(max(-10.0, lp) for lp in collected) / len(collected)
    return clamp_confidence(math.exp(mean_logprob))


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
    frame_size = max(1, int(len(samples) / max(1, round(duration / 0.02)))) if duration else len(samples)
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
    """Map measured audio statistics to a 0..1 quality score.

    Neutral 0.65 when no PCM is available (e.g. compressed upload we cannot
    decode here) so audio neither inflates nor unfairly penalises the result.
    """
    if stats is None:
        return 0.65

    snr_score = _score_between(stats.snr_db, 6.0, 22.0)
    if stats.rms < 0.006:          # near-silent capture
        level_score = 0.25
    elif stats.rms < 0.015:        # very quiet
        level_score = 0.60
    elif stats.rms < 0.18:         # healthy speech level
        level_score = 0.95
    elif stats.rms < 0.35:         # hot
        level_score = 0.75
    else:                          # likely distorted
        level_score = 0.50

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
    return 0.60


def _text_coherence_score(transcript: str, duration_seconds: Optional[float]) -> float:
    """Score transcript plausibility from computed statistics only.

    Uses degenerate-repetition ratio and speaking rate — both derived from the
    text/audio themselves. Deliberately contains no fixed phrase dictionary.
    """
    text = transcript.strip()
    if not text:
        return 0.0

    words = _WORD_RE.findall(text.lower())
    if not words:
        return 0.25

    score = 0.90
    if len(text) < 4 or len(words) == 1:
        score -= 0.20

    if duration_seconds and duration_seconds > 0:
        chars_per_second = len(text) / duration_seconds
        if chars_per_second < 1.5:      # implausibly little text for the audio
            score -= 0.15
        elif chars_per_second > 32:     # implausibly fast → likely garbage
            score -= 0.25

    # Degenerate repetition (a single token dominating) is a strong, model-free
    # signal of a low-quality / looping transcription.
    most_common_ratio = max(words.count(word) for word in set(words)) / len(words)
    if len(words) >= 4 and most_common_ratio > 0.45:
        score -= 0.25

    return max(0.0, min(1.0, score))


def compute_confidence(
    *,
    transcript: str,
    file_bytes: bytes | None = None,
    duration_seconds: Optional[float] = None,
    openai_logprobs: Iterable[float] = (),
) -> ConfidenceBreakdown:
    """Compute an explainable confidence breakdown for a transcript."""
    stats = audio_quality_stats(file_bytes or b"", duration_seconds) if file_bytes else None
    resolved_duration = (
        stats.duration_seconds if stats and stats.duration_seconds > 0 else duration_seconds
    )

    audio_score = _audio_score(stats)
    duration_score = _duration_score(resolved_duration)
    text_score = _text_coherence_score(transcript, resolved_duration)
    model_score = model_confidence(openai_logprobs)

    if model_score is not None:
        value = (
            _W_MODEL * model_score
            + _W_AUDIO_WITH_MODEL * audio_score
            + _W_TEXT_WITH_MODEL * text_score
        )
        source = "model_logprobs"
    else:
        value = (
            _W_AUDIO_FALLBACK * audio_score
            + _W_DURATION_FALLBACK * duration_score
            + _W_TEXT_FALLBACK * text_score
        )
        source = "signal_estimate"

    return ConfidenceBreakdown(
        value=clamp_confidence(value),
        source=source,
        model_score=model_score,
        audio_score=round(audio_score, 3),
        text_score=round(text_score, 3),
        duration_score=round(duration_score, 3),
    )


def estimate_transcript_confidence(
    *,
    transcript: str,
    file_bytes: bytes | None = None,
    duration_seconds: Optional[float] = None,
    openai_logprobs: Iterable[float] = (),
) -> float:
    """Backward-compatible entry point returning just the 0..1 score."""
    return compute_confidence(
        transcript=transcript,
        file_bytes=file_bytes,
        duration_seconds=duration_seconds,
        openai_logprobs=openai_logprobs,
    ).value
