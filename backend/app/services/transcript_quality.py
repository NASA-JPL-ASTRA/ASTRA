"""Heuristics to avoid STT hallucinations / silence junk polluting notes and structure notes."""

from __future__ import annotations


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
    return True
