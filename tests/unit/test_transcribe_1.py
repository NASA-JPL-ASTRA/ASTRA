# pip install httpx
import httpx
# To run the async function
import asyncio

url = "http://127.0.0.1/api/whisper/tasks/create"
file_url = "https://www2.cs.uic.edu/~i101/SoundFiles/preamble.wav"

# Define query parameters as a dictionary
params = {
    "task_type": "transcribe",
    "priority": "normal",
    "temperature": "0.8,1.0",
    "compression_ratio_threshold": "1.8",
    "no_speech_threshold": "0.6",
    "condition_on_previous_text": "true",
    "word_timestamps": "false",
    "prepend_punctuations": '"\'“¿([{-',
    "append_punctuations": '"\'.。,!！?？:：”)]}、',
    "clip_timestamps": "0.0",
    "file_url": file_url
}

# For an empty file upload field
# files = {"file": open("/path/to/audio.mp3", "rb")}
files = None


async def make_request():
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=None, params=params, files=files)
        print(response.json())


asyncio.run(make_request())
