# pip install httpx
import httpx

url = "http://127.0.0.1/api/whisper/tasks/result"
task_id = 1

params = {
    "task_id": task_id
}


async def make_request():
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        print(response.json())


if __name__ == "__main__":
    # To run the async function
    import asyncio
    # Run the async function
    asyncio.run(make_request())
