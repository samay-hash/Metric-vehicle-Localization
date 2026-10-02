import httpx
import asyncio

async def test():
    context = """You are a helpful AI assistant for a CCTV surveillance system. Answer the user's questions based ONLY on the data provided below. Do not make up answers. Keep responses short and conversational.

SYSTEM DATA:
- The user is currently looking at camera 'Camera 5'. It sees 12 objects right now.
- No vehicles recently detected.
- No recent security alerts.
"""
    messages = [{"role": "system", "content": context}, {"role": "user", "content": "can u see the camea 5"}]
    payload = {"model": "qwen:0.5b", "messages": messages, "stream": False}
    
    async with httpx.AsyncClient() as client:
        res = await client.post("http://127.0.0.1:11434/api/chat", json=payload)
        print(res.json()["message"]["content"])

asyncio.run(test())
