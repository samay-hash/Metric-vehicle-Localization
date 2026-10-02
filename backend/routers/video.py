import os
import shutil
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from services.video_pipeline import VideoPipeline
from data.database import add_event
router = APIRouter(prefix="/video", tags=["video"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
pipeline = VideoPipeline(output_dir="clips")
async def handle_event(event_data):
    add_event(event_data)
    print(f"New event added from video pipeline: {event_data['id']}")
@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    camera_id: str = Form("CAM_UPLOAD")
):
    if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid video format.")
    if pipeline.is_running:
        raise HTTPException(status_code=409, detail="A video is currently being processed. Please wait.")
    file_id = uuid.uuid4().hex[:8]
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    background_tasks.add_task(pipeline.process_video, file_path, handle_event, camera_id)
    return {
        "message": "Video uploaded successfully and processing started.",
        "file_id": file_id,
        "filename": safe_filename,
        "status": "processing"
    }
@router.get("/status")
def get_video_status():
    return {
        "is_running": pipeline.is_running
    }

from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    camera_id: str

@router.post("/run-analysis")
async def run_local_analysis(
    req: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    if pipeline.is_running:
        raise HTTPException(status_code=409, detail="A video is currently being processed. Please wait.")
        
    cam_index = req.camera_id.replace("CAM_0", "") 
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(base_dir, "frontend", "public", "streams", f"cam{cam_index}.mp4")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Local video file not found at {file_path}")
        
    background_tasks.add_task(pipeline.process_video, file_path, handle_event, req.camera_id)
    return {
        "message": f"AI Analysis started for {req.camera_id}",
        "status": "processing"
    }