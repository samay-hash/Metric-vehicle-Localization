"""
Download first N images from PKU Autonomous Driving dataset using Kaggle API directly.
Uses the Kaggle SDK to download individual train images.
"""
import os
import subprocess
import pandas as pd

KAGGLE_TOKEN = "KGAT_b82f825e76754e5fed48567e2e6f1225"
os.environ["KAGGLE_API_TOKEN"] = KAGGLE_TOKEN

BASE_DIR = "cv_challenge/kaggle_data"
IMG_DIR = os.path.join(BASE_DIR, "train_images")
os.makedirs(IMG_DIR, exist_ok=True)

# Read train.csv to get image IDs
df = pd.read_csv(os.path.join(BASE_DIR, "train.csv"))
print(f"Total images in dataset: {len(df)}")

# Download first 100 images only (~400-500MB)
N = 100
image_ids = df["ImageId"].tolist()[:N]

print(f"Downloading {N} images...")
success = 0
for i, img_id in enumerate(image_ids):
    img_path = os.path.join(IMG_DIR, f"{img_id}.jpg")
    if os.path.exists(img_path):
        success += 1
        continue
    
    cmd = [
        "kaggle", "competitions", "download",
        "pku-autonomous-driving",
        "-f", f"train_images/{img_id}.jpg",
        "-p", IMG_DIR
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        success += 1
        if (i+1) % 10 == 0:
            print(f"  Downloaded {i+1}/{N}...")
    else:
        print(f"  FAILED: {img_id} - {result.stderr.strip()}")

print(f"\nDone! {success}/{N} images downloaded to {IMG_DIR}")
print(f"Disk usage: {os.popen(f'du -sh {IMG_DIR}').read().strip()}")
