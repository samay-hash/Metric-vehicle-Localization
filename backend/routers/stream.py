"""
Gujarat Sentinel Grid — Real ANPR Stream Pipeline
YOLO11n ByteTrack → Best-frame selection → CLAHE enhancement → EasyOCR → Voting
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import cv2
import os
import re
import logging
import time
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
import os

DISABLE_ML = os.getenv("DISABLE_ML", "false").lower() == "true" or os.getenv("RENDER", "false").lower() == "true"
if not DISABLE_ML:
    from ultralytics import YOLO
from services.registry_client import RegistryClientError, resolve_worker_stream

log = logging.getLogger("SentinelStream")
router = APIRouter(prefix="/stream", tags=["stream"])

# ── Live detection state (per camera) ─────────────────────────────────────────
# Stores the latest real YOLO detection summary for the chatbot to consume
_live_detections: dict = {}
# camera_id → {"persons": int, "vehicles": int, "classes": list, "timestamp": str, "confirmed_plates": list}

# ── Load YOLO model once (global) ─────────────────────────────────────────────
model = None
if not DISABLE_ML:
    try:
        model = YOLO("yolo11n.pt")
        log.info("[ANPR] YOLO11n loaded successfully.")
    except Exception as e:
        log.warning(f"[ANPR] Could not load YOLO model: {e}")

# ── Load EasyOCR reader once (global, expensive to init) ─────────────────────
ocr_reader = None
if not DISABLE_ML:
    try:
        import easyocr
        ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        log.info("[ANPR] EasyOCR reader initialized.")
    except Exception as e:
        log.warning(f"[ANPR] Could not load EasyOCR: {e}")

# ── Load FastReID model once (global) ─────────────────────────────────────────
import sys
from pathlib import Path
reid_model = None

if not DISABLE_ML:
    import torch
    try:
        ROOT_DIR = Path(__file__).resolve().parent.parent.parent
        FASTREID_DIR = ROOT_DIR / "model_lab" / "vendor" / "fast-reid"
        if str(FASTREID_DIR) not in sys.path:
            sys.path.insert(0, str(FASTREID_DIR))
            
        from fastreid.config import get_cfg
        from fastreid.modeling import build_model
        
        reid_cfg = get_cfg()
        reid_cfg.merge_from_file(str(FASTREID_DIR / 'configs' / 'VeRi' / 'sbs_R50-ibn.yml'))
        reid_cfg.MODEL.DEVICE = "cpu"
        reid_cfg.MODEL.BACKBONE.PRETRAIN = False
        reid_cfg.MODEL.HEADS.NUM_CLASSES = 575
        
        reid_model = build_model(reid_cfg)
        model_path = str(ROOT_DIR / 'model_lab' / 'models' / 'veri_sbs_R50-ibn.pth')
        
        state = torch.load(model_path, map_location='cpu', weights_only=True)['model']
        state['heads.weight'] = state.pop('heads.classifier.weight')
        state.pop('heads.bnneck.num_batches_tracked', None)
        
        for name, buffer in [('pixel_mean', reid_model.pixel_mean), ('pixel_std', reid_model.pixel_std)]:
            source = state.pop(name)
            
        reid_model.load_state_dict(state, strict=False)
        reid_model.eval()
        REID_INPUT_SIZE = tuple(reid_cfg.INPUT.SIZE_TEST)
        log.info("[ANPR] FastReID model loaded successfully.")
    except Exception as e:
        log.warning(f"[ANPR] Could not load FastReID: {e}")

# ── Indian plate regex validator ──────────────────────────────────────────────
# Matches: GJ05AB1234 / MH12CD5678 / DL3CAB1234
PLATE_PATTERN = re.compile(
    r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$'
)

def is_valid_indian_plate(text: str) -> bool:
    cleaned = text.upper().replace(" ", "").replace("-", "")
    return bool(PLATE_PATTERN.match(cleaned))

def normalize_plate(text: str) -> str:
    """Normalize common OCR confusions for Indian plates."""
    cleaned = text.upper().replace(" ", "").replace("-", "")
    # Common OCR errors: O→0 in number positions, 0→O in letter positions
    # Apply heuristic: positions 2-3 are digits, 4-5-6 are letters
    if len(cleaned) >= 6:
        # State code (2 letters) — keep letters
        state = cleaned[:2]
        # Digits after state code
        rest = cleaned[2:]
        # Find where letters start again
        corrected = state
        for i, ch in enumerate(rest):
            if i < 2:  # number part
                corrected += ch.replace('O', '0').replace('I', '1')
            else:  # alpha + final digits
                corrected += ch
        return corrected
    return cleaned

# ── Per-camera ANPR state ─────────────────────────────────────────────────────
# track_id → list of (plate_crop_gray, sharpness_score)
_frame_buffers: dict = defaultdict(list)
# track_id → list of plate reading strings (for voting)
_plate_readings: dict = defaultdict(list)
# track_id → final confirmed plate (once voted)
_confirmed_plates: dict = {}

BUFFER_SIZE     = 30   # Collect up to 30 frames per tracked vehicle
MIN_FRAMES_OCR  = 5    # Start attempting OCR after 5 frames
VOTE_THRESHOLD  = 0.5  # Majority must agree (>50%) for confirmation


def _compute_sharpness(gray_img: np.ndarray) -> float:
    """Laplacian variance — higher = sharper image."""
    return float(cv2.Laplacian(gray_img, cv2.CV_64F).var())


def _enhance_plate(crop_bgr: np.ndarray) -> np.ndarray:
    """
    Full plate enhancement pipeline:
    1. 4× LANCZOS upscale
    2. Grayscale
    3. CLAHE contrast enhancement
    4. Bilateral filter (denoise, preserve edges)
    5. Adaptive threshold → clean binary image
    """
    # Step 1: Upscale 4×
    h, w = crop_bgr.shape[:2]
    if w < 10 or h < 5:
        return None
    upscaled = cv2.resize(crop_bgr, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)

    # Step 2: Grayscale
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)

    # Step 3: CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    # Step 4: Bilateral denoising
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

    # Step 5: Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 13, 3
    )
    return thresh


def _run_ocr(enhanced_img: np.ndarray) -> tuple[str, float]:
    """Run EasyOCR and return (plate_text, confidence)."""
    if ocr_reader is None or enhanced_img is None:
        return "", 0.0
    try:
        results = ocr_reader.readtext(
            enhanced_img,
            detail=1,
            allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            paragraph=False,
            min_size=8,
            text_threshold=0.5,
        )
        if not results:
            return "", 0.0
        # Combine all text boxes into one string
        full_text = "".join([r[1] for r in results]).upper().replace(" ", "")
        avg_conf  = float(np.mean([r[2] for r in results]))
        return full_text, avg_conf
    except Exception as e:
        log.debug(f"[OCR] Error: {e}")
        return "", 0.0


def _vote_plate(readings: list[str]) -> tuple[str, float]:
    """
    Majority voting across multiple OCR readings.
    Returns (best_plate, vote_fraction).
    """
    valid = [normalize_plate(r) for r in readings if is_valid_indian_plate(r)]
    if not valid:
        return "", 0.0
    counter = Counter(valid)
    best, count = counter.most_common(1)[0]
    return best, round(count / len(readings), 2)


def _process_anpr_for_box(
    frame: np.ndarray,
    track_id: int,
    x1: int, y1: int, x2: int, y2: int,
    camera_id: str
):
    """
    Core ANPR logic per tracked vehicle.
    Called every frame for each tracked bounding box.
    Returns confirmed plate string if ready, else None.
    """
    # If already confirmed for this track, skip heavy processing
    if track_id in _confirmed_plates:
        return _confirmed_plates[track_id]

    # ── Plate region crop ─────────────────────────────────────────────────────
    # Indian plates are in the lower ~18% of the vehicle bounding box
    box_h = y2 - y1
    box_w = x2 - x1
    if box_h < 30 or box_w < 40:
        return None  # Too small to see a plate

    plate_y1 = y2 - max(int(box_h * 0.22), 15)
    plate_y2 = y2
    plate_x1 = x1 + int(box_w * 0.1)
    plate_x2 = x2 - int(box_w * 0.1)

    plate_crop = frame[plate_y1:plate_y2, plate_x1:plate_x2]
    if plate_crop.size == 0:
        return None

    # ── Sharpness scoring ─────────────────────────────────────────────────────
    gray_crop = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    sharpness  = _compute_sharpness(gray_crop)
    _frame_buffers[track_id].append((plate_crop.copy(), sharpness))

    # ── Periodic OCR on best frame so far ─────────────────────────────────────
    buf = _frame_buffers[track_id]
    if len(buf) >= MIN_FRAMES_OCR and len(buf) % 5 == 0:
        # Pick sharpest frame from buffer
        best_crop, best_score = max(buf, key=lambda x: x[1])

        # Only attempt OCR if image is reasonably sharp
        if best_score > 80.0:
            enhanced = _enhance_plate(best_crop)
            text, conf = _run_ocr(enhanced)
            if text and conf > 0.4:
                _plate_readings[track_id].append(text)
                log.info(f"[OCR] track={track_id} raw='{text}' conf={conf:.2f}")

    # ── Voting: finalize after BUFFER_SIZE frames ─────────────────────────────
    if len(buf) >= BUFFER_SIZE:
        final_plate, vote_frac = _vote_plate(_plate_readings[track_id])
        

        if final_plate:
            _confirmed_plates[track_id] = final_plate
            log.info(f"[ANPR] ✅ Confirmed plate={final_plate} vote={vote_frac:.0%} camera={camera_id}")

            # ── FastReID Appearance Embedding ───────────────────────────────────
            embedding = None
            vehicle_crop = frame[max(0, y1):y2, max(0, x1):x2]
            if "reid_model" in globals() and reid_model is not None and vehicle_crop.size > 0:
                try:
                    import torch
                    rgb = cv2.cvtColor(cv2.resize(vehicle_crop, REID_INPUT_SIZE, interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB)
                    tensor = torch.from_numpy(rgb.transpose(2,0,1).copy()).float().unsqueeze(0)
                    with torch.no_grad():
                        feat = reid_model(tensor)
                        feat = torch.nn.functional.normalize(feat, dim=1, p=2)
                        embedding = feat.cpu().numpy()[0].tolist()
                except Exception as e:
                    log.warning(f"[ANPR] FastReID error: {e}")

            # ── Record sighting in vehicle journey tracker ─────────────────────
            try:
                from routers.vehicles import record_vehicle_sighting
                record_vehicle_sighting(
                    plate=final_plate,
                    camera_id=camera_id,
                    pts_ms=float(cv2.getTickCount() / cv2.getTickFrequency() * 1000),
                    bbox=[x1, y1, x2, y2],
                    confidence=vote_frac,
                    embedding=embedding
                )
            except Exception as e:
                log.warning(f"[ANPR] Could not record sighting: {e}")

            # ── Auto-generate event from ANPR detection ────────────────────────
            try:
                from data.database import add_event, CAMERAS
                import uuid
                from datetime import datetime
                camera_meta = next((c for c in CAMERAS if c["id"] == camera_id), {})
                add_event({
                    "id": f"EVT_ANPR_{uuid.uuid4().hex[:6].upper()}",
                    "camera_id": camera_id,
                    "camera_name": camera_meta.get("name", camera_id),
                    "zone": camera_meta.get("zone", "highway"),
                    "timestamp": datetime.now(),
                    "event_type": "vehicle_detected",
                    "severity": "low",
                    "status": "pending_review",
                    "description": f"ANPR identified plate {final_plate} at {camera_meta.get('name', camera_id)} with {vote_frac:.0%} confidence.",
                    "person_id": None,
                    "clip_ref": f"/streams/{camera_id.lower()}_analyzed.mp4",
                    "thumbnail": "/evidence/EVT_07D1446F.jpg",
                    "confidence": vote_frac,
                    "duration_sec": 2.0,
                    "vlm_analysis": {
                        "summary": f"ANPR system read plate {final_plate}. Confidence: {vote_frac:.0%}. Vehicle tracked across {len(buf)} frames. Best frame sharpness: {max(b[1] for b in buf):.1f}.",
                        "activity": f"Vehicle {final_plate} detected",
                        "objects_detected": ["vehicle", "license_plate"],
                        "plate": final_plate,
                        "ocr_readings": _plate_readings[track_id],
                        "vote_fraction": vote_frac,
                        "frames_analyzed": len(buf),
                    }
                })
                log.info(f"[ANPR] Event created for plate {final_plate}")
            except Exception as e:
                log.warning(f"[ANPR] Could not add event: {e}")

            # Cleanup buffer for this track to free memory
            _frame_buffers.pop(track_id, None)
            _plate_readings.pop(track_id, None)
            return final_plate

        elif len(buf) >= BUFFER_SIZE:
            # Could not confirm after max frames — cleanup and give up
            _frame_buffers.pop(track_id, None)
            _plate_readings.pop(track_id, None)

    return _confirmed_plates.get(track_id)


# ── Bounding box color helper ─────────────────────────────────────────────────
_CLASS_COLORS = {
    0: (0,   215, 255),   # Person — Yellow BGR
    1: (255, 191,   0),   # Bicycle/Auto — Cyan
    2: (255, 191,   0),   # Car — Cyan
    3: (255, 191,   0),   # Motorcycle — Cyan
    5: (0,   255,   0),   # Bus — Green
    7: (0,   255,   0),   # Truck — Green
}
_VEHICLE_CLASSES = {1, 2, 3, 5, 7}   # Classes that may have a plate


def _generate_connection_frames(camera_id: str, url: str):
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        log.warning(f"[Stream] Could not open RTSP for {camera_id}")
        return

    frame_count = 0
    # Reset per-camera tracking state on reconnect
    _frame_buffers.clear()
    _plate_readings.clear()

    while True:
        success, frame = cap.read()
        if not success:
            log.warning(f"[{camera_id}] Stream failed or ended.")
            break

        frame_count += 1

        # ── Skip alternate frames to halve bandwidth load ─────────────────────
        if frame_count % 2 != 0:
            continue

        frame = cv2.resize(frame, (1280, 720))

        if model:
            # ── ByteTrack: persistent object IDs across frames ────────────────
            # persist=True → tracker state maintained between calls
            # tracker="bytetrack.yaml" → uses the built-in ByteTrack config
            results = model.track(
                frame,
                persist=True,
                conf=0.30,
                classes=[0, 1, 2, 3, 5, 7],
                tracker="bytetrack.yaml",
                verbose=False,
            )

            if results and results[0].boxes is not None:
                boxes = results[0].boxes

                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls  = int(box.cls[0])
                    conf = float(box.conf[0])
                    # track_id may be None on first frame — fall back to -1
                    tid  = int(box.id[0]) if box.id is not None else -1

                    color = _CLASS_COLORS.get(cls, (180, 180, 180))
                    label = f"{model.names[cls].upper()} {conf:.0%}"
                    if tid >= 0:
                        label += f"  #{tid}"

                    # ── Draw professional bounding box ────────────────────────
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                    text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                    cv2.rectangle(frame, (x1, y1 - 18), (x1 + text_size[0] + 6, y1), color, -1)
                    cv2.putText(frame, label, (x1 + 3, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)

                    # ── ANPR pipeline for vehicle classes ─────────────────────
                    if cls in _VEHICLE_CLASSES and tid >= 0:
                        confirmed = _process_anpr_for_box(
                            frame, tid, x1, y1, x2, y2, camera_id
                        )

                        if confirmed:
                            # Render confirmed plate on-screen
                            pw, _ = cv2.getTextSize(confirmed, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                            px1 = x1
                            py1 = y2 + 2
                            px2 = x1 + pw[0] + 10
                            py2 = y2 + 18

                            cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 255, 255), -1)
                            cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 0), 1)
                            cv2.putText(frame, confirmed, (px1 + 4, py2 - 3),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 128), 1, cv2.LINE_AA)

                # ── Update live detection snapshot for this camera ─────────────
                # This is consumed by /stream/{id}/detections endpoint
                # which the chatbot reads for real scene context
                class_names = [model.names[int(b.cls[0])] for b in boxes]
                _live_detections[camera_id] = {
                    "camera_id": camera_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_objects": len(boxes),
                    "persons":  sum(1 for n in class_names if n == "person"),
                    "vehicles": sum(1 for n in class_names if n in ["car","motorcycle","bus","truck","bicycle"]),
                    "classes":  list(Counter(class_names).items()),  # [("car",3),("person",2),...]
                    "confirmed_plates": list(_confirmed_plates.values()),
                }

        # ── MJPEG encode and yield ─────────────────────────────────────────────
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
        if not ret:
            continue

        try:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except GeneratorExit:
            log.info(f"[{camera_id}] Processed stream client disconnected; releasing capture.")
            cap.release()
            raise

    cap.release()


def generate_frames(camera_id: str, url: str):
    """Reconnect a dropped vendor feed without ending the browser's MJPEG response."""
    failures = 0
    while failures < 5:
        delivered_frame = False
        connection = _generate_connection_frames(camera_id, url)
        try:
            for chunk in connection:
                delivered_frame = True
                failures = 0
                yield chunk
        finally:
            connection.close()
        failures += 1
        delay = min(2 ** (failures - 1), 8)
        log.warning(f"[{camera_id}] Reconnecting registered stream in {delay}s ({failures}/5).")
        time.sleep(delay)
        if delivered_frame:
            continue
    log.error(f"[{camera_id}] Registered stream unavailable after 5 reconnect attempts.")


def _generate_raw_connection_frames(camera_id: str, url: str):
    """Relay a low-rate CCTV preview without running detection or drawing overlays."""
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        log.warning(f"[Raw stream] Could not open RTSP for {camera_id}")
        return

    last_frame_at = 0.0
    try:
        while True:
            success, frame = cap.read()
            if not success:
                log.warning(f"[{camera_id}] Raw stream failed or ended.")
                break

            now = time.monotonic()
            if now - last_frame_at < 0.2:  # Dashboard previews are capped at 5 FPS.
                continue
            last_frame_at = now

            height, width = frame.shape[:2]
            if width > 640:
                preview_height = max(1, round(height * 640 / width))
                frame = cv2.resize(frame, (640, preview_height), interpolation=cv2.INTER_AREA)

            encoded, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if encoded:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        cap.release()


def generate_raw_frames(camera_id: str, url: str):
    """Reconnect raw dashboard previews without invoking the analytics pipeline."""
    failures = 0
    while failures < 5:
        delivered_frame = False
        connection = _generate_raw_connection_frames(camera_id, url)
        try:
            for chunk in connection:
                delivered_frame = True
                failures = 0
                yield chunk
        finally:
            connection.close()
        failures += 1
        delay = min(2 ** (failures - 1), 8)
        log.warning(f"[{camera_id}] Reconnecting raw preview in {delay}s ({failures}/5).")
        time.sleep(delay)
        if delivered_frame:
            continue
    log.error(f"[{camera_id}] Raw preview unavailable after 5 reconnect attempts.")


@router.get("/{camera_id}/raw")
def raw_video_feed(camera_id: str):
    """Browser-compatible CCTV preview with no inference or annotations."""
    try:
        url, _ = resolve_worker_stream(camera_id)
    except RegistryClientError as exc:
        raise HTTPException(503, str(exc)) from None
    return StreamingResponse(
        generate_raw_frames(camera_id, url),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{camera_id}")
def video_feed(camera_id: str):
    """
    MJPEG stream endpoint.
    Browser renders this directly via <img> tag.
    Pipeline: RTSP → YOLO11n + ByteTrack → ANPR → OCR → EasyOCR voting → Events
    """
    try:
        url, _ = resolve_worker_stream(camera_id)
    except RegistryClientError as exc:
        raise HTTPException(503, str(exc)) from None
    return StreamingResponse(
        generate_frames(camera_id, url),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/{camera_id}/detections")
def get_live_detections(camera_id: str):
    """
    Returns real-time YOLO detection summary for a camera.
    Used by the Sentinel Copilot chatbot for live scene context.
    """
    data = _live_detections.get(camera_id)
    if not data:
        return {
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "total_objects": 0,
            "persons": 0,
            "vehicles": 0,
            "classes": [],
            "confirmed_plates": [],
            "status": "stream_not_active"
        }
    return {**data, "status": "live"}
