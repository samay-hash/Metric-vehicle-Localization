import os
import pandas as pd
import numpy as np

def x_from_z(u, z_m, fx, cx):
    return (u - cx) * z_m / fx

class LocalizationPipeline:
    def __init__(self):
        # We assume standard vehicle dimensions for the PKU dataset
        self.VEH_W = 1.8  # width in meters
        self.VEH_H = 1.5  # height in meters
        
    def predict_target(self, img_w, img_h, x1, y1, x2, y2, fx, fy, cx, cy):
        # 1. Bounding box dimensions in pixels
        bw = max(x2 - x1, 1.0)
        bh = max(y2 - y1, 1.0)
        
        # 2. Independent geometric cues (Pinhole Camera Model)
        z_w = fx * self.VEH_W / bw
        z_h = fy * self.VEH_H / bh
        
        # 3. Robust Geometric Fusion (Harmonic Mean)
        # Harmonic mean naturally penalizes large outliers and trusts the smaller estimate
        z_m = 2.0 / ((1.0 / z_w) + (1.0 / z_h))
        
        # 4. Lateral Position X
        # Reference point is the horizontal center of the bounding box
        # We use strictly correct 'cx' from calibration, not image center
        u_center = (x1 + x2) / 2.0
        x_m = x_from_z(u_center, z_m, fx, cx)
        
        # 5. Physics-Based Confidence Scoring
        # A) Geometric Agreement: Do width and height imply the same distance?
        # If z_w and z_h are perfectly equal, ratio is 1.0.
        agreement_ratio = min(z_w, z_h) / max(z_w, z_h)
        
        # B) Edge Truncation Penalty: If car is cut off by the frame, box is unreliable
        edge_px = min(x1, y1, img_w - x2, img_h - y2)
        # Normalize edge distance (if > 50px away from edge, it's 100% safe)
        edge_safety = np.clip(edge_px / 50.0, 0.1, 1.0)
        
        # C) Extreme Distance Penalty: Pinhole math gets unstable at extreme distances (>100m)
        distance_decay = np.clip(1.0 - (z_m / 150.0), 0.1, 1.0)
        
        # Combine into a final [0, 1] confidence
        # Agreement is the most important factor
        confidence = (0.75 * agreement_ratio + 0.25 * distance_decay) * edge_safety
        
        return round(x_m, 2), round(z_m, 2), round(float(confidence), 3)

def run_evaluation(images_dir, targets_csv, calibration_csv, output_csv):
    targets = pd.read_csv(targets_csv)
    calib = pd.read_csv(calibration_csv)
    df = pd.merge(targets, calib, on="image_id")
    
    pipeline = LocalizationPipeline()
    results = []
    
    print(f"Processing {len(df)} targets using Physics-Based Geometric Heuristic...")
    
    for idx, row in df.iterrows():
        x_m, z_m, conf = pipeline.predict_target(
            img_w=row['width'], img_h=row['height'],
            x1=row['x1'], y1=row['y1'], x2=row['x2'], y2=row['y2'],
            fx=row['fx'], fy=row['fy'], cx=row['cx'], cy=row['cy']
        )
        
        results.append({
            "image_id": row['image_id'],
            "target_id": row['target_id'],
            "x_m": x_m,
            "z_m": z_m,
            "confidence": conf
        })
        
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_csv, index=False)
    print(f"Predictions saved to {output_csv} successfully!")
