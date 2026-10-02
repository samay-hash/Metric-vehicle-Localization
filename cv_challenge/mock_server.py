from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import os, glob

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PRED_PATH   = "cv_challenge/kaggle_data/predictions.csv"
GT_PATH     = "cv_challenge/kaggle_data/targets.csv"
VIZ_DIR     = "cv_challenge/visualisations"
TRAIN_DIR   = "cv_challenge/kaggle_data/train_images"

# ─── Load & merge predictions with ground truth ───────────────────────────────
def load_merged(limit: int = 0):
    try:
        pred = pd.read_csv(PRED_PATH)
        gt   = pd.read_csv(GT_PATH)[["target_id","image_id","x1","y1","x2","y2","gt_x_m","gt_z_m"]]
        df   = pd.merge(pred, gt, on=["target_id","image_id"])
        df["err_z"]   = (df["z_m"] - df["gt_z_m"]).abs().round(3)
        df["err_x"]   = (df["x_m"] - df["gt_x_m"]).abs().round(3)
        df["abs_rel"] = (df["err_z"] / df["gt_z_m"].abs()).round(3)
        if limit:
            df = df.head(limit)
        return df
    except Exception as e:
        return pd.DataFrame()

# ─── Build camera list from real visualisation images ────────────────────────
def _build_cameras():
    imgs = sorted(glob.glob(f"{VIZ_DIR}/viz_*.jpg"))
    cameras = []
    for i, path in enumerate(imgs):
        fname   = os.path.basename(path)               # viz_ID_044fbdda4.jpg
        img_id  = fname.replace("viz_", "").replace(".jpg", "")  # ID_044fbdda4
        cameras.append({
            "id":           img_id,
            "external_id":  img_id,
            "name":         f"CV Cam {i+1:02d} · {img_id[:10]}",
            "enabled":      True,
            "source_state": "approved",
            "stream":       {"configured": True},
            "health":       {"status": "online"},
            "revision":     1,
            "location":     "PKU Autonomous Driving Dataset",
            "zone":         "highway",
        })
    return cameras

# ─── Load predictions ─────────────────────────────────────────────────────────
def load_preds():
    try:
        return pd.read_csv(PRED_PATH)
    except Exception:
        return pd.DataFrame(columns=["image_id", "target_id", "x_m", "z_m", "confidence"])

def _make_events(df, limit=10):
    events = []
    for i, row in df.head(limit).iterrows():
        conf = float(row["confidence"])
        sev  = "critical" if conf < 0.4 else ("high" if conf < 0.6 else "low")
        events.append({
            "id":          str(i),
            "camera_id":   str(row["image_id"]),
            "camera_name": f"Image {str(row['image_id'])[:12]}",
            "event_type":  "suspicious_motion",
            "severity":    sev,
            "description": f"Z={float(row['z_m']):.1f}m  X={float(row['x_m']):.1f}m  conf={conf:.2f}",
            "timestamp":   "2026-10-02T12:00:00Z",
            "status":      "pending_review" if conf < 0.5 else "resolved",
        })
    return events

# ─── System stats ─────────────────────────────────────────────────────────────
@app.get("/reports/system/stats")
def sys_stats():
    df       = load_preds()
    total    = len(df)
    critical = int((df["confidence"] < 0.5).sum()) if total else 0
    return {
        "critical_events":  critical,
        "active_incidents": 2,
        "events_today":     total,
        "pending_review":   critical,
        "hardware":         {"cpu": 14, "ram": 43},
    }

# ─── Events ──────────────────────────────────────────────────────────────────
@app.get("/events/")
def get_events(limit: int = 10, severity: str = None, status: str = None):
    df     = load_preds()
    events = _make_events(df, limit=max(limit, 20))
    if severity == "critical":
        events = [e for e in events if e["severity"] == "critical"]
    if status == "pending_review":
        events = [e for e in events if e["status"] == "pending_review"]
    return {"events": events[:limit], "total": len(events)}

@app.get("/events/live/feed")
def live_feed():
    return {"feed": _make_events(load_preds(), limit=5)}

# ─── Cameras (real images) ────────────────────────────────────────────────────
@app.get("/registry/cameras")
@app.get("/api/v1/cameras")
def registry_cameras(limit: int = 500):
    cameras = _build_cameras()
    return {"data": cameras[:limit], "total": len(cameras)}

@app.get("/api/v1/fleet/health")
def fleet_health():
    n = len(_build_cameras())
    return {
        "total":      n,
        "counts":     {"healthy": n, "stale": 0, "unmonitored": 0},
        "checked_at": "2026-10-02T12:00:00Z",
    }

# ─── Stream: serve real annotated visualisation images ───────────────────────
@app.get("/stream/{camera_id}/raw")
@app.get("/stream/{camera_id}")
def stream(camera_id: str):
    # 1. Try exact visualisation match
    viz = f"{VIZ_DIR}/viz_{camera_id}.jpg"
    if os.path.exists(viz):
        return FileResponse(viz)

    # 2. Try raw train image
    raw = f"{TRAIN_DIR}/{camera_id}.jpg"
    if os.path.exists(raw):
        return FileResponse(raw)

    # 3. Fallback: first available visualisation
    imgs = sorted(glob.glob(f"{VIZ_DIR}/viz_*.jpg"))
    if imgs:
        return FileResponse(imgs[0])

    return JSONResponse({"error": "no image"}, status_code=404)

# ─── Vehicles ─────────────────────────────────────────────────────────────────
@app.get("/vehicles/active")
def vehicles_active(limit: int = 20):
    df = load_preds()
    vehicles = [
        {
            "id":         str(row["target_id"]),
            "image_id":   str(row["image_id"]),
            "x_m":        round(float(row["x_m"]), 2),
            "z_m":        round(float(row["z_m"]), 2),
            "confidence": round(float(row["confidence"]), 3),
        }
        for _, row in df.head(limit).iterrows()
    ]
    return {"vehicles": vehicles, "total": len(df)}

@app.get("/vehicles/cameras")
def vehicles_cameras():
    return {"cameras": _build_cameras(), "total": len(_build_cameras())}

# ─── Incidents ────────────────────────────────────────────────────────────────
@app.get("/investigation/incidents")
def get_incidents():
    return {"incidents": [
        {"id": "inc_1", "title": "Low-confidence cluster detected", "status": "open",
         "severity": "high", "created_at": "2026-10-02T10:00:00Z"},
        {"id": "inc_2", "title": "Edge-of-frame vehicle occlusion", "status": "under_investigation",
         "severity": "medium", "created_at": "2026-10-02T11:00:00Z"},
    ]}

# ─── Reports ──────────────────────────────────────────────────────────────────
@app.get("/reports/eod")
def eod_report():
    df    = load_preds()
    cams  = _build_cameras()
    return {
        "date":         "2026-10-02",
        "total_events": len(df),
        "critical":     int((df["confidence"] < 0.4).sum()),
        "resolved":     int((df["confidence"] >= 0.6).sum()),
        "summary":      "Roostr CV Challenge evaluation complete. Width+Height Ensemble method used.",
        "cameras":      [{"id": c["id"], "name": c["name"], "events": len(df)//len(cams)} for c in cams],
    }

# ─── Access management ────────────────────────────────────────────────────────
@app.get("/api/v1/access/users")
def access_users():
    return {"data": [{"id": "u1", "email": "admin@roostr.ai",
                      "display_name": "Roostr Admin", "roles": ["master_admin"]}], "total": 1}

@app.get("/api/v1/access/audit")
def security_audit():
    return {"data": [
        {"id": "a1", "action": "predict.run",  "user": "admin@roostr.ai",
         "timestamp": "2026-10-02T12:00:00Z", "details": "CV pipeline executed on 100 images"},
        {"id": "a2", "action": "evaluate.run", "user": "admin@roostr.ai",
         "timestamp": "2026-10-02T12:01:00Z", "details": "MAE_Z=16.70m, MAE_X=5.12m"},
    ], "total": 2}

# ─── WebSocket ────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass

# ─── CV Challenge Specific Endpoints ─────────────────────────────────────────
@app.get("/cv/metrics")
def cv_metrics():
    """Overall evaluation metrics from predictions vs ground truth."""
    df = load_merged()
    if df.empty:
        return {"error": "no data"}
    return {
        "total_predictions": len(df),
        "total_images": int(df["image_id"].nunique()),
        "mae_z":   round(float(df["err_z"].mean()), 3),
        "mae_x":   round(float(df["err_x"].mean()), 3),
        "rmse_z":  round(float((df["err_z"]**2).mean()**0.5), 3),
        "abs_rel": round(float(df["abs_rel"].mean()), 3),
        "p90_z":   round(float(df["err_z"].quantile(0.9)), 3),
        "high_conf_mae_z": round(float(df[df["confidence"] >= df["confidence"].median()]["err_z"].mean()), 3),
        "low_conf_mae_z":  round(float(df[df["confidence"] < df["confidence"].median()]["err_z"].mean()), 3),
        "method": "Width+Height Ensemble (Method C)",
    }

@app.get("/cv/results")
def cv_results(limit: int = 50, image_id: str = None):
    """Per-prediction results: predicted vs ground truth."""
    df = load_merged()
    if df.empty:
        return {"results": [], "total": 0}
    if image_id:
        df = df[df["image_id"] == image_id]
    results = []
    for _, row in df.head(limit).iterrows():
        results.append({
            "image_id":   str(row["image_id"]),
            "target_id":  str(row["target_id"]),
            "pred_x":     round(float(row["x_m"]), 2),
            "pred_z":     round(float(row["z_m"]), 2),
            "gt_x":       round(float(row["gt_x_m"]), 2),
            "gt_z":       round(float(row["gt_z_m"]), 2),
            "err_z":      round(float(row["err_z"]), 2),
            "err_x":      round(float(row["err_x"]), 2),
            "confidence": round(float(row["confidence"]), 3),
            "bbox":       [int(row["x1"]), int(row["y1"]), int(row["x2"]), int(row["y2"])],
            "has_image":  os.path.exists(f"{VIZ_DIR}/viz_{row['image_id']}.jpg"),
        })
    return {"results": results, "total": len(df)}

@app.get("/cv/images")
def cv_images():
    """List all annotated visualisation images."""
    imgs = sorted(glob.glob(f"{VIZ_DIR}/viz_*.jpg"))
    items = []
    for path in imgs:
        fname  = os.path.basename(path)
        img_id = fname.replace("viz_", "").replace(".jpg", "")
        items.append({
            "image_id": img_id,
            "url":      f"/cv/image/{img_id}",
        })
    return {"images": items, "total": len(items)}

@app.get("/cv/image/{image_id}")
def cv_image(image_id: str):
    """Serve the annotated visualisation image for an image_id."""
    path = f"{VIZ_DIR}/viz_{image_id}.jpg"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    # fallback: raw train image
    raw = f"{TRAIN_DIR}/{image_id}.jpg"
    if os.path.exists(raw):
        return FileResponse(raw, media_type="image/jpeg")
    return JSONResponse({"error": "not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
