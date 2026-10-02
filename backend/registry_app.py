"""Run from backend: uvicorn registry_app:app --host 127.0.0.1 --port 8001."""
from pathlib import Path
from dotenv import load_dotenv
from registry.app import create_app

load_dotenv(Path(__file__).resolve().parent / ".env.registry")
app = create_app()
