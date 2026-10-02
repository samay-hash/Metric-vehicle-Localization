import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rbac_middleware import authorize, enforce_rbac, has_global_scope
from routers import cameras, events, investigation, reports, video, topology, inference, watchlist, vehicles, stream, registry_gateway
from database import init_db

try:
    init_db()
    print("[System] Analytics database initialized.")
except Exception as e:
    print(f"[System] Warning: Could not initialize the analytics database ({e})")

app = FastAPI(
    title="Inferia AI — Gujarat Police CCTV Intelligence Platform",
    description=(
        "Unified AI video analytics platform for Gujarat Police. "
        "WATCH → DETECT → TRACK → ALERT. "
        "Connects 50+ live CCTV feeds, runs YOLO vehicle detection, ANPR plate reading, "
        "cross-camera journey reconstruction, and real-time watchlist matching."
    ),
    version="1.0.0",
)

import asyncio
import random
import uuid
from datetime import datetime
from data.database import add_event, CAMERAS

import os, requests as _requests

import os
from services.local_llm import generate_text

async def _local_llm_describe(camera_name: str, zone: str, event_type: str, severity: str) -> str:
    """Generate a real Local LLM description for a detected event."""
    prompt = (
        f"You are a professional CCTV analyst for Gujarat Police AI Surveillance Grid. "
        f"Write ONE precise, factual observation sentence (max 20 words) describing a "
        f"'{event_type.replace('_',' ')}' event at {camera_name} ({zone} zone) with "
        f"severity '{severity}'. Be direct and professional. No filler words."
    )
    
    try:
        response = await generate_text(prompt)
        if response:
            return response.strip()
    except Exception as e:
        print(f"[System] Local LLM error: {e}")
        
    return f"{event_type.replace('_',' ').title()} detected at {camera_name} ({zone})."

async def simulate_live_events():
    while True:
        await asyncio.sleep(random.randint(20, 45))
        camera = random.choice(CAMERAS[:6])

        # 90% normal activity, 10% anomaly
        is_anomaly = random.random() < 0.1

        if is_anomaly:
            types = ["suspicious_motion", "unauthorized_entry", "loitering"]
            severity = random.choice(["high", "critical"]) if camera["zone"] == "restricted" else random.choice(["medium", "high"])
        else:
            types = ["person_detected", "vehicle_detected", "normal_activity"]
            severity = "low"

        event_type = random.choice(types)
        cam_num = int(camera["id"].split("_")[1])
        confidence = round(random.uniform(0.75, 0.98), 2)
        duration = round(random.uniform(2.0, 15.0), 1)

        # Real Local LLM generated description (no hardcoded strings)
        description = await _local_llm_describe(camera["name"], camera["zone"], event_type, severity)

        event = {
            "id": f"EVT_{uuid.uuid4().hex[:6].upper()}",
            "camera_id": camera["id"],
            "camera_name": camera["name"],
            "zone": camera["zone"],
            "timestamp": datetime.now(),
            "event_type": event_type,
            "severity": severity,
            "status": "pending_review",
            "description": description,
            "person_id": None,  # No fake person IDs — only real ANPR plates
            "clip_ref": f"/stream/{camera['id']}",  # Points to live stream, not fake .mp4
            "thumbnail": "/evidence/EVT_07D1446F.jpg",
            "confidence": confidence,
            "duration_sec": duration,
            "vlm_analysis": {
                "summary": description,
                "activity": f"{severity.upper()} activity — {event_type.replace('_', ' ')}",
                "objects_detected": ["vehicle", "person"] if is_anomaly else ["vehicle"],
                "zone_inferred": camera["zone"],
                "confidence": confidence,
                "flags": ["suspicious_motion", "restricted_zone"] if severity in ["high", "critical"] else [],
            }
        }
        add_event(event)
        print(f"[Event] {camera['id']} | {event_type} | {severity} | {description[:60]}")

@app.on_event("startup")
async def startup_event():
    if os.getenv("ENABLE_SIMULATED_EVENTS", "false").lower() in ("1", "true", "yes"):
        asyncio.create_task(simulate_live_events())


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(enforce_rbac)
BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR  = os.path.join(BASE, "uploads")
os.makedirs(UPLOADS_DIR,  exist_ok=True)
from fastapi.staticfiles import StaticFiles
app.mount("/uploads",  StaticFiles(directory=UPLOADS_DIR),  name="uploads")
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(investigation.router)
app.include_router(reports.router)
app.include_router(video.router)
app.include_router(topology.router)
app.include_router(watchlist.router)
app.include_router(vehicles.router)
app.include_router(registry_gateway.router)
app.include_router(stream.router)

from fastapi import WebSocket, WebSocketDisconnect
from websocket_manager import manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.cookies.get("synetra_session")
    identity, error = await authorize(token, "event.read")
    if error or not has_global_scope(identity):
        reason = error or "scope_not_supported_by_resource"
        await websocket.close(code=4403 if reason.startswith(("permission_required:", "scope_")) else 4401,
                              reason=reason[:120])
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
app.include_router(inference.router)
@app.get("/")
def root():
    return {
        "system": "BankCCTV AI Investigation System",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "cameras": "/cameras",
            "events": "/events",
            "investigation": "/investigation/query",
            "reports": "/reports/eod",
            "system_stats": "/reports/system/stats",
        },
    }
@app.get("/health")
def health():
    return {"status": "ok", "service": "bankcctv-backend"}# force reload
