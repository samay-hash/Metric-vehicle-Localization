import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def generate_text(prompt: str, system_prompt: str = "") -> str:
    """Generate a single text response using Google Gemini API."""
    if not GEMINI_API_KEY:
        return "AI Service is currently unavailable. (Missing GEMINI_API_KEY in .env)"
    try:
        # Wrap synchronous call in thread for async execution
        def _generate():
            client = genai.Client(api_key=GEMINI_API_KEY)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            return response.text
            
        return await asyncio.to_thread(_generate)
    except Exception as e:
        print(f"[Gemini API] Error generating text: {e}")
        return "AI Service is currently unavailable."

async def generate_chat_stream(messages: list, system_prompt: str = ""):
    """Yield streamed chunks from Google Gemini API."""
    if not GEMINI_API_KEY:
        yield "AI Service is currently unavailable. Please add GEMINI_API_KEY to your .env file."
        return
        
    try:
        # Format messages for Gemini
        gemini_messages = []
        for msg in messages:
            role = 'user' if msg.get('role') == 'user' else 'model'
            gemini_messages.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get('content', ''))])
            )
            
        def _get_stream():
            client = genai.Client(api_key=GEMINI_API_KEY)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
            )
            return client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=gemini_messages,
                config=config
            )
            
        # The stream is an iterable, we can yield from it in a thread or directly
        # genai sdk streaming is synchronous, so we'll consume chunks in an async way
        stream = await asyncio.to_thread(_get_stream)
        
        for chunk in stream:
            # Yielding synchronously is fine here or we can await sleep
            yield chunk.text
            await asyncio.sleep(0)
            
    except Exception as e:
        print(f"[Gemini API] Error streaming chat: {e}")
        yield "AI Service encountered an error."
