import httpx
import asyncio


class WhisperTaskClient:
    def __init__(self, url: str = "http://127.0.0.1/api/whisper/tasks/create"):
        self.url = url
        self.default_form_data = {
            "priority": "normal",
            "prepend_punctuations": "'“¿([{-",
            "no_speech_threshold": "0.6",
            "clip_timestamps": "0",
            "word_timestamps": "false",
            "temperature": "0.8,1.0",
            "task_type": "transcribe",
            "callback_url": "",
            "hallucination_silence_threshold": "0",
            "language": "",
            "condition_on_previous_text": "true",
            "compression_ratio_threshold": "1.8",
            "append_punctuations": "。。，，!！?？:：”)]}、",
            "initial_prompt": ""
        }

    async def create_task(self, file_path: str, form_data: dict = None):
        # Merge custom form data with default data
        form_data = {**self.default_form_data, **(form_data or {})}

        # Include the file in the form data
        files = {"file": (file_path.split("/")[-1], open(file_path, "rb"), "video/mp4")}

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers={"accept": "application/json"}, data=form_data, files=files)

        # Print the response
        print(response.status_code)
        print(response.json())

    async def send_single_requests(self, file_path: str, count: int, form_data: dict = None):
        """Sends requests one by one sequentially."""
        for _ in range(count):
            await self.create_task(file_path, form_data)

    async def send_concurrent_requests(self, file_path: str, count: int, form_data: dict = None):
        """Sends requests concurrently."""
        tasks = [self.create_task(file_path, form_data) for _ in range(count)]
        await asyncio.gather(*tasks)


# Usage Example
if __name__ == "__main__":
    file_path = r"C:\Users\Evil0ctal\Downloads\Example.mp4"
    custom_form_data = None
    client = WhisperTaskClient()

    # Run the async methods for testing
    count = 100

    # Sequential requests
    asyncio.run(client.send_single_requests(file_path, count, custom_form_data))

    # Concurrent requests
    asyncio.run(client.send_concurrent_requests(file_path, count, custom_form_data))
