import uuid
import os
import shutil
import cv2
import asyncio
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from services.ml_service import threat_detector
from data.database import add_event
from services.storage_service import storage_service

router = APIRouter(prefix="/inference", tags=["ML Inference"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "inference")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
async def analyze_frame(camera_id: str = Form(...), file: UploadFile = File(...)):
    """
    Receives an image frame, runs PaliGemma inference, and injects a critical event if a weapon is detected.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_ext = os.path.splitext(file.filename)[1]
    temp_filename = f"{uuid.uuid4().hex}{file_ext}"
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)

    # Save uploaded file
    with open(temp_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"Received frame from {camera_id}. Running ML inference...")
    
    # Run Inference
    is_threat = await asyncio.to_thread(threat_detector.analyze_frame, temp_filepath)
    
    # Create Event if threat detected
    if is_threat:
        event_id = f"EVT_{uuid.uuid4().hex[:8].upper()}"
        print(f"🚨 WEAPON DETECTED on {camera_id}! Creating Event {event_id} 🚨")
        
        event = {
            "id": event_id,
            "camera_id": camera_id,
            "camera_name": camera_id,  # Fallback, real system would look it up
            "timestamp": datetime.utcnow(),
            "event_type": "weapon_detected",
            "severity": "critical",
            "description": "AI detected a weapon in the frame.",
            "status": "pending_review",
            "clip_ref": f"/uploads/inference/{temp_filename}",
            "thumbnail": f"/uploads/inference/{temp_filename}",
            "confidence": 0.95
        }
        add_event(event)
        
        return {"status": "success", "threat_detected": True, "event_id": event_id}
    else:
        print("✅ Frame is clear.")
        return {"status": "success", "threat_detected": False}

async def process_video_background(video_path: str, camera_id: str, original_filename: str):
    """
    Background task: Reads video, extracts frames at 1 fps, runs ML inference.
    If a weapon is found, it triggers an event and saves the specific frame.
    """
    print(f"🎬 Starting background analysis for video {original_filename} on {camera_id}...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = int(fps * 2)  
    
    frame_count = 0
    threat_found = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            temp_frame_path = os.path.join(UPLOAD_DIR, f"temp_frame_{uuid.uuid4().hex}.jpg")
            cv2.imwrite(temp_frame_path, frame)
            

            print(f"[{camera_id}] Analyzing frame at {frame_count/fps:.1f}s...")
            is_threat = await asyncio.to_thread(threat_detector.analyze_frame, temp_frame_path)
            
            if is_threat:
                threat_found = True
                event_id = f"EVT_{uuid.uuid4().hex[:8].upper()}"
                print(f"🚨 WEAPON DETECTED in video at {frame_count/fps:.1f}s! Creating Event {event_id}")
                
                # Upload to S3 / MinIO
                video_url = storage_service.upload_file(video_path, f"clips/{event_id}.mp4")
                thumb_url = storage_service.upload_file(temp_frame_path, f"evidence/{event_id}.jpg")
                
                # We can now safely delete the temp frame (and video will be deleted at the end)
                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)
                
                event = {
                    "id": event_id,
                    "camera_id": camera_id,
                    "camera_name": f"{camera_id} Area",
                    "timestamp": datetime.utcnow(),
                    "event_type": "weapon_detected",
                    "severity": "critical",
                    "description": f"AI detected a weapon at {frame_count/fps:.1f}s in uploaded CCTV feed.",
                    "status": "pending_review",
                    "clip_ref": video_url,
                    "thumbnail": thumb_url,
                    "confidence": 0.96
                }
                add_event(event)
                

                break
            else:
               
                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)
                    
        frame_count += 1
        await asyncio.sleep(0)  
        
    cap.release()

    if os.path.exists(video_path):
        os.remove(video_path)
        
    if not threat_found:
        print(f"✅ Video analysis complete. No threats found in {original_filename}.")

@router.post("/analyze_video")
async def analyze_video(
    background_tasks: BackgroundTasks,
    camera_id: str = Form(...), 
    file: UploadFile = File(...)
):
    """
    Receives a video file, saves it, and spawns a background task to process it.
    Returns immediately so the UI doesn't block.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_ext = os.path.splitext(file.filename)[1]
    temp_filename = f"vid_{uuid.uuid4().hex}{file_ext}"
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)


    with open(temp_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


    background_tasks.add_task(process_video_background, temp_filepath, camera_id, file.filename)
    
    return {
        "status": "processing", 
        "message": "Video uploaded successfully. ML analysis started in background."
    }

from pydantic import BaseModel
from fastapi.responses import StreamingResponse

class CopilotRequest(BaseModel):
    messages: list
    context: str

@router.post("/copilot")
async def copilot_chat(req: CopilotRequest):
    """
    Proxies chat queries to the local Ollama LLM.
    Streams the response back to the frontend.
    """
    from services.local_llm import generate_chat_stream
    import re
    
    # ── Database RAG Logic ──
    # Search the ENTIRE conversation history to preserve context across messages
    full_conversation = " ".join([m["content"] for m in req.messages if m.get("role") == "user"]).upper()
    plate_matches = re.findall(r"([A-Z0-9]{8,10})", full_conversation)
    
    if plate_matches:
        # Use the most recently mentioned plate for RAG injection
        plate = plate_matches[-1]
        try:
            from database import SessionLocal, VehicleSighting
            db = SessionLocal()
            try:
                sightings = db.query(VehicleSighting).filter(VehicleSighting.plate == plate).order_by(VehicleSighting.timestamp.asc()).all()
            finally:
                db.close()
            
            if sightings:
                history_text = f"\\n\\n[SYSTEM KNOWLEDGE]: The vehicle {plate} was detected in the database:\\n"
                for s in sightings:
                    history_text += f"- Seen at Camera: {s.camera_id} at Time: {s.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\\n"
                history_text += "Use this exact information to answer the user's question accurately."
                req.context += history_text
            else:
                req.context += f"\\n\\n[SYSTEM KNOWLEDGE]: No historical data found for vehicle {plate}."
        except Exception as e:
            print(f"Error querying db for chat: {e}")
            
    return StreamingResponse(
        generate_chat_stream(req.messages, system_prompt=req.context),
        media_type="text/event-stream"
    )
