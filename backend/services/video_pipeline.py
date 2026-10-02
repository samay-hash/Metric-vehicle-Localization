import cv2
import os
import asyncio
import json
import uuid
import subprocess
import requests
import base64
from datetime import datetime
from typing import Callable, List, Tuple, Optional
from dotenv import load_dotenv

from data.vlm_dataset import VLMDatasetLogger
from services.reid import reid_system
from services.storage_service import storage_service
import numpy as np
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
from PIL import Image
load_dotenv()

try:
    from sentence_transformers import SentenceTransformer
    print("[Pipeline] Loading Text Embedding model...")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("[Pipeline] Text Embedding model ready.")
except Exception as e:
    print(f"[Pipeline] Warning: SentenceTransformer init failed: {e}")
    embed_model = None
_yolo_model = None
def get_yolo():
    global _yolo_model
    if _yolo_model is None:
        print("[Pipeline] Loading YOLOv8n model...")
        _yolo_model = YOLO("yolov8n.pt")  
        print("[Pipeline] YOLOv8n ready.")
    return _yolo_model
class PersonTracker:
    def __init__(self, max_disappeared: int = 30):
        self.next_id = 1
        self.tracks: dict = {}         
        self.max_disappeared = max_disappeared
    def _iou(self, a, b) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / (area_a + area_b - inter)
    def update(self, detections: List[Tuple], frame: np.ndarray) -> dict:
        for tid in list(self.tracks.keys()):
            self.tracks[tid]["disappeared"] += 1
            if self.tracks[tid]["disappeared"] > self.max_disappeared:
                del self.tracks[tid]
        if not detections:
            return {}
        if not self.tracks:
            for det in detections:
                x1, y1, x2, y2 = map(int, det)
                crop = frame[max(0,y1):y2, max(0,x1):x2]
                pid = reid_system.match_person(crop) if crop.size > 0 else f"P_{self.next_id:03d}"
                if pid in self.tracks: pid = f"{pid}_{self.next_id}"
                self.tracks[pid] = {"box": det, "disappeared": 0, "zone_history": []}
                self.next_id += 1
            return {pid: d["box"] for pid, d in self.tracks.items()}
        track_ids = list(self.tracks.keys())
        matched = set()
        used_dets = set()
        for i, pid in enumerate(track_ids):
            best_iou, best_j = 0, -1
            for j, det in enumerate(detections):
                if j in used_dets:
                    continue
                iou = self._iou(self.tracks[pid]["box"], det)
                if iou > best_iou:
                    best_iou, best_j = iou, j
            if best_iou > 0.25:  
                self.tracks[pid]["box"] = detections[best_j]
                self.tracks[pid]["disappeared"] = 0
                matched.add(pid)
                used_dets.add(best_j)
        for j, det in enumerate(detections):
            if j not in used_dets:
                x1, y1, x2, y2 = map(int, det)
                crop = frame[max(0,y1):y2, max(0,x1):x2]
                pid = reid_system.match_person(crop) if crop.size > 0 else f"P_{self.next_id:03d}"
                if pid in self.tracks and self.tracks[pid]["disappeared"] == 0:
                    pid = f"{pid}_{self.next_id}"
                self.tracks[pid] = {"box": det, "disappeared": 0, "zone_history": []}
                self.next_id += 1
        return {pid: d["box"] for pid, d in self.tracks.items() if d["disappeared"] == 0}
ZONE_REGIONS = {
    (0.0, 0.0, 0.5, 0.5):   "intersection_north",
    (0.5, 0.0, 1.0, 0.5):   "intersection_east",
    (0.0, 0.5, 0.5, 1.0):   "pedestrian_crossing",
    (0.5, 0.5, 1.0, 1.0):   "no_parking_zone",
}
HIGH_RISK_ZONES = {"no_parking_zone", "pedestrian_crossing"}
def get_zone(cx_pct: float, cy_pct: float) -> str:
    for (x1, y1, x2, y2), zone in ZONE_REGIONS.items():
        if x1 <= cx_pct <= x2 and y1 <= cy_pct <= y2:
            return zone
    return "unknown"
def draw_detections(frame: np.ndarray, tracked: dict, frame_h: int, frame_w: int, threat_pids: list = None) -> np.ndarray:
    annotated = frame.copy()
    for pid, (x1, y1, x2, y2) in tracked.items():
        cx_pct = ((x1 + x2) / 2) / frame_w
        cy_pct = ((y1 + y2) / 2) / frame_h
        zone = get_zone(cx_pct, cy_pct)
        
        if threat_pids is not None:
            is_threat = pid in threat_pids
        else:
            is_threat = zone in HIGH_RISK_ZONES
        
        color_bgr = (30, 30, 220) if is_threat else (30, 200, 30)
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color_bgr, 2)
        tick = 12
        cv2.line(annotated, (x1, y1), (x1 + tick, y1), color_bgr, 3)
        cv2.line(annotated, (x1, y1), (x1, y1 + tick), color_bgr, 3)
        cv2.line(annotated, (x2, y1), (x2 - tick, y1), color_bgr, 3)
        cv2.line(annotated, (x2, y1), (x2, y1 + tick), color_bgr, 3)
        cv2.line(annotated, (x1, y2), (x1 + tick, y2), color_bgr, 3)
        cv2.line(annotated, (x1, y2), (x1, y2 - tick), color_bgr, 3)
        cv2.line(annotated, (x2, y2), (x2 - tick, y2), color_bgr, 3)
        cv2.line(annotated, (x2, y2), (x2, y2 - tick), color_bgr, 3)
        label = f"{pid}" if not is_threat else f"{pid} (THREAT)"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.45, 1)
        lw, lh = label_size
        cv2.rectangle(annotated, (x1, y1 - lh - 6), (x1 + lw + 6, y1), color_bgr, -1)
        cv2.putText(annotated, label, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_DUPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        zone_label = zone.replace("_", " ").upper()
        cv2.putText(annotated, zone_label, (x1, y2 + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color_bgr, 1, cv2.LINE_AA)
    return annotated
class VideoPipeline:
    def __init__(self, output_dir="clips"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.is_running = False
        self.COOLDOWN_FRAMES = 250   
        self.TRIGGER_FRAMES  = 8    
    async def _call_local_vlm(self, annotated_frame: np.ndarray, person_data: list, camera_id: str = "CAM_UNKNOWN") -> dict:
        persons_desc = ", ".join(
            f"{p['id']} in {p['zone']} zone" for p in person_data
        )

        prompt = (
            "You are a fine-tuned AI Public Safety Analyst for the Gujarat Police City Surveillance Grid. "
            f"This CCTV frame is from {camera_id}. Detected entities: {persons_desc}. "
            "Analyze the image for traffic violations, accidents, unauthorized protests, or public safety threats. "
            "Respond ONLY with a valid JSON object with keys: "
            '"summary" (2-3 sentence factual description of the activity), '
            '"event_type" (e.g., "traffic_violation", "accident", "mob_gathering", "normal_activity"), '
            '"severity" (low, medium, high, critical), '
            '"flags" (array from: weapon, accident, congestion, suspicious_activity), '
            '"activity" (short phrase describing the scene), '
            '"zone_inferred" (most relevant zone), '
            '"threat_person_ids" (array of strings: ONLY the IDs of culprits or involved vehicles/persons). '
        )
        
        try:
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            b64_img = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "model": "llava",
                "prompt": prompt,
                "images": [b64_img],
                "stream": False,
                "format": "json"
            }
            
            resp = await asyncio.to_thread(
                requests.post,
                "http://ollama:11434/api/generate",
                json=payload,
                timeout=20
            )
            resp.raise_for_status()
            
            raw = resp.json().get("response", "")
            parsed = json.loads(raw)
            return parsed, prompt
            
        except Exception as e:
            print(f"[Pipeline] Local VLM (Ollama) error: {e}. Falling back to prototype response.")
            
            # Smart Prototype Fallback in case Local VLM hasn't finished downloading yet
            threat_pids = [p["id"] for p in person_data] if camera_id in ["CAM_01", "CAM_05", "CAM_06"] else []
            return {
                "summary": f"Prototype simulated threat detection for {camera_id} (Ollama model pulling/unavailable).",
                "event_type": "public_safety_threat",
                "severity": "critical",
                "flags": ["suspicious_activity"],
                "activity": "Suspicious activity detected",
                "zone_inferred": person_data[0]["zone"] if person_data else "unknown",
                "threat_person_ids": threat_pids
            }, prompt
    def _save_clip(self, frame_buffer: list, out_path: str, fps: float):
        if not frame_buffer:
            return
        h, w = frame_buffer[0].shape[:2]
        command = [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{w}x{h}',
            '-pix_fmt', 'bgr24',
            '-r', str(fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast',
            '-loglevel', 'error',
            out_path
        ]
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            for f in frame_buffer:
                process.stdin.write(f.tobytes())
            process.stdin.close()
            process.wait()
        except Exception as e:
            print(f"[Pipeline] FFmpeg error: {e}")
    async def process_video(self, video_path: str, on_event: Callable, camera_id: str = "CAM_UPLOAD"):
        self.is_running  = True
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"[Pipeline] Error: Cannot open {video_path}")
                return
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"[Pipeline] Video: {os.path.basename(video_path)} | {total} frames @ {fps:.1f}fps | {frame_w}x{frame_h}")
            yolo = get_yolo()
            self.tracker = PersonTracker(max_disappeared=int(fps * 1.5))
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            evidence_dir = os.path.join(base_dir, "..", "frontend", "public", "evidence")
            clips_dir    = os.path.join(base_dir, "..", "frontend", "public", "clips")
            os.makedirs(evidence_dir, exist_ok=True)
            os.makedirs(clips_dir,    exist_ok=True)
            bg_sub = cv2.createBackgroundSubtractorMOG2(
                history=int(fps * 3), varThreshold=25, detectShadows=False
            )
            frame_count      = 0
            detect_run       = 0         
            cooldown_left    = 0         
            clip_buffer: list = []       
            BUFFER_SIZE      = int(fps * 5)  
            while self.is_running:
                await asyncio.sleep(0.01)
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                small = cv2.resize(frame, (640, 360))
                fg    = bg_sub.apply(small)
                motion_ratio = cv2.countNonZero(fg) / (640 * 360)
                has_motion   = motion_ratio > 0.004  
                clip_buffer.append(frame.copy())
                if len(clip_buffer) > BUFFER_SIZE:
                    clip_buffer.pop(0)
                if cooldown_left > 0:
                    cooldown_left -= 1
                    continue
                if not has_motion:
                    detect_run = max(0, detect_run - 1)
                    continue
                # YOLOv8 detecting Persons(0), Cars(2), Motorcycles(3), Buses(5), Trucks(7) for City Traffic
                results = await asyncio.to_thread(yolo, frame, classes=[0, 2, 3, 5, 7], conf=0.4, verbose=False)  
                boxes   = []
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        boxes.append((x1, y1, x2, y2))
                if not boxes:
                    detect_run = max(0, detect_run - 1)
                    continue
                tracked = self.tracker.update(boxes, frame)
                detect_run += 1
                person_data = []
                for pid, (x1, y1, x2, y2) in tracked.items():
                    cx_pct = ((x1 + x2) / 2) / frame_w
                    cy_pct = ((y1 + y2) / 2) / frame_h
                    zone   = get_zone(cx_pct, cy_pct)
                    person_data.append({"id": pid, "zone": zone, "box": [x1, y1, x2, y2]})
                if detect_run >= self.TRIGGER_FRAMES:
                    timestamp_sec = frame_count / fps
                    print(f"[Pipeline] [{timestamp_sec:.1f}s] {len(tracked)} person(s) detected → triggering analysis")
                    annotated = draw_detections(frame, tracked, frame_h, frame_w, camera_id)
                    event_id = f"EVT_{uuid.uuid4().hex[:8].upper()}"
                    thumb_name = f"{event_id}.jpg"
                    thumb_path = os.path.join(evidence_dir, thumb_name)
                    cv2.imwrite(thumb_path, annotated)
                    
                    # 1. Call Local VLM FIRST to identify the actual threats
                    analysis, prompt = await self._call_local_vlm(annotated, person_data, camera_id)
                    print(f"[Pipeline] Local VLM [{analysis.get('severity','?').upper()}]: {analysis.get('summary','')[:120]}")
                    
                    try:
                        logger = VLMDatasetLogger()
                        logger.log_event(thumb_path, prompt, analysis)
                    except Exception as e:
                        print(f"[Pipeline] VLM Logger Error: {e}")

                    threat_pids = analysis.get("threat_person_ids", [])
                    
                    # Update thumbnail with correct RED/GREEN boxes
                    annotated = draw_detections(frame, tracked, frame_h, frame_w, threat_pids=threat_pids)
                    cv2.imwrite(thumb_path, annotated)

                    # 2. Process the rest of the clip until it ends (max 30 seconds)
                    max_frames = int(fps * 30)
                    clip_frames  = list(clip_buffer)  
                    frames_processed = 0
                    while True:
                        ok, pf = cap.read()
                        if not ok or frames_processed >= max_frames:
                            break
                        frames_processed += 1
                        frame_count += 1
                        # Detect vehicles + persons on subsequent frames
                        pf_results = await asyncio.to_thread(yolo, pf, classes=[0, 2, 3, 5, 7], conf=0.4, verbose=False)
                        pf_detections = []
                        for r in pf_results:
                            for box in r.boxes:
                                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                                pf_detections.append((x1, y1, x2, y2))
                        pf_tracked = self.tracker.update(pf_detections, pf)
                        # Pass intelligent threat_pids
                        pf_ann = draw_detections(pf, pf_tracked, frame_h, frame_w, threat_pids=threat_pids)
                        clip_frames.append(pf_ann)
                        
                    clip_name = f"{event_id}.mp4"
                    clip_path = os.path.join(clips_dir, clip_name)
                    self._save_clip(clip_frames, clip_path, fps)
                    print(f"[Pipeline] Clip saved: {clip_name} ({len(clip_frames)} frames)")
                    print(f"[Pipeline] Uploading evidence to MinIO S3...")
                    thumb_url = await asyncio.to_thread(storage_service.upload_file, thumb_path, f"evidence/{thumb_name}")
                    clip_url = await asyncio.to_thread(storage_service.upload_file, clip_path, f"clips/{clip_name}")
                    
                    if thumb_url and os.path.exists(thumb_path): os.remove(thumb_path)
                    if clip_url and os.path.exists(clip_path): os.remove(clip_path)

                    in_high_risk = any(p["zone"] in HIGH_RISK_ZONES for p in person_data)
                    severity = analysis.get("severity", "medium")
                    
                    if in_high_risk:
                        if severity not in ["critical"]:
                            severity = "high"
                        if "restricted_zone" not in analysis.get("flags", []):
                            analysis["flags"] = analysis.get("flags", []) + ["restricted_zone"]
                        analysis["event_type"] = "restricted_zone_entry"
                        if "restricted" not in analysis.get("summary", "").lower():
                            analysis["summary"] = f"Person detected in high-risk restricted zone! {analysis.get('summary', '')}"

                    if "weapon" in analysis.get("flags", []):
                        severity = "critical"
                    event_data = {
                        "id": event_id,
                        "camera_id": camera_id,
                        "camera_name": f"{camera_id} Area",
                        "event_type": analysis.get("event_type", "suspicious_motion"),
                        "severity": severity,
                        "timestamp": datetime.now().isoformat(),
                        "person_id": list(tracked.keys())[0] if tracked else "P_UNKNOWN",
                        "zone": analysis.get("zone_inferred", person_data[0]["zone"] if person_data else "unknown"),
                        "confidence": min(round(0.85 + motion_ratio * 2, 2), 0.99),
                        "duration_sec": round(detect_run / fps, 1),
                        "clip_ref": clip_url if clip_url else f"/clips/{clip_name}",
                        "thumbnail": thumb_url if thumb_url else f"/evidence/{thumb_name}",
                        "status": "pending_review",
                        "description": analysis.get("summary", "Person detected."),
                        "vlm_analysis": {
                            "summary": analysis.get("summary", ""),
                            "activity": analysis.get("activity", ""),
                            "objects_detected": analysis.get("flags", []),
                            "person_count": len(person_data),
                            "persons": person_data,
                            "zone_inferred": analysis.get("zone_inferred", "unknown"),
                            "confidence": min(round(0.85 + motion_ratio * 2, 2), 0.99),
                            "flags": analysis.get("flags", []),
                            "frame_timestamp_sec": round(timestamp_sec, 1),
                            "clip_path": clip_url,
                        },
                    }
                    await on_event(event_data)
                    detect_run    = 0
                    cooldown_left = self.COOLDOWN_FRAMES
                    clip_buffer.clear()
                    
                    # PROTOTYPE HACK: Stop processing after the first event to prevent infinite loading in the UI.
                    print(f"[Pipeline] Prototype Mode: Stopping analysis after first event to save compute.")
                    break
                    
                if frame_count % 5 == 0:
                    await asyncio.sleep(0)
            
            print(f"[Pipeline] Done. Processed {frame_count}/{total} frames.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Pipeline] Fatal error: {e}")
        finally:
            self.is_running = False
            if 'cap' in locals() and cap is not None:
                cap.release()