# Risk-Calibrated Confidence

## Recommended pipeline

RGB image
→ local monocular metric depth
→ robust depth aggregation inside target region
→ geometric width/height cue
→ fused metric Z
→ X = (u - cx) * Z / fx
→ reliability features
→ development-set risk calibrator
→ calibrated 0..1 confidence

## Why this is the right confidence strategy

Do not write `confidence = 0.85`.

Instead, train a small risk model on the development labels to predict how likely the X/Z estimate is to be wrong. Features include:

- geometric width/height depth
- disagreement between those cues
- monocular-depth estimate
- depth-vs-geometry disagreement
- depth MAD/IQR
- bounding-box size
- distance to image edges
- optional pretrained depth confidence

The module uses out-of-fold predictions for calibration and maps lower predicted risk to higher confidence.

## Model choice

UniDepthV2 is a strong candidate for the depth branch because its official implementation supports supplied camera intrinsics, metric depth prediction, and a confidence output. Its native confidence is documented as a relative/ranking signal rather than an absolute 0..1 probability, so the development-set calibration step is important.

## Critical limitation

A genuine `85+` confidence cannot be guaranteed before running on the actual development/evaluation distribution. A professional solution should produce high confidence on predictions that are empirically reliable, rather than inflate every row to 0.85.
