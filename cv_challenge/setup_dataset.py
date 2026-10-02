import os
import urllib.request
import pandas as pd
import cv2

def setup_dummy_dataset():
    base_dir = "cv_challenge/dataset"
    img_dir = os.path.join(base_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    
    print("Downloading sample images...")
    # Download a reliable traffic image (Ultralytics bus.jpg)
    img1_path = os.path.join(img_dir, "bus.jpg")
    if not os.path.exists(img1_path):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/bus.jpg", img1_path)
    
    # Let's use the same image duplicated to act as 2 samples
    img2_path = os.path.join(img_dir, "bus_2.jpg")
    if not os.path.exists(img2_path):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/bus.jpg", img2_path)
        
    print("Generating targets.csv and calibration.csv...")
    
    # Read image to get dimensions
    img = cv2.imread(img1_path)
    h, w, _ = img.shape
    
    # Dummy bounding boxes (assuming a vehicle in bus.jpg)
    # The bus in bus.jpg is roughly at x1=50, y1=390, x2=745, y2=900 (it's a large bus)
    # Let's just define arbitrary boxes for testing the pipeline
    targets = [
        {"image_id": "bus", "target_id": "car_1", "x1": 50, "y1": 400, "x2": 745, "y2": 900},
        {"image_id": "bus_2", "target_id": "car_2", "x1": 100, "y1": 450, "x2": 600, "y2": 850}
    ]
    pd.DataFrame(targets).to_csv(os.path.join(base_dir, "targets.csv"), index=False)
    
    # Dummy calibration matrix (PKU autonomous driving approx)
    calib = [
        {"image_id": "bus", "fx": 2304.54, "fy": 2305.87, "cx": w/2, "cy": h/2, "width": w, "height": h},
        {"image_id": "bus_2", "fx": 2304.54, "fy": 2305.87, "cx": w/2, "cy": h/2, "width": w, "height": h}
    ]
    pd.DataFrame(calib).to_csv(os.path.join(base_dir, "calibration.csv"), index=False)
    
    print(f"Mini dataset created at {base_dir}")

if __name__ == "__main__":
    setup_dummy_dataset()
