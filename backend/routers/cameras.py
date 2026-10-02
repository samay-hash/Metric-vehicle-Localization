from fastapi import APIRouter, HTTPException
from typing import List
from data.database import CAMERAS, ZONES, SYSTEM_STATS
import random
router = APIRouter(prefix="/cameras", tags=["cameras"])
@router.get("/")
def list_cameras():
    return {"cameras": CAMERAS, "total": len(CAMERAS)}
@router.get("/{camera_id}")
def get_camera(camera_id: str):
    cam = next((c for c in CAMERAS if c["id"] == camera_id), None)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    cam_with_stats = {
        **cam,
        "current_fps": SYSTEM_STATS()["streams_fps"].get(camera_id, 0),
        "persons_detected": random.randint(0, 5),
        "active_events": random.randint(0, 2),
        "uptime_hours": round(random.uniform(20, 24), 1),
    }
    return cam_with_stats
@router.get("/zones/list")
def get_zones():
    return {"zones": ZONES}
@router.get("/{camera_id}/stats")
def camera_stats(camera_id: str):
    cam = next((c for c in CAMERAS if c["id"] == camera_id), None)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {
        "camera_id": camera_id,
        "fps_live": SYSTEM_STATS()["streams_fps"].get(camera_id, 0),
        "gpu_decode_ms": round(random.uniform(2, 8), 2),
        "inference_ms": round(random.uniform(18, 35), 2),
        "tracker_ms": round(random.uniform(1, 4), 2),
        "total_latency_ms": round(random.uniform(22, 50), 2),
        "persons_in_frame": random.randint(0, 8),
        "objects_in_frame": random.randint(0, 15),
        "zone": cam["zone"],
    }