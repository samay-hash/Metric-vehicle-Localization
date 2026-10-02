import requests
import uuid
import time
from datetime import datetime, timezone

BACKEND_URL = "http://localhost:8000/events/ingest"

# Let's create a realistic journey for the stolen vehicle (GJ01AB1234)
# Route: Navrangpura -> Law Garden -> Ellis Bridge -> Paldi Circle -> Kankaria Lake
journey_cameras = ["cam49", "cam35", "cam39", "cam04", "cam31"]
plate = "GJ01AB1234"

print("Injecting LIVE DEMO events into the Sentinel Grid...")
for i, cam in enumerate(journey_cameras):
    event = {
        "id": f"EVT_{uuid.uuid4().hex[:8].upper()}",
        "camera_id": cam,
        "track_id": 9999 + i,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": "vehicle_detected",
        "severity": "medium",
        "bbox": [100, 150, 300, 250],
        "confidence": 0.98,
        "status": "pending_review",
        "plate": plate,
        "duration_frames": 45
    }
    
    try:
        res = requests.post(BACKEND_URL, json=event)
        if res.status_code == 200:
            print(f"✅ Vehicle detected on {cam.upper()} | Watchlist Match: {res.json().get('watchlist_matched')}")
        else:
            print(f"❌ Failed to ingest event: {res.text}")
    except Exception as e:
        print(f"⚠️ Error: {e}")
    
    time.sleep(1) # simulate a slight delay between sightings

print("\n🚀 DONE! The database is now loaded with live events.")
print("Go to http://localhost:5173/sentinel")
print("1. Watch the right sidebar (Live Detected Plates) fill up!")
print("2. Search 'GJ01AB1234' on the Map Trace to see the journey.")
