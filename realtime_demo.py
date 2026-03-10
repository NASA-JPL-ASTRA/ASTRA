#!/usr/bin/env python3
"""
JPL ASTRA - Real-time STT Quick Demo
====================================
Quasi-real-time speech-to-text using VAD (pause-based segmentation) + Whisper.

Flow:
  1. Microphone records continuously
  2. VAD detects speech pause (configurable, default ~1.5s silence = end of utterance)
  3. Audio chunk saved as WAV
  4. Upload to Backend (integrated) or Whisper API (standalone) -> get transcript
  5. Loop

Modes:
  - Integrated (--backend-url): Upload to ASTRA Backend -> Notes, WebSocket, Frontend
  - Standalone (--api-url): Direct to Whisper API, print only (original behavior)

Requirements:
  pip install sounddevice webrtcvad numpy httpx

Usage:
  # Integrated: Backend + Whisper (notes go to session, Frontend can show)
  python realtime_demo.py --backend-url http://127.0.0.1:8000

  # Standalone: Direct to Whisper API
  python realtime_demo.py --api-url http://127.0.0.1:8001

  python realtime_demo.py --backend-url http://localhost:8000 --debug
"""
import argparse
import sys
import tempfile
import time
import wave
from pathlib import Path

import httpx
import numpy as np
import sounddevice as sd
import webrtcvad

# API URLs
DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
CREATE_URL = "/api/whisper/tasks/create"
RESULT_URL = "/api/whisper/tasks/result"
BACKEND_SESSIONS_URL = "/api/sessions"
BACKEND_STT_UPLOAD_URL = "/api/sessions/{sid}/stt/upload"
BACKEND_STT_TASK_URL = "/api/sessions/{sid}/stt/tasks/{tid}"
POLL_INTERVAL = 0.5
MAX_POLLS = 120

# Audio config (webrtcvad requires 8k/16k/32k, 16-bit)
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 30  # webrtcvad standard
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

# Timing: NOT from Backend README (it says "configurable threshold" but no values).
# Chosen as reasonable defaults - you can tune via --silence-sec and --min-speech-sec:
# - 1.5s silence: common in voice assistants; shorter = more chunks, longer = wait more
# - 0.45s min: avoid noise bursts; shorter = more false triggers, longer = miss quick words
DEFAULT_SILENCE_SEC = 1.5
DEFAULT_MIN_SPEECH_SEC = 0.45

# Hallucination filter (confidence-based)
try:
    from app.utils.hallucination_filter import is_likely_hallucination
except ImportError:
    # Fallback when run outside project
    def is_likely_hallucination(transcript: str, segments: list, debug: bool = False) -> tuple[bool, str | None]:
        for seg in segments or []:
            if seg.get("no_speech_prob", 0) > 0.4:
                return True, f"no_speech_prob {seg.get('no_speech_prob')} > 0.4"
            if (seg.get("avg_logprob") or 0) < -0.5:
                return True, f"avg_logprob {seg.get('avg_logprob')} < -0.5"
        t = transcript.strip().lower().rstrip(".,!? ")
        if len(t) <= 25 and t in {"thank you", "thanks", "okay", "ok", "bye", "you", "the", "end", "um", "uh"}:
            return True, f"phrase fallback: '{t}'"
        return False, None


# ── Backend (integrated) ──

def create_session_sync(backend_url: str) -> str:
    """Create ASTRA Backend session, return session_id."""
    url = f"{backend_url.rstrip('/')}{BACKEND_SESSIONS_URL}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, json={"name": "Realtime Demo Session", "description": "VAD-triggered transcription"})
    resp.raise_for_status()
    data = resp.json()
    return data["id"]


def upload_to_backend_sync(backend_url: str, session_id: str, wav_path: Path, duration_sec: float) -> dict | None:
    """Upload WAV to Backend STT endpoint. Returns STT task dict or None on failure."""
    url = f"{backend_url.rstrip('/')}{BACKEND_STT_UPLOAD_URL.format(sid=session_id)}"
    with open(wav_path, "rb") as f:
        files = {"file": (wav_path.name, f, "audio/wav")}
        data = {
            "audio_chunk_id": f"chunk_{int(time.time() * 1000)}",
            "duration_seconds": duration_sec,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, files=files, data=data)
    if resp.status_code != 200:
        return None
    return resp.json()


def poll_backend_stt_task(backend_url: str, session_id: str, task_id: str) -> tuple[str | None, str | None]:
    """Poll Backend for STT task result. Returns (transcript, error)."""
    url = f"{backend_url.rstrip('/')}{BACKEND_STT_TASK_URL.format(sid=session_id, tid=task_id)}"
    for _ in range(MAX_POLLS):
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return None, resp.text or "Request failed"
        task = resp.json()
        status = task.get("status", "")
        if status == "done":
            return task.get("transcript") or "", None
        if status == "failed":
            return None, task.get("error") or "Transcription failed"
        time.sleep(POLL_INTERVAL)
    return None, "Timeout waiting for result"


# ── Whisper API (standalone) ──

def create_task_sync(api_url: str, wav_path: Path) -> dict:
    """Upload WAV to Whisper API, return create response."""
    url = f"{api_url.rstrip('/')}{CREATE_URL}"
    params = {
        "task_type": "transcribe",
        "priority": "high",
        "language": "en",                      # English only
        "no_speech_threshold": "0.8",           # Higher = less likely to transcribe silence/noise
        "condition_on_previous_text": "false",  # Reduces hallucinations on short chunks
        "hallucination_silence_threshold": "0.5",  # Suppress hallucinations after silence
    }
    with open(wav_path, "rb") as f:
        files = {"file_upload": (wav_path.name, f, "audio/wav")}
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, params=params, files=files)
    resp.raise_for_status()
    return resp.json()


def get_result_sync(api_url: str, task_id: int, full_format: bool = True) -> dict:
    """Poll Whisper API for task result. full_format=True gets segments with avg_logprob/no_speech_prob."""
    url = f"{api_url.rstrip('/')}{RESULT_URL}"
    params = {"task_id": task_id}
    if not full_format:
        params["format"] = "astra"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def poll_until_done_sync(api_url: str, task_id: int) -> tuple[str, list]:
    """
    Poll until transcription done. Returns (transcript, segments).
    segments contain avg_logprob, no_speech_prob for confidence-based filtering.
    """
    for _ in range(MAX_POLLS):
        result = get_result_sync(api_url, task_id, full_format=True)
        code = result.get("code") or result.get("detail", {}).get("code") or 0
        if code == 200:
            data = result.get("data", {})
            task_result = data.get("result") or {}
            transcript = task_result.get("text", "")
            segments = task_result.get("segments", [])
            return transcript, segments
        if code != 202:
            raise RuntimeError(f"Task error: {result}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError("Transcription timeout")


def save_wav(frames: list, path: Path) -> None:
    """Save list of raw PCM frames (bytes) to WAV file."""
    raw = b"".join(frames)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(raw)


def run_realtime_demo(
    api_url: str | None,
    backend_url: str | None,
    silence_sec: float,
    min_speech_sec: float,
    debug: bool = False,
) -> None:
    """Main loop: record -> VAD -> transcribe -> print."""
    vad = webrtcvad.Vad(2)  # Aggressiveness 0-3, 2 is moderate

    silence_threshold_frames = int(silence_sec * 1000 / FRAME_DURATION_MS)
    min_speech_frames = int(min_speech_sec * 1000 / FRAME_DURATION_MS)

    session_id: str | None = None
    if backend_url:
        try:
            session_id = create_session_sync(backend_url)
            print(f"[Backend] Session created: {session_id}")
        except Exception as e:
            print(f"[Error] Failed to create Backend session: {e}")
            print("  Make sure ASTRA Backend is running (uvicorn app.main:app --port 8000)")
            sys.exit(1)

    print("=" * 50)
    print("JPL ASTRA - Real-time STT Demo")
    print("=" * 50)
    mode = "Integrated (Backend)" if backend_url else "Standalone (Whisper)"
    print(f"Mode: {mode}")
    print(f"URL: {backend_url or api_url}")
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print(f"Silence to trigger: {silence_sec}s | Min speech: {min_speech_sec}s")
    print("Press Ctrl+C to quit.")
    print("=" * 50)

    speech_frames = []
    silence_frames = 0
    in_speech = False

    def audio_callback(indata, frames, time_info, status):
        nonlocal speech_frames, silence_frames, in_speech
        if status:
            print(f"[Audio] {status}", file=sys.stderr)
        # indata is (frames, channels), float32 in [-1, 1]
        # Convert to int16 for webrtcvad
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        raw = pcm.tobytes()
        # Process in 30ms chunks
        for i in range(0, len(raw), FRAME_SIZE * 2):
            chunk = raw[i : i + FRAME_SIZE * 2]
            if len(chunk) < FRAME_SIZE * 2:
                break
            is_speech = vad.is_speech(chunk, SAMPLE_RATE)
            if is_speech:
                speech_frames.append(chunk)
                silence_frames = 0
                in_speech = True
            elif in_speech:
                speech_frames.append(chunk)
                silence_frames += 1

    def process_utterance():
        nonlocal speech_frames, silence_frames, in_speech
        if len(speech_frames) < min_speech_frames:
            return
        frames_to_process = list(speech_frames)
        speech_frames.clear()
        silence_frames = 0
        in_speech = False

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            save_wav(frames_to_process, tmp_path)
            duration = len(frames_to_process) * FRAME_DURATION_MS / 1000
            print(f"\n  [Processing {duration:.1f}s of audio...]")

            if backend_url and session_id:
                # Integrated: upload to Backend, poll for result (Backend handles Whisper + filtering)
                task = upload_to_backend_sync(backend_url, session_id, tmp_path, duration)
                if not task:
                    print("  [Error] Backend upload failed")
                    return
                tid = task.get("id")
                if not tid:
                    print("  [Error] No task id from Backend")
                    return
                transcript, err = poll_backend_stt_task(backend_url, session_id, tid)
                if err:
                    print(f"  >>> [Error] {err}")
                elif transcript:
                    print(f"  >>> {transcript}")
                else:
                    print("  >>> (no speech detected)")
            else:
                # Standalone: direct to Whisper API
                create_resp = create_task_sync(api_url or DEFAULT_API_URL, tmp_path)
                task_id = create_resp.get("data", {}).get("id")
                if not task_id:
                    print("  [Error] No task_id in response")
                    return
                transcript, segments = poll_until_done_sync(api_url or DEFAULT_API_URL, task_id)
                if transcript.strip():
                    filtered, reason = is_likely_hallucination(transcript, segments, debug=debug)
                    if filtered:
                        reason_str = f" [{reason}]" if (debug and reason) else ""
                        print(f"  >>> (noise / no actual content){reason_str}")
                    else:
                        print(f"  >>> {transcript}")
                else:
                    print("  >>> (no speech detected)")
        except Exception as e:
            print(f"  [Error] {e}")
        finally:
            tmp_path.unlink(missing_ok=True)

    # Stream: process when silence threshold reached
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=FRAME_SIZE,
            callback=audio_callback,
        ):
            while True:
                sd.sleep(100)
                if in_speech and silence_frames >= silence_threshold_frames:
                    process_utterance()
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Real-time STT Quick Demo")
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--backend-url",
        default=None,
        help="ASTRA Backend URL (integrated mode: notes, WebSocket, Frontend). Example: http://127.0.0.1:8000",
    )
    g.add_argument(
        "--api-url",
        default=None,
        help="Whisper API URL (standalone mode, direct to Whisper). Example: http://127.0.0.1:8001",
    )
    parser.add_argument(
        "--silence-sec", type=float, default=DEFAULT_SILENCE_SEC,
        help="Seconds of silence to trigger transcription (default: 1.5)"
    )
    parser.add_argument(
        "--min-speech-sec", type=float, default=DEFAULT_MIN_SPEECH_SEC,
        help="Min speech duration to process, shorter chunks ignored (default: 0.45)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Print confidence values when filtering (standalone mode only)"
    )
    args = parser.parse_args()

    backend_url = args.backend_url
    api_url = args.api_url
    if not backend_url and not api_url:
        # Default: prefer integrated mode if Backend might be on 8000
        backend_url = DEFAULT_BACKEND_URL

    # Check dependencies
    try:
        import sounddevice
        import webrtcvad
        import numpy
    except ImportError:
        print("Missing dependency. Install with:")
        print("  pip install sounddevice webrtcvad numpy httpx")
        sys.exit(1)

    run_realtime_demo(
        api_url=api_url,
        backend_url=backend_url,
        silence_sec=args.silence_sec,
        min_speech_sec=args.min_speech_sec,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
