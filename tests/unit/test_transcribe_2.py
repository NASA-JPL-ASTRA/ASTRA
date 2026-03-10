# pip install httpx
import httpx

url = "http://127.0.0.1/api/tiktok/video_task"
tiktok_url = "https://www.tiktok.com/@taylorswift/video/7359655005701311786"

# Define the form data as a dictionary
data = {
    "url": tiktok_url,
    "priority": "normal",
    "prepend_punctuations": '"\'“¿([{-',
    "no_speech_threshold": "0.6",
    "clip_timestamps": "0",
    "word_timestamps": "false",
    "platform": "tiktok",
    "temperature": "0.8,1.0",
    "task_type": "transcribe",
    "callback_url": "",
    "hallucination_silence_threshold": "0",
    "language": "",
    "condition_on_previous_text": "true",
    "compression_ratio_threshold": "1.8",
    "append_punctuations": '"\'.。,!！?？:：”)]}、',
    "initial_prompt": ""
}


async def make_request():
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        print(response.json())


if __name__ == "__main__":
    # To run the async function
    import asyncio
    # Run the async function
    asyncio.run(make_request())
