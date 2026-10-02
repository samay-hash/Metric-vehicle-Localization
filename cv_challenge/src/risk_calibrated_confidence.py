from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pickle
import numpy as np

try:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import KFold
except ImportError as exc:
    raise ImportError("Install scikit-learn: pip install scikit-learn") from exc

EPS = 1e-6

@dataclass
class ConfidenceFeatures:
    z_width: float
    z_height: float
    z_geom: float
    z_depth: float
    wh_disagreement: float
    depth_geom_disagreement: float
    depth_mad_rel: float
    depth_iqr_rel: float
    bbox_area_ratio: float
    bbox_width_ratio: float
    bbox_height_ratio: float
    edge_margin: float
    depth_model_conf: float = np.nan

    def vector(self) -> np.ndarray:
        x = np.array([
            self.z_width, self.z_height, self.z_geom, self.z_depth,
            self.wh_disagreement, self.depth_geom_disagreement,
            self.depth_mad_rel, self.depth_iqr_rel,
            self.bbox_area_ratio, self.bbox_width_ratio,
            self.bbox_height_ratio, self.edge_margin,
            self.depth_model_conf
        ], dtype=np.float32)
        return np.nan_to_num(x, nan=0.0, posinf=1e6, neginf=-1e6)

def robust_depth_stats(depth_crop: np.ndarray):
    d = np.asarray(depth_crop, dtype=np.float32)
    d = d[np.isfinite(d) & (d > 0)]
    if d.size == 0:
        return np.nan, 1.0, 1.0
    lo, hi = np.percentile(d, [10, 90])
    trimmed = d[(d >= lo) & (d <= hi)]
    if trimmed.size < 5:
        trimmed = d
    med = float(np.median(trimmed))
    mad = float(np.median(np.abs(trimmed - med)))
    q25, q75 = np.percentile(trimmed, [25, 75])
    return med, mad / max(med, EPS), float(q75 - q25) / max(med, EPS)

def build_features(
    *, image_width: int, image_height: int,
    x1: float, y1: float, x2: float, y2: float,
    fx: float, fy: float, depth_crop: np.ndarray,
    depth_at_reference: Optional[float] = None,
    depth_model_confidence: Optional[float] = None,
    real_vehicle_width_m: float = 1.8,
    real_vehicle_height_m: float = 1.5,
) -> ConfidenceFeatures:
    bw = max(float(x2 - x1), 1.0)
    bh = max(float(y2 - y1), 1.0)
    z_width = fx * real_vehicle_width_m / bw
    z_height = fy * real_vehicle_height_m / bh

    wh_disagreement = abs(z_width - z_height) / max(
        0.5 * (z_width + z_height), EPS
    )
    z_geom = 2.0 / max(
        1.0 / max(z_width, EPS) + 1.0 / max(z_height, EPS), EPS
    )

    z_depth, mad_rel, iqr_rel = robust_depth_stats(depth_crop)
    if not np.isfinite(z_depth):
        z_depth = z_geom
    disagreement = abs(z_depth - z_geom) / max(
        0.5 * (z_depth + z_geom), EPS
    )

    if depth_at_reference is not None and np.isfinite(depth_at_reference):
        z_depth = 0.8 * z_depth + 0.2 * depth_at_reference

    area_ratio = bw * bh / max(image_width * image_height, 1)
    width_ratio = bw / max(image_width, 1)
    height_ratio = bh / max(image_height, 1)
    edge_px = min(x1, y1, image_width - x2, image_height - y2)
    edge_margin = np.clip(edge_px / max(min(image_width, image_height), 1), 0, 0.5)

    return ConfidenceFeatures(
        z_width=float(z_width), z_height=float(z_height), z_geom=float(z_geom),
        z_depth=float(z_depth), wh_disagreement=float(wh_disagreement),
        depth_geom_disagreement=float(disagreement),
        depth_mad_rel=float(mad_rel), depth_iqr_rel=float(iqr_rel),
        bbox_area_ratio=float(area_ratio), bbox_width_ratio=float(width_ratio),
        bbox_height_ratio=float(height_ratio), edge_margin=float(edge_margin),
        depth_model_conf=(
            float(depth_model_confidence)
            if depth_model_confidence is not None else np.nan
        )
    )

class RiskCalibratedConfidence:
    """
    Learns localization risk from the development split and converts
    predicted risk into a 0..1 reliability ranking.

    This is intentionally NOT a hard-coded 0.85/0.95 confidence.
    """
    def __init__(self, n_splits: int = 5, random_state: int = 42):
        self.n_splits = n_splits
        self.random_state = random_state
        self.model = None
        self.oof_risk_sorted = None

    @staticmethod
    def target(x_pred, z_pred, x_true, z_true):
        z_true = np.maximum(np.abs(z_true), 1e-3)
        rel_z = np.abs(z_pred - z_true) / z_true
        x_scale = np.maximum(1.0, 0.10 * np.abs(z_true))
        norm_x = np.abs(x_pred - x_true) / x_scale
        risk = 0.70 * rel_z + 0.30 * norm_x
        return np.log1p(risk).astype(np.float32)

    def fit(self, X, x_pred, z_pred, x_true, z_true):
        X = np.asarray(X, dtype=np.float32)
        y = self.target(
            np.asarray(x_pred), np.asarray(z_pred),
            np.asarray(x_true), np.asarray(z_true)
        )
        if len(X) < max(20, self.n_splits * 4):
            raise ValueError("Need more development targets for calibration.")

        kf = KFold(self.n_splits, shuffle=True, random_state=self.random_state)
        oof = np.zeros(len(X), dtype=np.float32)

        for tr, va in kf.split(X):
            m = HistGradientBoostingRegressor(
                learning_rate=0.05, max_iter=250,
                max_leaf_nodes=15, l2_regularization=1.0,
                random_state=self.random_state
            )
            m.fit(X[tr], y[tr])
            oof[va] = m.predict(X[va])

        self.model = HistGradientBoostingRegressor(
            learning_rate=0.05, max_iter=250,
            max_leaf_nodes=15, l2_regularization=1.0,
            random_state=self.random_state
        )
        self.model.fit(X, y)
        self.oof_risk_sorted = np.sort(oof)
        return self

    def predict_confidence(self, X):
        if self.model is None or self.oof_risk_sorted is None:
            raise RuntimeError("Fit the calibrator before inference.")
        risk = self.model.predict(np.asarray(X, dtype=np.float32))
        ranks = np.searchsorted(self.oof_risk_sorted, risk, side="right")
        conf = 1.0 - ranks / max(len(self.oof_risk_sorted), 1)
        return np.clip(conf, 0.0, 1.0).astype(np.float32)

    def save(self, path: str | Path):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str | Path):
        with open(path, "rb") as f:
            return pickle.load(f)

def x_from_z(u: float, z_m: float, fx: float, cx: float) -> float:
    return float((u - cx) * z_m / max(fx, EPS))
