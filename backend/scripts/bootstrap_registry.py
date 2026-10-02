"""Register the real Sentinel source through the API. Safe to repeat."""
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.username or url.password or url.query or url.fragment or not (url.scheme == "https" or (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1"))):
        parser.error("Use HTTPS or a loopback HTTP address without embedded credentials")
    token = os.getenv("REGISTRY_ADMIN_TOKEN", "")
    if not token:
        parser.error("Set REGISTRY_ADMIN_TOKEN in the registry environment")
    with httpx.Client(base_url=args.url.rstrip("/"), headers={"Authorization": f"Bearer {token}"}, timeout=90, trust_env=False) as client:
        def call(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.is_error:
                # Responses intentionally contain codes, never source secrets.
                raise SystemExit(f"Registry request failed ({response.status_code}): {response.text[:500]}")
            return response.json()

        def find(path, predicate):
            after = None
            while True:
                page = call("GET", path, params={"after": after} if after else {})
                found = next((row for row in page["data"] if predicate(row)), None)
                if found or not page["next_cursor"]:
                    return found
                after = page["next_cursor"]

        vendor = find("/api/v1/vendors", lambda row: row["slug"] == "sentinel")
        if vendor is None:
            vendor = call("POST", "/api/v1/vendors", json={"name": "Sentinel", "slug": "sentinel"})
        source = find("/api/v1/sources", lambda row: row["vendor_id"] == vendor["id"] and row["slug"] == "sentinel-government")
        if source is None:
            source = call("POST", "/api/v1/sources", json={"vendor_id": vendor["id"], "slug": "sentinel-government",
                "name": "Sentinel government catalogue", "adapter": "sentinel", "connector_profile": "sentinel"})
        if source["state"] == "disabled":
            raise SystemExit("Source is disabled. An administrator must explicitly re-enable it.")
        preview = call("POST", f'/api/v1/sources/{source["id"]}/sync', json={"dry_run": True})
        if source["state"] == "draft":
            call("PUT", f'/api/v1/sources/{source["id"]}/state', json={"state": "approved"})
        result = call("POST", f'/api/v1/sources/{source["id"]}/sync', json={"dry_run": False})
        print(f'Vendor: {vendor["id"]}; source: {source["id"]}')
        print(f'Discovered {result["discovered"]}; created {result["created"]}; updated {result["updated"]}; missing {result["missing"]}')
        print("Coordinates, infrastructure and media health remain unknown until supplied or measured.")


if __name__ == "__main__":
    main()
