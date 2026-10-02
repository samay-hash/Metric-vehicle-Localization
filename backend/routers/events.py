from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from data.database import EVENTS, EVENT_TYPES, TRAJECTORIES, add_event
from datetime import datetime, timedelta
import copy

router = APIRouter(prefix="/events", tags=["events"])

# ── Edge Node Ingest endpoint ─────────────────────────────────────────────────
MOCK_VAHAN_DB = {
    "GJ01AB1234": {
        "owner": "Harshil Patel",
        "make": "Maruti Swift (White)",
        "status": "STOLEN - HOTLISTED"
    },
    "MH02CD5678": {
        "owner": "Rahul Sharma",
        "make": "Hyundai Creta (Black)",
        "status": "CLEAR"
    },
    "DL03EF9012": {
        "owner": "Amit Singh",
        "make": "Honda City (Silver)",
        "status": "SUSPICIOUS - UNPAID CHALLANS"
    }
}

class EdgeDetection(BaseModel):
    id: str
    camera_id: str
    timestamp_utc: str
    pts_ms: Optional[float] = 0.0
    track_id: Optional[int] = None
    event_type: str          # "vehicle_detected" | "person_detected"
    severity: str
    bbox: List[float]
    confidence: float
    status: str
    plate: Optional[str] = None   # filled in after ANPR
    duration_frames: Optional[int] = None

@router.post("/ingest")
def ingest_edge_detection(det: EdgeDetection):
    """
    Receives detections from the edge_node.py RTSP processor.
    For vehicles: runs ANPR plate check + watchlist match + journey recording.
    """
    from routers.watchlist import check_plate_against_watchlist, record_watchlist_alert, WATCHLIST_ALERTS
    from routers.vehicles import record_vehicle_sighting

    plate = det.plate
    alert = None
    vahan_data = None

    # If plate not already read by edge, try to match from existing data
    if plate:
        # Check watchlist
        match = check_plate_against_watchlist(plate)
        if match:
            alert = record_watchlist_alert(plate, det.camera_id, det.pts_ms, match)

        # Check VAHAN mock DB
        vahan_data = MOCK_VAHAN_DB.get(plate, {
            "owner": "UNKNOWN",
            "make": "UNKNOWN",
            "status": "UNKNOWN"
        })

        # Record in journey tracker
        if det.event_type == "vehicle_detected":
            record_vehicle_sighting(plate, det.camera_id, det.pts_ms, det.bbox, det.confidence)

    event = {
        "id": det.id,
        "camera_id": det.camera_id,
        "camera_name": det.camera_id.upper(),
        "zone": "public",
        "timestamp": datetime.fromisoformat(det.timestamp_utc.replace("Z", "+00:00")),
        "event_type": det.event_type,
        "severity": "critical" if alert else det.severity,
        "status": "alert" if alert else det.status,
        "description": (
            f"{'Vehicle' if det.event_type == 'vehicle_detected' else 'Person'} detected "
            f"on {det.camera_id.upper()} ({det.confidence*100:.1f}% confidence)."
            + (f" Plate: {plate}." if plate else "")
            + (f" ⚠️ WATCHLIST HIT: {alert['message']}" if alert else "")
        ),
        "confidence": det.confidence,
        "bbox": det.bbox,
        "plate": plate,
        "pts_ms": det.pts_ms,
        "vlm_analysis": None,
        "clip_ref": None,
        "thumbnail": None,
        "person_id": None,
        "watchlist_alert": alert,
        "vahan_data": vahan_data,
    }
    add_event(event)

    return {
        "status": "ingested",
        "event_id": det.id,
        "watchlist_matched": alert is not None,
        "alert": alert,
    }


@router.get("/")
def list_events(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    results = copy.deepcopy(EVENTS)
    if severity:
        results = [e for e in results if e["severity"] == severity]
    if status:
        results = [e for e in results if e["status"] == status]
    if camera_id:
        results = [e for e in results if e["camera_id"] == camera_id]
    if zone:
        results = [e for e in results if e["zone"] == zone]
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return {
        "events": results[:limit],
        "total": len(results),
        "filters_applied": {
            "severity": severity,
            "status": status,
            "camera_id": camera_id,
            "zone": zone,
        },
    }
@router.get("/types")
def get_event_types():
    return {"event_types": EVENT_TYPES}
@router.get("/stats")
def event_stats():
    severity_counts = {}
    status_counts = {}
    zone_counts = {}
    for e in EVENTS:
        severity_counts[e["severity"]] = severity_counts.get(e["severity"], 0) + 1
        status_counts[e["status"]] = status_counts.get(e["status"], 0) + 1
        zone_counts[e["zone"]] = zone_counts.get(e["zone"], 0) + 1
    return {
        "total_events": len(EVENTS),
        "by_severity": severity_counts,
        "by_status": status_counts,
        "by_zone": zone_counts,
    }
@router.get("/{event_id}")
def get_event(event_id: str):
    event = next((e for e in EVENTS if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return event
@router.patch("/{event_id}/status")
def update_event_status(event_id: str, new_status: str):
    valid = ["pending_review", "under_investigation", "resolved", "escalated", "false_positive"]
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid}")
    event = next((e for e in EVENTS if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event["status"] = new_status
    return {"message": f"Event {event_id} status updated to {new_status}", "event_id": event_id, "status": new_status}
@router.get("/person/{person_id}/trajectory")
def get_person_trajectory(person_id: str):
    traj = TRAJECTORIES.get(person_id)
    if not traj:
        raise HTTPException(status_code=404, detail=f"No trajectory data for {person_id}")
    return {"person_id": person_id, "trajectory": traj, "total_points": len(traj)}
@router.get("/live/feed")
def live_event_feed():
    recent = sorted(EVENTS, key=lambda x: x["timestamp"], reverse=True)[:5]
    return {"feed": recent, "as_of": datetime.now().isoformat()}