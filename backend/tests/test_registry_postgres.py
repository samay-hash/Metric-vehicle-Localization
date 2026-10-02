"""Opt-in integration test; only use a disposable database whose name ends in _test."""
import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from registry.app import create_app
from registry.config import Settings


@pytest.mark.skipif(not os.getenv("REGISTRY_TEST_DATABASE_URL"), reason="Disposable PostGIS database not configured")
def test_postgis_migration_spatial_queries_and_rollback(monkeypatch):
    url = os.environ["REGISTRY_TEST_DATABASE_URL"]
    assert make_url(url).database.endswith("_test"), "Refusing migration test on a non-test database"
    monkeypatch.setenv("REGISTRY_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "registry-alembic.ini"))
    command.upgrade(config, "head")
    token = "postgres-test-" + "x" * 32
    with TestClient(create_app(Settings(url, token)), headers={"Authorization": f"Bearer {token}"}) as client:
        vendor = client.post("/api/v1/vendors", json={"slug": "spatial-test", "name": "Spatial test"}).json()
        source = client.post("/api/v1/sources", json={"vendor_id": vendor["id"], "slug": "test", "name": "Test", "adapter": "manual"}).json()
        response = client.post("/api/v1/cameras", json={"source_id": source["id"], "external_id": "surveyed", "name": "Surveyed",
            "coordinates": {"latitude": 23, "longitude": 72, "provenance": "integration test"}})
        assert response.status_code == 201, response.text
        assert len(client.get("/api/v1/map/cameras?bbox=71,22,73,24").json()["features"]) == 1
        assert client.get("/api/v1/map/cameras?bbox=0,0,1,1").json()["features"] == []
        assert client.get("/api/v1/cameras?bbox=71,22,73,24").json()["total"] == 1
        assert "Surveyed" in client.get("/api/v1/camera-export?bbox=71,22,73,24").text
    engine = create_engine(url)
    with engine.connect() as db:
        assert json.loads(db.execute(text("SELECT ST_AsGeoJSON(geom) FROM registry_cameras")).scalar())["coordinates"] == [72, 23]
        assert db.execute(text("SELECT indexname FROM pg_indexes WHERE indexname='ix_registry_cameras_geom'")).scalar()
    engine.dispose()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
