import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as client:
        payload = {
            "model": "qwen:0.5b",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True
        }
        try:
            async with client.stream("POST", "http://127.0.0.1:11434/api/chat", json=payload) as response:
                response.raise_for_status()
                print(response.status_code)
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
