"""Read-only integration with the documented Sentinel catalogue, never its control API."""
import json
import os
from urllib.parse import quote, urlsplit

import httpx
from pydantic import ValidationError

from .config import Connector, Settings
from .schemas import CatalogueEntry


class AdapterError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def fetch_sentinel(config: Connector, settings: Settings, transport=None):
    email = os.getenv(f"{config.credentials_prefix}_EMAIL", "")
    password = os.getenv(f"{config.credentials_prefix}_PASSWORD", "")
    if not email or not password:
        raise AdapterError("source_credentials_missing")
    # No redirects: credentials/cookies must never be forwarded to an unapproved host.
    with httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False,
                      trust_env=False, transport=transport,
                      headers={"User-Agent": "Synetra-Registry/1.0", "Accept": "application/json"}) as client:
        try:
            login = client.post(config.login_url, data={"email": email, "password": password})
            if login.status_code not in (200, 302, 303):
                raise AdapterError("source_authentication_failed")
            # We intentionally do not follow the login redirect. Cookie jar retains the session.
            with client.stream("GET", config.catalogue_url) as response:
                if response.status_code in (301, 302, 303, 307, 308, 401, 403):
                    raise AdapterError("source_authentication_failed")
                if response.status_code != 200:
                    raise AdapterError("catalogue_unavailable")
                if "application/json" not in response.headers.get("content-type", "").lower():
                    raise AdapterError("catalogue_not_json")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > settings.max_catalogue_bytes:
                        raise AdapterError("catalogue_too_large")
            data = json.loads(body)
            if not isinstance(data, list) or len(data) > settings.max_catalogue_cameras:
                raise AdapterError("catalogue_invalid")
            entries = [CatalogueEntry.model_validate(item) for item in data]
            if len({item.id for item in entries}) != len(entries):
                raise AdapterError("catalogue_duplicate_ids")
            return entries
        except (httpx.HTTPError, OSError):
            raise AdapterError("source_connection_failed") from None
        except (ValueError, ValidationError):
            raise AdapterError("catalogue_invalid") from None


def resolve_sentinel(config: Connector, external_id: str):
    """Internal worker-only resolution. Never serialize this result to dashboard clients."""
    email = os.getenv(f"{config.credentials_prefix}_EMAIL", "")
    password = os.getenv(f"{config.credentials_prefix}_PASSWORD", "")
    if not email or not password:
        raise AdapterError("source_credentials_missing")
    rtsp = urlsplit(config.rtsp_origin)
    camera_path = quote(external_id, safe="")
    return {
        "rtsp_url": f"{rtsp.scheme}://{quote(email, safe='')}:{quote(password, safe='')}@{rtsp.netloc}{config.rtsp_path_template.format(camera_id=camera_path)}",
        "hls_url": f"{config.hls_origin.rstrip('/')}{config.hls_path_template.format(camera_id=camera_path)}",
        "whep_url": f"{config.whep_origin.rstrip('/')}{config.whep_path_template.format(camera_id=camera_path)}",
        "hls_auth": "sentinel_portal_session",
        "rtsp_transport": "tcp",
    }


def public_sentinel_endpoints(config: Connector, external_id: str):
    camera = quote(external_id, safe="")
    rtsp = urlsplit(config.rtsp_origin)
    return {
        "rtsp_url": f"{rtsp.scheme}://{rtsp.netloc}{config.rtsp_path_template.format(camera_id=camera)}",
        "hls_url": f"{config.hls_origin.rstrip('/')}{config.hls_path_template.format(camera_id=camera)}",
        "whep_url": f"{config.whep_origin.rstrip('/')}{config.whep_path_template.format(camera_id=camera)}",
    }
