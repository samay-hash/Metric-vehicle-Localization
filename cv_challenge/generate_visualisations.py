"""
Generate annotated visualisation images for each method.
Draws: original image + vehicle bbox + predicted Z vs GT Z label.
"""
import os, sys
import numpy as np
import pandas as pd
import cv2

BASE_DIR = "cv_challenge/kaggle_data"
IMG_DIR  = os.path.join(BASE_DIR, "train_images")
VIZ_DIR  = "cv_challenge/visualisations"
os.makedirs(VIZ_DIR, exist_ok=True)

# Load ablation results
res  = pd.read_csv(os.path.join(BASE_DIR, "ablation_v2.csv"))
gt   = pd.read_csv(os.path.join(BASE_DIR, "targets.csv"))
df   = pd.merge(res, gt[["target_id","image_id","x1","y1","x2","y2"]], on="target_id")

COLORS = {
    "gt":   (0,  255, 0),      # green
    "za":   (0,  100, 255),    # orange-ish (bad)
    "zb":   (255, 200, 0),     # yellow
    "zc":   (0,  200, 255),    # cyan (best)
}

def draw_vehicle(img, x1, y1, x2, y2, label, color, thickness=2):
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
    # Background for text
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    tx, ty = int(x1), int(y1) - 6
    cv2.rectangle(img, (tx, ty - th - 4), (tx + tw + 4, ty + 4), color, -1)
    cv2.putText(img, label, (tx + 2, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (0, 0, 0), 2, cv2.LINE_AA)

def add_legend(img):
    entries = [
        ("GT",      COLORS["gt"]),
        ("Method A (Naive Depth)", COLORS["za"]),
        ("Method B (Width Prior)", COLORS["zb"]),
        ("Method C (Ensemble)",    COLORS["zc"]),
    ]
    y0 = 20
    for i, (label, color) in enumerate(entries):
        y = y0 + i * 28
        cv2.rectangle(img, (10, y), (30, y + 18), color, -1)
        cv2.putText(img, label, (38, y + 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)

# Pick 10 diverse images to visualise
sample_imgs = df.groupby("image_id").filter(lambda g: len(g) >= 2)
unique_imgs = sample_imgs["image_id"].unique()[:10]

generated = 0
for img_id in unique_imgs:
    ip = os.path.join(IMG_DIR, f"{img_id}.jpg")
    if not os.path.exists(ip): continue

    img = cv2.imread(ip)
    if img is None: continue
    # Resize to half for readable output
    h, w = img.shape[:2]
    scale = min(1.0, 1600 / w)
    img = cv2.resize(img, (int(w*scale), int(h*scale)))

    group = df[df["image_id"] == img_id]
    for _, row in group.iterrows():
        x1,y1,x2,y2 = row.x1*scale, row.y1*scale, row.x2*scale, row.y2*scale
        gt_z = row.gt_z

        # GT box (green)
        draw_vehicle(img, x1,y1,x2,y2, f"GT: {gt_z:.1f}m", COLORS["gt"])
        # Method C box (cyan, slightly inset)
        draw_vehicle(img, x1+4,y1+4,x2-4,y2-4,
                     f"C:{row.zc:.1f}m", COLORS["zc"], thickness=2)
        # Method B box (yellow, inset more)
        draw_vehicle(img, x1+8,y1+8,x2-8,y2-8,
                     f"B:{row.zb:.1f}m", COLORS["zb"], thickness=1)

    add_legend(img)
    out_path = os.path.join(VIZ_DIR, f"viz_{img_id}.jpg")
    cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    generated += 1
    print(f"  Saved: {out_path}")

print(f"\n✅ {generated} visualisations saved to {VIZ_DIR}/")
