# ==============================================================================
# Hallucination filter for Whisper transcription results.
# Used by task_processor (server-side) and realtime_demo (client-side).
# ==============================================================================

# Confidence-based: no_speech_prob, avg_logprob from faster-whisper segments.
NO_SPEECH_THRESHOLD = 0.4   # Segment with no_speech_prob > this → likely silence/noise
LOGPROB_THRESHOLD = -0.5    # Segment with avg_logprob < this → low confidence

# Fallback: for very short transcripts only.
SHORT_TRANSCRIPT_MAX_LEN = 25
HALLUCINATION_PHRASES_SHORT = frozenset({
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "subscribe", "please subscribe", "thanks for listening",
    "bye", "goodbye", "see you", "all right", "okay", "ok",
    "you", "the", "end", "um", "uh",
    "gracias", "merci", "danke", "谢谢", "ありがとう", "감사합니다",
})


def is_likely_hallucination(transcript: str, segments: list, debug: bool = False) -> tuple[bool, str | None]:
    """
    Filter hallucinations using: (1) model confidence, (2) short-transcript phrase fallback.
    Returns (True, reason) if filtered, (False, None) otherwise.
    """
    # 1. Confidence-based
    for i, seg in enumerate(segments or []):
        no_speech = seg.get("no_speech_prob")
        avg_logprob = seg.get("avg_logprob")
        if debug and (no_speech is not None or avg_logprob is not None):
            print(f"    [debug] seg[{i}] no_speech_prob={no_speech}, avg_logprob={avg_logprob}")
        if no_speech is not None and no_speech > NO_SPEECH_THRESHOLD:
            reason = f"no_speech_prob {no_speech:.4f} > {NO_SPEECH_THRESHOLD}"
            if debug:
                print(f"    [debug] filtered: {reason}")
            return True, reason
        if avg_logprob is not None and avg_logprob < LOGPROB_THRESHOLD:
            reason = f"avg_logprob {avg_logprob:.4f} < {LOGPROB_THRESHOLD}"
            if debug:
                print(f"    [debug] filtered: {reason}")
            return True, reason

    if debug and segments and not any(seg.get("no_speech_prob") is not None or seg.get("avg_logprob") is not None for seg in segments):
        print("    [debug] segments have no no_speech_prob/avg_logprob (using phrase fallback only)")

    # 2. Fallback: very short transcript matching known hallucination phrases
    t = transcript.strip().lower().rstrip(".,!? ")
    if len(t) <= SHORT_TRANSCRIPT_MAX_LEN and t in HALLUCINATION_PHRASES_SHORT:
        reason = f"phrase fallback: '{t}'"
        if debug:
            print(f"    [debug] filtered: {reason}")
        return True, reason

    return False, None
