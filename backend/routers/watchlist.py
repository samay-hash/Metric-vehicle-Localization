"""
Inferia AI — Watchlist Router
Stolen vehicles, wanted persons, blacklisted plates.
Matches ANPR output against watchlist in real-time.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

# ── In-memory watchlist (seed with realistic mock data) ───────────────────────
STOLEN_VEHICLES: List[dict] = [
    {"id": "WL001", "plate": "GJ01AB1234", "type": "Car",        "make": "Maruti Swift",   "color": "White",  "reported": "2026-09-10", "status": "active", "fir": "FIR/2026/AHM/0891"},
    {"id": "WL002", "plate": "GJ05CD5678", "type": "Motorcycle", "make": "Honda Activa",   "color": "Black",  "reported": "2026-09-12", "status": "active", "fir": "FIR/2026/JUN/0234"},
    {"id": "WL003", "plate": "GJ06EF9012", "type": "Truck",      "make": "Tata 407",       "color": "Blue",   "reported": "2026-09-14", "status": "active", "fir": "FIR/2026/RAJ/0456"},
    {"id": "WL004", "plate": "GJ18GH3456", "type": "Car",        "make": "Hyundai i20",    "color": "Silver", "reported": "2026-09-15", "status": "active", "fir": "FIR/2026/SUR/0789"},
    {"id": "WL005", "plate": "GJ01KL7890", "type": "Car",        "make": "Toyota Innova",  "color": "Grey",   "reported": "2026-09-16", "status": "active", "fir": "FIR/2026/AHM/0912"},
    {"id": "WL006", "plate": "GJ09MN2345", "type": "Bus",        "make": "Ashok Leyland",  "color": "Red",    "reported": "2026-09-08", "status": "active", "fir": "FIR/2026/GAN/0123"},
    {"id": "WL007", "plate": "GJ15PQ6789", "type": "Motorcycle", "make": "Bajaj Pulsar",   "color": "Orange", "reported": "2026-09-11", "status": "active", "fir": "FIR/2026/VAD/0567"},
    {"id": "WL008", "plate": "GJ27RS0123", "type": "Car",        "make": "Mahindra Scorpio","color": "Black", "reported": "2026-09-13", "status": "active", "fir": "FIR/2026/BHU/0890"},
]

# Alert history (matched hits stored here)
WATCHLIST_ALERTS: List[dict] = []


# ── Normalise plate string for comparison ─────────────────────────────────────
def normalise(plate: str) -> str:
    return plate.upper().replace(" ", "").replace("-", "")


# ── Core match function (used by events/ingest) ───────────────────────────────
def check_plate_against_watchlist(plate: str) -> Optional[dict]:
    """
    Returns the watchlist entry if the plate matches, else None.
    Called from events/ingest whenever ANPR reads a plate.
    """
    norm = normalise(plate)
    for entry in STOLEN_VEHICLES:
        if normalise(entry["plate"]) == norm:
            return entry
    return None


def record_watchlist_alert(plate: str, camera_id: str, pts_ms: float, entry: dict) -> dict:
    """Create and store a watchlist hit alert."""
    alert = {
        "id": f"ALERT_{uuid.uuid4().hex[:8].upper()}",
        "timestamp": datetime.utcnow().isoformat(),
        "plate": plate,
        "camera_id": camera_id,
        "pts_ms": pts_ms,
        "watchlist_entry": entry,
        "severity": "CRITICAL",
        "message": (
            f"STOLEN VEHICLE DETECTED: {entry['make']} ({entry['color']}) "
            f"plate {plate} spotted on {camera_id.upper()}. FIR: {entry['fir']}"
        ),
    }
    WATCHLIST_ALERTS.append(alert)
    return alert


# ── API endpoints ─────────────────────────────────────────────────────────────

@router.get("/")
def list_watchlist():
    """Return all watchlist entries."""
    return {"total": len(STOLEN_VEHICLES), "entries": STOLEN_VEHICLES}


@router.get("/alerts")
def list_alerts():
    """Return all watchlist match alerts."""
    return {
        "total": len(WATCHLIST_ALERTS),
        "alerts": sorted(WATCHLIST_ALERTS, key=lambda x: x["timestamp"], reverse=True)
    }


@router.post("/check")
def check_plate(payload: dict):
    """Manually check a plate against the watchlist."""
    plate = payload.get("plate", "")
    if not plate:
        raise HTTPException(status_code=400, detail="plate required")
    match = check_plate_against_watchlist(plate)
    return {
        "plate": plate,
        "matched": match is not None,
        "entry": match,
    }


class WatchlistEntry(BaseModel):
    plate: str
    type: str
    make: str
    color: str
    fir: str


@router.post("/add")
def add_to_watchlist(entry: WatchlistEntry):
    """Add a new vehicle to the watchlist."""
    new = {
        "id": f"WL{len(STOLEN_VEHICLES)+1:03d}",
        "plate": entry.plate.upper(),
        "type": entry.type,
        "make": entry.make,
        "color": entry.color,
        "reported": datetime.utcnow().date().isoformat(),
        "status": "active",
        "fir": entry.fir,
    }
    STOLEN_VEHICLES.append(new)
    return {"status": "added", "entry": new}
