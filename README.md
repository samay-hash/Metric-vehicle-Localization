# Sentinel AI — Metric Vehicle Localization

A full-stack computer vision and analytics platform built for the **Roostr / The Genie — CV Engineering Challenge**.

This repository contains:
1. **CV Algorithm** — Physics-based metric vehicle localization from a single RGB image (no LiDAR)
2. **Sentinel AI Dashboard** — React frontend + FastAPI backend to visualize and verify the results live

---

## 🎯 Part 1: The CV Challenge Solution

**Goal:** Estimate the 3D position (Forward distance `Z` + Lateral position `X`) of a vehicle from a single 2D bounding box, with a calibrated Confidence Score.

### 🧠 Core Approach (Physics over Black-Box AI)
Instead of uncalibrated monocular deep-learning depth models, this solution uses a **Physics-Based Pinhole Geometry Ensemble**:

1. **Distance (`Z`)** — Harmonic Mean of width prior + height prior using Pinhole Camera Model
2. **Lateral Position (`X`)** — `X = (u_center - cx) * Z / fx` using camera intrinsics
3. **Confidence** — Deterministic Geometric Agreement score (no ML, no guessing)

### 📊 Results
| Method | MAE_Z | AbsRel_Z | P90_Z | MAE_X |
|--------|-------|----------|-------|-------|
| Deep Learning Baseline | 37.52 m | 1.699 | 75.76 m | 11.65 m |
| **Physics-Based Ensemble** | **18.90 m** | **0.376** | **32.05 m** | **4.59 m** |

**Confidence Calibration Proof:**
- High Confidence (Top 50%) Error: **16.8m** ✅
- Low Confidence (Bottom 50%) Error: **21.0m** 🔴
- **Δ = −4.18m** — confidence is a reliable predictor of accuracy

---

## 💻 Part 2: Sentinel AI Dashboard

A live React dashboard showing real annotated images, predictions vs ground truth, and calibrated confidence metrics.

---

## 🚀 Full Setup Guide (Clone & Run Everything)

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and npm

---

### Step 1 — Clone the Repository
```bash
git clone https://github.com/samay-hash/Metric-vehicle-Localization.git
cd Metric-vehicle-Localization
```

---

### Step 2 — Run the Backend API Server
This serves the CV predictions, images, and metrics to the dashboard.

```bash
# Install Python dependencies
pip install fastapi uvicorn pandas numpy pillow opencv-python

# Start the server (runs on http://localhost:8000)
python cv_challenge/mock_server.py
```

> Keep this terminal running.

---

### Step 3 — Run the Frontend Dashboard
Open a **new terminal tab**:

```bash
cd frontend
npm install
npm run dev
```

> Frontend runs on `http://localhost:5173`

---

### Step 4 — Open the Dashboard
Open your browser and go to:

```
http://localhost:5173/dashboard/cv-results
```

You will see:
- ✅ **Live metrics** (MAE Z, MAE X, RMSE, AbsRel, P90, Confidence calibration proof)
- ✅ **10 annotated real images** with bounding boxes and predicted Z/X labels
- ✅ **Predictions vs Ground Truth table** (1,065 vehicles, color-coded by error)

---

### Optional — Run CV Prediction on Your Own Dataset
To run the algorithm on a custom eval set:

```bash
pip install -r cv_challenge/requirements.txt

python cv_challenge/predict.py \
  --images       ./eval/images \
  --targets      ./eval/targets.csv \
  --calibration  ./eval/calibration.csv \
  --output       ./predictions.csv
```

**Input format:**
- `targets.csv`: `image_id, target_id, x1, y1, x2, y2`
- `calibration.csv`: `image_id, fx, fy, cx, cy, width, height`

**Output:**
- `predictions.csv`: `image_id, target_id, x_m, z_m, confidence`

---

## 📁 Repository Structure

```
Metric-vehicle-Localization/
├── cv_challenge/
│   ├── src/
│   │   ├── pipeline.py          ← Core physics algorithm (80 lines)
│   │   └── geometry.py          ← Camera math helpers
│   ├── visualisations/          ← 10 annotated evaluation images
│   ├── predict.py               ← CLI entry point
│   ├── predictions.csv          ← Pre-generated output (1,065 rows)
│   ├── mock_server.py           ← FastAPI backend for dashboard
│   ├── README.md                ← CV challenge documentation
│   ├── experiments.md           ← Ablation study + 3 failure cases
│   ├── SOURCES.md               ← AI tool disclosures
│   └── requirements.txt
│
├── frontend/                    ← React + TypeScript + Vite dashboard
│   └── src/pages/CVResults.tsx  ← CV metrics dashboard page
│
└── README.md                    ← This file
```

---

## 📦 CV-Only Submission (ZIP)
The challenge ZIP (`samay_samrat_cv_challenge.zip`) is located at:
```
cv_challenge/samay_samrat_cv_challenge.zip
```
This contains only the required submission files per the PDF checklist.

---

*Built for The Genie Engineering Challenge — Physics-based, deterministic, production-ready.*
