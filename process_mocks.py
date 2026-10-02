import cv2
import os
from ultralytics import YOLO

base_dir = "/Users/samaysamrat/bankcctv/frontend/public/streams"
model = YOLO('yolov8n.pt')

for i in range(1, 9):
    in_path = os.path.join(base_dir, f"cam{i}.mp4")
    out_path = os.path.join(base_dir, f"cam{i}_analyzed.mp4")
    if not os.path.exists(in_path):
        continue
    
    cap = cv2.VideoCapture(in_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    
    print(f"Processing {in_path}...")
    frames_processed = 0
    while True:
        ret, frame = cap.read()
        if not ret or frames_processed > 300: # process max 300 frames (12s) to save time
            break
        
        # simple YOLO detection and drawing green boxes
        results = model.predict(frame, classes=[0], verbose=False)
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, "PERSON", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
        out.write(frame)
        frames_processed += 1
        
    cap.release()
    out.release()
    print(f"Saved {out_path}")
