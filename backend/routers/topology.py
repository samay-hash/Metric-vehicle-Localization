from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from data.database import TOPOLOGY

router = APIRouter(prefix="/topology", tags=["topology"])

class CameraPosition(BaseModel):
    camera_id: str
    x: float
    y: float

class TopologyUpdate(BaseModel):
    floor_plan_url: Optional[str] = None
    cameras: Optional[List[CameraPosition]] = None

@router.get("/")
def get_topology():
    import data.database as db
    # Force reset to default if empty
    if not db.TOPOLOGY.get("floor_plan_url") or len(db.TOPOLOGY.get("cameras", [])) == 0:
        db.TOPOLOGY = {
            "floor_plan_url": "/blueprint.jpg",
            "cameras": [
                {"camera_id": "CAM_01", "x": 25, "y": 50},
                {"camera_id": "CAM_02", "x": 48, "y": 55},
                {"camera_id": "CAM_03", "x": 52, "y": 55},
                {"camera_id": "CAM_04", "x": 33, "y": 26},
                {"camera_id": "CAM_05", "x": 68, "y": 26},
                {"camera_id": "CAM_06", "x": 50, "y": 26},
                {"camera_id": "CAM_07", "x": 68, "y": 75},
                {"camera_id": "CAM_08", "x": 10, "y": 50},
            ]
        }
    return db.TOPOLOGY

@router.post("/")
def update_topology(data: TopologyUpdate):
    import data.database as db
    if data.floor_plan_url is not None:
        db.TOPOLOGY["floor_plan_url"] = data.floor_plan_url
    if data.cameras is not None:
        db.TOPOLOGY["cameras"] = [cam.dict() for cam in data.cameras]
    
    return {"status": "success", "topology": db.TOPOLOGY}
