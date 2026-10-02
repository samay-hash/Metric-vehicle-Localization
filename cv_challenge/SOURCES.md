# Sources and Disclosures

## External Models and Code
- **Dataset**: Peking University / Baidu Autonomous Driving Dataset (Kaggle). We do not include the raw Kaggle data in the submission per requirements.
- **Formulas & Geometry**: Standard Pinhole Camera Model formulas (`X = (u - cx) * Z / fx`) are standard computer vision mathematics. The `Width+Height Ensemble` (Harmonic Mean) is an original geometric adaptation to address bounding-box truncation and partial occlusions.
- **Confidence Calibration**: The physical agreement logic (`min(z_w, z_h) / max(z_w, z_h)`) is an original heuristic derived specifically for this challenge to reflect structural camera logic without relying on opaque ML models.

## AI Tools Used
As permitted by the challenge rules ("AI usage is explicitly allowed... You remain responsible for correctness"), the following AI tools were used during development:

1. **Google DeepMind Antigravity / Gemini**:
   - **Role**: AI coding assistant.
   - **Contribution**: Assisted in scaffolding the FastAPI mock server, iterating on React frontend dashboards for evaluation visualization, and generating the baseline code structure.
   - **Critical Pivot**: Initially, a pre-trained monocular depth model (`DepthAnythingV2`) combined with a machine-learning risk calibrator (`HistGradientBoostingRegressor`) was explored. However, the AI assistant and I jointly analyzed the dashboard metrics and realized that a Deep Learning approach was producing uncalibrated results due to relative/absolute error mismatches. I directed the pivot to the final, purely physics-based `Geometric-Aware Heuristic` which eliminated the opaque ML models and resulted in perfectly calibrated confidence scores.

The final mathematical approach, evaluation, and pipeline logic submitted here are fully understood, deterministic, and fundamentally grounded in physical camera principles.
