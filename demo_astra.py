#!/usr/bin/env python3
"""
JPL ASTRA Demo Script
====================
Demonstrates the Whisper STT API integration flow with ASTRA Backend.

Usage:
  # Upload audio and get ASTRA format result
  python demo_astra.py <audio_file> [--session-id SESSION_ID] [--api-url URL]
  python demo_astra.py sample.wav --session-id ASTRA-mls4d2of

  # Get ASTRA format for existing task only (no re-upload)
  python demo_astra.py --task-id 1 --api-url http://127.0.0.1

Start API first: python start.py
"""
import argparse
import asyncio
import sys
from pathlib import Path

import httpx

DEFAULT_API_URL = "http://127.0.0.1"
CREATE_URL = "/api/whisper/tasks/create"
RESULT_URL = "/api/whisper/tasks/result"
POLL_INTERVAL = 2
MAX_POLLS = 60


async def create_task(api_url: str, file_path: Path, session_id: str) -> dict:
    """Upload audio file to create transcription task. platform field is used to pass session_id."""
    url = f"{api_url.rstrip('/')}{CREATE_URL}"
    # Set content-type based on file extension
    suffix = file_path.suffix.lower()
    content_type = "audio/wav" if suffix == ".wav" else "audio/mpeg" if suffix == ".mp3" else "video/mp4"
    params = {"task_type": "transcribe", "priority": "high", "platform": session_id, "language": "en"}
    with open(file_path, "rb") as f:
        files = {"file_upload": (file_path.name, f, content_type)}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, params=params, files=files)
    resp.raise_for_status()
    return resp.json()


async def get_result(api_url: str, task_id: int, format_astra: bool = True) -> dict:
    """Get task result. format=astra returns Backend integration format."""
    url = f"{api_url.rstrip('/')}{RESULT_URL}"
    params = {"task_id": task_id}
    if format_astra:
        params["format"] = "astra"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


async def poll_until_complete(api_url: str, task_id: int, session_id: str) -> dict:
    """Poll until task completes, return ASTRA format result."""
    for i in range(MAX_POLLS):
        result = await get_result(api_url, task_id, format_astra=True)
        # For 200, body has code; for 202, body is {"detail": {"code": 202, ...}}
        code = result.get("code") or result.get("detail", {}).get("code") or 0
        if code == 200:
            return result
        if code == 202:
            print(f"  Task processing... ({i * POLL_INTERVAL}s)")
            await asyncio.sleep(POLL_INTERVAL)
        else:
            raise RuntimeError(f"Task error: {result}")
    raise TimeoutError("Task timeout")


async def main():
    parser = argparse.ArgumentParser(description="JPL ASTRA STT Demo")
    parser.add_argument("audio_file", type=Path, nargs="?", help="Audio file path (wav/mp3/mp4 etc.)")
    parser.add_argument("--task-id", type=int, help="Query existing task directly (skip upload)")
    parser.add_argument("--session-id", default="ASTRA-demo", help="Session ID (for Backend association)")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API URL")
    args = parser.parse_args()

    if args.task_id:
        # Get existing task directly
        print("=" * 50)
        print("JPL ASTRA - Get ASTRA format result")
        print("=" * 50)
        print(f"task_id: {args.task_id}")
        try:
            result = await get_result(args.api_url, args.task_id, format_astra=True)
        except httpx.HTTPStatusError as e:
            print(f"Failed to fetch: {e}")
            sys.exit(1)
        if result.get("code") != 200:
            print(f"Task not completed or does not exist: {result}")
            sys.exit(1)
        astra_data = result.get("data", {})
    else:
        if not args.audio_file:
            print("Please provide audio file: python demo_astra.py <audio_file>")
            print("Or use --task-id to query existing task: python demo_astra.py --task-id 1")
            sys.exit(1)
        if not args.audio_file.exists():
            print(f"Error: File does not exist {args.audio_file}")
            sys.exit(1)

        print("=" * 50)
        print("JPL ASTRA - STT Demo")
        print("=" * 50)
        print(f"1. Upload audio: {args.audio_file}")
        print(f"2. Session ID: {args.session_id}")

        try:
            create_resp = await create_task(args.api_url, args.audio_file, args.session_id)
        except httpx.HTTPStatusError as e:
            print(f"Failed to create task: {e}")
            sys.exit(1)

        data = create_resp.get("data", {})
        task_id = data.get("id")
        if not task_id:
            print(f"Unexpected response: {create_resp}")
            sys.exit(1)

        print(f"3. Task created, task_id={task_id}")
        print("4. Waiting for transcription to complete...")

        try:
            result = await poll_until_complete(args.api_url, task_id, args.session_id)
        except (TimeoutError, RuntimeError) as e:
            print(f"Error: {e}")
            sys.exit(1)

        astra_data = result.get("data", {})
    print("\n" + "=" * 50)
    print("ASTRA format output (for Backend integration)")
    print("=" * 50)
    print(f"session_id: {astra_data.get('session_id')}")
    print(f"task_id: {astra_data.get('task_id')}")
    print(f"language: {astra_data.get('language')}")
    print(f"timestamp: {astra_data.get('timestamp')}")
    print(f"\ntranscript:\n  {astra_data.get('transcript', '')}")
    print(f"\nsegments (with timestamps):")
    for seg in astra_data.get("segments", [])[:10]:
        print(f"  [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
    if len(astra_data.get("segments", [])) > 10:
        print(f"  ... total {len(astra_data['segments'])} segments")
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
