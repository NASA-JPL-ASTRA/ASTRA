"""Heuristics to avoid STT hallucinations / silence junk polluting notes and structure notes."""

from __future__ import annotations

import os
import re

# CJK, Japanese kana, Korean, Cyrillic, Arabic — operational English sessions should not contain these.
_NON_ENGLISH_SCRIPTS = re.compile(
    r"[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff\uac00-\ud7af\u0400-\u04ff\u0600-\u06ff]"
)
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_LETTER_RE = re.compile(r"[A-Za-z]")
_REPEATED_CHAR_RE = re.compile(r"([A-Za-z])\1{4,}")


def english_gate_enabled() -> bool:
    flag = os.getenv("STT_ENGLISH_ONLY_GATE", "true").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def transcript_is_english(text: str) -> bool:
    """
    Return True when transcript looks like English operational speech.
    Used to drop non-English STT output before UI/notes (not a fixed-string blocklist).
    """
    t = (text or "").strip()
    if len(t) < 2:
        return False
    if not any(ch.isalnum() for ch in t):
        return False
    if _NON_ENGLISH_SCRIPTS.search(t):
        return False
    letters = [ch for ch in t if ch.isalpha()]
    if len(letters) < 2:
        return False
    latin = sum(1 for ch in letters if ch.isascii())
    return (latin / len(letters)) >= 0.85


def transcript_is_plausible_speech(text: str) -> bool:
    """
    Reject obvious STT hallucination junk before it reaches UI / notes.

    This intentionally uses shape-based checks rather than a fixed phrase
    blocklist so it catches non-speech, gibberish, repeated tokens, and symbol
    noise without hard-coding demo-specific text.
    """
    t = (text or "").strip()
    if len(t) < 2:
        return False
    if not any(ch.isalnum() for ch in t):
        return False
    if _REPEATED_CHAR_RE.search(t):
        return False

    words = [word.lower() for word in _WORD_RE.findall(t)]
    if not words:
        return False

    letters = _LETTER_RE.findall(t)
    alpha_ratio = len(letters) / max(1, len([ch for ch in t if not ch.isspace()]))
    if alpha_ratio < 0.45:
        return False

    # Single-token outputs are allowed for operational commands, but only when
    # they look like a real word rather than a tiny noise artifact.
    if len(words) == 1:
        word = words[0]
        return len(word) >= 3 and any(ch.isalpha() for ch in word)

    unique_words = set(words)
    if len(words) >= 4 and len(unique_words) <= 2:
        return False

    most_common_ratio = max(words.count(word) for word in unique_words) / len(words)
    if len(words) >= 5 and most_common_ratio > 0.55:
        return False

    return True


def transcript_qualifies_for_notes(text: str) -> bool:
    """
    Return False for empty, punctuation-only, or single-character noise.
    Does not try to classify semantic hallucinations (handled upstream by silence gating).
    """
    t = (text or "").strip()
    if len(t) < 2:
        return False
    if not any(ch.isalnum() for ch in t):
        return False
    if english_gate_enabled() and not transcript_is_english(t):
        return False
    if not transcript_is_plausible_speech(t):
        return False
    return True
