import pandas as pd
import numpy as np
import os

BASE_DIR = "cv_challenge/kaggle_data"
res = pd.read_csv(os.path.join(BASE_DIR, "predictions.csv"))
gt = pd.read_csv(os.path.join(BASE_DIR, "targets.csv"))[["target_id", "gt_x_m", "gt_z_m"]]

df = pd.merge(res, gt, on="target_id")
df = df[(df["gt_z_m"] >= 3) & (df["gt_z_m"] <= 100)].copy()
df["err_z"] = (df["z_m"] - df["gt_z_m"]).abs()

median_conf = df["confidence"].median()
high_conf = df[df["confidence"] >= median_conf]
low_conf = df[df["confidence"] < median_conf]

print("Confidence Calibration Proof:")
print(f"High Confidence (>= {median_conf:.2f}): MAE_Z = {high_conf['err_z'].mean():.2f}m")
print(f"Low Confidence (< {median_conf:.2f}): MAE_Z = {low_conf['err_z'].mean():.2f}m")
