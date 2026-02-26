#!/usr/bin/env python3
"""
JPL ASTRA - Real-time STT Quick Demo
====================================
Quasi-real-time speech-to-text using VAD (pause-based segmentation) + Whisper API.

Flow:
  1. Microphone records continuously
  2. VAD detects speech pause (configurable, default ~1.5s silence = end of utterance)
  3. Audio chunk saved as WAV
  4. POST to Whisper API -> poll for result -> print transcript
  5. Loop

Requirements:
  pip install sounddevice webrtcvad numpy

Usage:
  python realtime_demo.py [--api-url URL] [--silence-sec 1.5] [--min-speech-sec 0.45] [--debug]
  python realtime_demo.py --api-url http://127.0.0.1:8000 --debug   # Print confidence values

Start Whisper API first: python start.py (or PORT=8000 python start.py)
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

# Whisper API
DEFAULT_API_URL = "http://127.0.0.1:8000"
CREATE_URL = "/api/whisper/tasks/create"
RESULT_URL = "/api/whisper/tasks/result"
POLL_INTERVAL = 1.5
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

# Use shared hallucination filter (same logic as task_processor for consistency)
try:
    from app.utils.hallucination_filter import is_likely_hallucination
except ImportError:
    # Fallback when run outside project
    def is_likely_hallucination(transcript: str, segments: list, debug: bool = False) -> bool:
        for seg in segments or []:
            if seg.get("no_speech_prob", 0) > 0.4 or (seg.get("avg_logprob") or 0) < -0.5:
                return True
        t = transcript.strip().lower().rstrip(".,!? ")
        return len(t) <= 25 and t in {"thank you", "thanks", "okay", "ok", "bye", "you", "the", "end", "um", "uh"}


def create_task_sync(api_url: str, wav_path: Path) -> dict:
    """Upload WAV to Whisper API, return create response."""
    url = f"{api_url.rstrip('/')}{CREATE_URL}"
    params = {
        "task_type": "transcribe",
        "priority": "high",
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


def run_realtime_demo(api_url: str, silence_sec: float, min_speech_sec: float, debug: bool = False) -> None:
    """Main loop: record -> VAD -> transcribe -> print."""
    vad = webrtcvad.Vad(2)  # Aggressiveness 0-3, 2 is moderate

    silence_threshold_frames = int(silence_sec * 1000 / FRAME_DURATION_MS)
    min_speech_frames = int(min_speech_sec * 1000 / FRAME_DURATION_MS)

    print("=" * 50)
    print("JPL ASTRA - Real-time STT Demo")
    print("=" * 50)
    print(f"API: {api_url}")
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
            create_resp = create_task_sync(api_url, tmp_path)
            task_id = create_resp.get("data", {}).get("id")
            if not task_id:
                print("  [Error] No task_id in response")
                return
            transcript, segments = poll_until_done_sync(api_url, task_id)
            if transcript.strip():
                if is_likely_hallucination(transcript, segments, debug=debug):
                    print("  >>> (noise / no actual content)")
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
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Whisper API URL")
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
        help="Print confidence values (no_speech_prob, avg_logprob) when filtering"
    )
    args = parser.parse_args()

    # Check dependencies
    try:
        import sounddevice
        import webrtcvad
        import numpy
    except ImportError:
        print("Missing dependency. Install with:")
        print("  pip install sounddevice webrtcvad numpy")
        sys.exit(1)

    run_realtime_demo(args.api_url, args.silence_sec, args.min_speech_sec, debug=args.debug)


if __name__ == "__main__":
    main()
