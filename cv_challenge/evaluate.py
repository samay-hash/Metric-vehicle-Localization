"""
Evaluate predictions.csv against ground truth targets.csv
Metrics: MAE_Z, AbsRel_Z, P90_Z, MAE_X
"""
import pandas as pd
import numpy as np

def evaluate(predictions_path, targets_gt_path):
    preds = pd.read_csv(predictions_path)
    gt = pd.read_csv(targets_gt_path)[["target_id", "gt_x_m", "gt_z_m"]]
    
    df = pd.merge(preds, gt, on="target_id")
    
    # Filter out extreme outliers from GT (beyond 100m is unreliable for monocular)
    df = df[df["gt_z_m"] <= 100]
    df = df[df["gt_z_m"] >= 3]
    
    # --- Z (Depth / Forward Distance) Metrics ---
    z_err = (df["z_m"] - df["gt_z_m"]).abs()
    mae_z = z_err.mean()
    abs_rel_z = (z_err / df["gt_z_m"]).mean()
    p90_z = np.percentile(z_err, 90)
    rmse_z = np.sqrt((z_err**2).mean())
    
    # --- X (Lateral Position) Metrics ---
    x_err = (df["x_m"] - df["gt_x_m"]).abs()
    mae_x = x_err.mean()
    
    print("=" * 50)
    print("📊 EVALUATION RESULTS")
    print("=" * 50)
    print(f"  Samples evaluated   : {len(df)}")
    print(f"  GT Z range          : {df['gt_z_m'].min():.1f}m – {df['gt_z_m'].max():.1f}m")
    print()
    print("  [Forward Distance Z]")
    print(f"  MAE_Z               : {mae_z:.2f} m")
    print(f"  AbsRel_Z            : {abs_rel_z:.3f}")
    print(f"  RMSE_Z              : {rmse_z:.2f} m")
    print(f"  P90_Z               : {p90_z:.2f} m")
    print()
    print("  [Lateral Position X]")
    print(f"  MAE_X               : {mae_x:.2f} m")
    print("=" * 50)
    
    return {
        "n": len(df),
        "MAE_Z": round(mae_z, 3),
        "AbsRel_Z": round(abs_rel_z, 4),
        "RMSE_Z": round(rmse_z, 3),
        "P90_Z": round(p90_z, 3),
        "MAE_X": round(mae_x, 3),
    }

if __name__ == "__main__":
    results = evaluate(
        "cv_challenge/kaggle_data/predictions.csv",
        "cv_challenge/kaggle_data/targets.csv"
    )
