"""Server-side client for the standalone CCTV registry service."""
import os
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")


class RegistryClientError(RuntimeError):
    pass


def registry_get(path: str, params: dict | None = None):
    base_url = os.getenv("REGISTRY_API_URL", "http://127.0.0.1:8001").rstrip("/")
    token = os.getenv("REGISTRY_READER_TOKEN", "")
    if not token:
        raise RegistryClientError("registry_reader_token_missing")
    try:
        response = httpx.get(
            f"{base_url}{path}", params=params,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=10, trust_env=False,
        )
    except httpx.HTTPError as exc:
        raise RegistryClientError("registry_unavailable") from exc
    if response.status_code == 404:
        raise RegistryClientError("registry_camera_not_found")
    if response.is_error:
        raise RegistryClientError(f"registry_error_{response.status_code}")
    return response.json()


def camera_streams(camera_id: str):
    return registry_get(f"/api/v1/cameras/{quote(camera_id, safe='')}/streams")


def resolve_worker_stream(camera_id: str):
    """Resolve a registered media URL and add server-held credentials only for the worker."""
    data = camera_streams(camera_id)
    streams = data.get("streams", [])
    priority = {"rtsp": 0, "rtsps": 1, "hls": 2, "https": 3, "http": 4, "whep": 5}
    usable = sorted((stream for stream in streams if stream.get("url")),
                    key=lambda stream: priority.get(stream.get("protocol"), 99))
    if not usable:
        raise RegistryClientError("camera_has_no_registered_stream")
    stream = usable[0]
    url = stream["url"]
    if stream.get("auth") != "server_credentials":
        return url, stream

    email = os.getenv("SENTINEL_EMAIL", "")
    password = os.getenv("SENTINEL_PASSWORD", "")
    parsed = urlsplit(url)
    if not email or not password or not parsed.hostname:
        raise RegistryClientError("stream_server_credentials_missing")
    authenticated_netloc = f"{quote(email, safe='')}:{quote(password, safe='')}@{parsed.netloc}"
    return urlunsplit((parsed.scheme, authenticated_netloc, parsed.path, parsed.query, parsed.fragment)), stream
