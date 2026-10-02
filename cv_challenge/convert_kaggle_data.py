"""
Convert PKU Autonomous Driving train.csv (Kaggle format) to our pipeline format.
Kaggle format: model, yaw, pitch, roll, x, y, z (per vehicle in PredictionString)
Our format: targets.csv (image_id, target_id, x1, y1, x2, y2)
            calibration.csv (image_id, fx, fy, cx, cy, width, height)

Camera intrinsics from camera_intrinsic.txt:
  fx = 2304.5479, fy = 2305.8757, cx = 1686.2379, cy = 1354.9849
Image size (standard): 3384 x 2710
"""
import os
import numpy as np
import pandas as pd
import cv2

# Camera constants (from downloaded camera_intrinsic.txt)
FX = 2304.5479
FY = 2305.8757
CX = 1686.2379
CY = 1354.9849
IMG_W = 3384
IMG_H = 2710

BASE_DIR = "cv_challenge/kaggle_data"
IMG_DIR = os.path.join(BASE_DIR, "train_images")
OUT_DIR = BASE_DIR


def rotation_matrix_from_angles(yaw, pitch, roll):
    """Build 3x3 rotation matrix from euler angles."""
    Ry = np.array([[np.cos(yaw), 0, np.sin(yaw)],
                   [0, 1, 0],
                   [-np.sin(yaw), 0, np.cos(yaw)]])
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(pitch), -np.sin(pitch)],
                   [0, np.sin(pitch), np.cos(pitch)]])
    Rz = np.array([[np.cos(roll), -np.sin(roll), 0],
                   [np.sin(roll), np.cos(roll), 0],
                   [0, 0, 1]])
    return Ry @ Rx @ Rz


def project_3d_to_2d(x3d, y3d, z3d):
    """Project 3D camera coordinates to 2D image plane."""
    if z3d <= 0:
        return None, None
    u = int(FX * x3d / z3d + CX)
    v = int(FY * y3d / z3d + CY)
    return u, v


def get_vehicle_bbox_from_pose(x3d, y3d, z3d, half_w=1.0, half_h=0.75, half_d=2.2):
    """
    Approximate 2D bounding box from 3D position.
    Uses a fixed vehicle size prior to project corners onto image plane.
    Returns (x1, y1, x2, y2) or None if out of frame.
    """
    # 8 corners of the vehicle bounding box in camera space
    corners_3d = [
        [x3d - half_w, y3d - half_h, z3d - half_d],
        [x3d + half_w, y3d - half_h, z3d - half_d],
        [x3d - half_w, y3d + half_h, z3d - half_d],
        [x3d + half_w, y3d + half_h, z3d - half_d],
        [x3d - half_w, y3d - half_h, z3d + half_d],
        [x3d + half_w, y3d - half_h, z3d + half_d],
        [x3d - half_w, y3d + half_h, z3d + half_d],
        [x3d + half_w, y3d + half_h, z3d + half_d],
    ]
    us, vs = [], []
    for cx3, cy3, cz3 in corners_3d:
        if cz3 <= 0:
            continue
        u, v = project_3d_to_2d(cx3, cy3, cz3)
        if u is not None:
            us.append(u)
            vs.append(v)
    if len(us) < 2:
        return None
    x1, y1 = max(0, min(us)), max(0, min(vs))
    x2, y2 = min(IMG_W, max(us)), min(IMG_H, max(vs))
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)


def parse_prediction_string(pred_str):
    """Parse Kaggle PredictionString into list of vehicle poses."""
    vals = list(map(float, pred_str.strip().split()))
    vehicles = []
    # format: model_type(1), yaw(1), pitch(1), roll(1), x(1), y(1), z(1) = 7 per vehicle
    for i in range(0, len(vals), 7):
        if i + 6 >= len(vals):
            break
        model_type = int(vals[i])
        yaw, pitch, roll = vals[i+1], vals[i+2], vals[i+3]
        x3d, y3d, z3d = vals[i+4], vals[i+5], vals[i+6]
        vehicles.append({
            "model_type": model_type,
            "yaw": yaw, "pitch": pitch, "roll": roll,
            "x3d": x3d, "y3d": y3d, "z3d": z3d
        })
    return vehicles


def convert_dataset():
    df = pd.read_csv(os.path.join(BASE_DIR, "train.csv"))
    
    # Filter to only images we actually downloaded
    downloaded = set(f.replace(".jpg", "") for f in os.listdir(IMG_DIR) if f.endswith(".jpg"))
    print(f"Found {len(downloaded)} downloaded images.")
    df = df[df["ImageId"].isin(downloaded)]
    print(f"Processing {len(df)} images...")
    
    targets_rows = []
    calib_rows = []
    
    for _, row in df.iterrows():
        img_id = row["ImageId"]
        vehicles = parse_prediction_string(row["PredictionString"])
        
        # Check actual image size
        img_path = os.path.join(IMG_DIR, f"{img_id}.jpg")
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        
        for v_idx, v in enumerate(vehicles):
            bbox = get_vehicle_bbox_from_pose(v["x3d"], v["y3d"], v["z3d"])
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            targets_rows.append({
                "image_id": img_id,
                "target_id": f"{img_id}_v{v_idx}",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                # Store ground truth for evaluation
                "gt_x_m": round(v["x3d"], 3),
                "gt_z_m": round(v["z3d"], 3),
            })
        
        calib_rows.append({
            "image_id": img_id,
            "fx": FX, "fy": FY, "cx": CX, "cy": CY,
            "width": w, "height": h
        })
    
    targets_df = pd.DataFrame(targets_rows)
    calib_df = pd.DataFrame(calib_rows)
    
    targets_df.to_csv(os.path.join(OUT_DIR, "targets.csv"), index=False)
    calib_df.to_csv(os.path.join(OUT_DIR, "calibration.csv"), index=False)
    
    # Also save a version without gt for the actual predict run
    targets_df[["image_id","target_id","x1","y1","x2","y2"]].to_csv(
        os.path.join(OUT_DIR, "targets_no_gt.csv"), index=False
    )
    
    print(f"\n✅ Conversion done!")
    print(f"   targets.csv      : {len(targets_df)} vehicles from {len(calib_df)} images")
    print(f"   calibration.csv  : {len(calib_df)} entries")
    print(f"\nGround truth Z range: {targets_df['gt_z_m'].min():.1f}m – {targets_df['gt_z_m'].max():.1f}m")
    print(f"Ground truth X range: {targets_df['gt_x_m'].min():.1f}m – {targets_df['gt_x_m'].max():.1f}m")


if __name__ == "__main__":
    convert_dataset()
