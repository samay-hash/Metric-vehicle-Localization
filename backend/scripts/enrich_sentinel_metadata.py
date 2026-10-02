"""Backfill missing locations and GIS points for existing Sentinel cameras."""
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

from registry.config import Settings
from registry.db import make_engine, make_sessions
from registry.models import Audit, Camera, Source
from registry.sentinel_metadata import enrich_sentinel_camera


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")
    engine = make_engine(Settings.from_env().database_url)
    sessions = make_sessions(engine)
    camera_count = location_count = coordinate_count = 0

    with sessions() as db:
        rows = db.execute(
            select(Camera, Source).join(Source).where(Source.adapter == "sentinel")
        ).all()
        for camera, source in rows:
            changes = enrich_sentinel_camera(camera, camera.discovered_name)
            if not changes:
                continue
            camera_count += 1
            location_count += int("location" in changes)
            coordinate_count += int("coordinates" in changes)
            db.add(Audit(
                vendor_id=source.vendor_id,
                resource_id=camera.id,
                actor="sentinel-metadata-enrichment",
                action="camera.metadata_enriched",
                changes=changes,
            ))
        db.commit()

    engine.dispose()
    print(
        f"Enriched {camera_count} Sentinel cameras: "
        f"locations={location_count}, coordinates={coordinate_count}"
    )


if __name__ == "__main__":
    main()
