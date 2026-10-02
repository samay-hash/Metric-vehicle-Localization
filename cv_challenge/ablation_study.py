"""
Ablation Study v2 — 3 genuinely distinct methods:

Method A (True Baseline):
  Use DepthAnything relative depth map center pixel directly.
  Apply a GLOBAL scale factor computed from median(gt_z / rel_d) on first 50 images.
  This shows what happens when you blindly trust the depth model output.

Method B (Geometric Width Prior):
  z = fx * 1.8 / bbox_width_px
  Classic pinhole geometry with known vehicle width assumption.
  No depth model needed for Z estimation.

Method C (Ensemble Geometry: Width + Height):
  z_w = fx * 1.8 / bbox_width_px
  z_h = fy * 1.5 / bbox_height_px
  z = weighted harmonic mean (trusts narrower estimate more)
  More robust when vehicle is partially occluded on one dimension.
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from depth_estimator import DepthEstimator

BASE_DIR   = "cv_challenge/kaggle_data"
IMG_DIR    = os.path.join(BASE_DIR, "train_images")
GT_PATH    = os.path.join(BASE_DIR, "targets.csv")
CALIB_PATH = os.path.join(BASE_DIR, "calibration.csv")

FX = 2304.5479
FY = 2305.8757
CX = 1686.2379
CY = 1354.9849
VEH_W = 1.8   # standard car width (m)
VEH_H = 1.5   # standard car height (m)


def get_center_rel_depth(dmap, x1, y1, x2, y2):
    H, W = dmap.shape
    cx = int(np.clip((x1 + x2) / 2, 0, W - 1))
    cy = int(np.clip((y1 + y2) / 2, 0, H - 1))
    return float(dmap[cy, cx])


def method_b_geom_width(x1, y1, x2, y2):
    """fx * W_real / W_px"""
    bbox_w = max(x2 - x1, 1)
    return (FX * VEH_W) / bbox_w


def method_c_ensemble(x1, y1, x2, y2):
    """Harmonic-weighted blend of width prior and height prior"""
    bbox_w = max(x2 - x1, 1)
    bbox_h = max(y2 - y1, 1)
    z_w = (FX * VEH_W) / bbox_w
    z_h = (FY * VEH_H) / bbox_h
    # Weight inversely by bbox dimension ratio (prefer the axis that's more reliable)
    # Narrow bbox -> height prior more trustworthy; wide bbox -> width prior more trustworthy
    w_w = bbox_w / (bbox_w + bbox_h)
    w_h = bbox_h / (bbox_w + bbox_h)
    return w_w * z_w + w_h * z_h


def pixel_to_x(u, z):
    return (u - CX) * z / FX


def run():
    targets = pd.read_csv(GT_PATH)
    calib   = pd.read_csv(CALIB_PATH)
    df = pd.merge(targets, calib, on="image_id")
    df = df[(df["gt_z_m"] >= 3) & (df["gt_z_m"] <= 100)].copy()

    estimator = DepthEstimator()
    print(f"Step 1: Calibrating global depth scale on first 40 images...")

    # --- Calibrate global scale for Method A ---
    calib_imgs = df["image_id"].unique()[:40]
    calib_df   = df[df["image_id"].isin(calib_imgs)]

    scales = []
    depth_cache = {}
    for img_id, grp in calib_df.groupby("image_id"):
        ip = os.path.join(IMG_DIR, f"{img_id}.jpg")
        if not os.path.exists(ip): continue
        if img_id not in depth_cache:
            depth_cache[img_id] = estimator.estimate(ip)
        dmap = depth_cache[img_id]
        for _, row in grp.iterrows():
            rel_d = get_center_rel_depth(dmap, row.x1, row.y1, row.x2, row.y2)
            if rel_d > 0.01:
                scales.append(row["gt_z_m"] / rel_d)

    global_scale = float(np.median(scales))
    print(f"   Global depth scale = {global_scale:.4f}")

    # --- Evaluate all 3 methods on remaining 52 images (eval set) ---
    eval_imgs = df["image_id"].unique()[40:]
    eval_df   = df[df["image_id"].isin(eval_imgs)]
    print(f"Step 2: Evaluating on {len(eval_df)} vehicles from {len(eval_imgs)} held-out images...\n")

    rows = []
    for img_id, grp in eval_df.groupby("image_id"):
        ip = os.path.join(IMG_DIR, f"{img_id}.jpg")
        if not os.path.exists(ip): continue
        if img_id not in depth_cache:
            depth_cache[img_id] = estimator.estimate(ip)
        dmap = depth_cache[img_id]

        for _, row in grp.iterrows():
            rel_d = get_center_rel_depth(dmap, row.x1, row.y1, row.x2, row.y2)
            u_c   = (row.x1 + row.x2) / 2

            za = rel_d * global_scale          # Method A: depth model + global scale
            zb = method_b_geom_width(row.x1, row.y1, row.x2, row.y2)
            zc = method_c_ensemble(row.x1, row.y1, row.x2, row.y2)

            rows.append({
                "target_id": row["target_id"],
                "gt_z": row["gt_z_m"], "gt_x": row["gt_x_m"],
                "za": za, "zb": zb, "zc": zc,
                "xa": pixel_to_x(u_c, za),
                "xb": pixel_to_x(u_c, zb),
                "xc": pixel_to_x(u_c, zc),
            })

    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(BASE_DIR, "ablation_v2.csv"), index=False)

    print("=" * 65)
    print("  ABLATION STUDY — 3 GENUINELY DISTINCT METHODS")
    print("=" * 65)

    method_labels = {
        "A": ("za","xa", "DepthAnything + Global Scale (Naive Baseline)"),
        "B": ("zb","xb", "Geometric Width Prior   (z = fx·W/bbox_w)"),
        "C": ("zc","xc", "Width+Height Ensemble   (Weighted Harmonic Mean)"),
    }

    for m, (zk, xk, label) in method_labels.items():
        z_err = (res[zk] - res["gt_z"]).abs()
        x_err = (res[xk] - res["gt_x"]).abs()
        print(f"\n  Method {m}: {label}")
        print(f"    MAE_Z    = {z_err.mean():.2f} m")
        print(f"    AbsRel_Z = {(z_err / res['gt_z']).mean():.3f}")
        print(f"    RMSE_Z   = {np.sqrt((z_err**2).mean()):.2f} m")
        print(f"    P90_Z    = {np.percentile(z_err, 90):.2f} m")
        print(f"    MAE_X    = {x_err.mean():.2f} m")

    print("\n" + "=" * 65)
    print(f"  Vehicles evaluated: {len(res)}")
    print(f"  Saved: ablation_v2.csv")

if __name__ == "__main__":
    run()
