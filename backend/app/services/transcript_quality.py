"""Heuristics to avoid STT hallucinations / silence junk polluting notes and structure notes."""

from __future__ import annotations

import os
import re

# CJK, Japanese kana, Korean, Cyrillic, Arabic — operational English sessions should not contain these.
_NON_ENGLISH_SCRIPTS = re.compile(
    r"[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff\uac00-\ud7af\u0400-\u04ff\u0600-\u06ff]"
)


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
    return True
