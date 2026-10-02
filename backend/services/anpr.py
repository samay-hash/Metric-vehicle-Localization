"""
Inferia AI — ANPR (Automatic Number Plate Recognition) Service
Uses EasyOCR to extract Indian number plate text from vehicle bounding boxes.
"""

import cv2
import numpy as np
import re
import ssl
import logging
from typing import Optional

# Fix SSL cert verification for EasyOCR model downloads on macOS
ssl._create_default_https_context = ssl._create_unverified_context

log = logging.getLogger("InferiaANPR")

# Indian number plate pattern: GJ01AB1234 or GJ-01-AB-1234
PLATE_PATTERN = re.compile(
    r'\b([A-Z]{2}[\s\-]?\d{2}[\s\-]?[A-Z]{1,2}[\s\-]?\d{4})\b',
    re.IGNORECASE
)

_reader = None

def get_reader():
    """Lazy-load EasyOCR reader (takes ~10s first time, cached after)."""
    global _reader
    if _reader is None:
        try:
            import easyocr
            log.info("Loading EasyOCR (English + Hindi)...")
            _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            log.info("EasyOCR ready.")
        except ImportError:
            log.warning("EasyOCR not installed. Run: pip install easyocr")
            _reader = None
    return _reader


def preprocess_plate_crop(crop: np.ndarray) -> np.ndarray:
    """
    Enhance the cropped region for better OCR accuracy.
    Resize, grayscale, denoise, threshold.
    """
    if crop is None or crop.size == 0:
        return crop

    # Resize to standard plate height for OCR
    h, w = crop.shape[:2]
    scale = max(1, 80 // h)
    crop = cv2.resize(crop, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    # Grayscale
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive threshold to handle lighting variation
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def extract_plate_from_frame(
    frame: np.ndarray,
    vehicle_bbox: list,
    expand_ratio: float = 0.15
) -> Optional[str]:
    """
    Given a full frame and a vehicle bounding box [x1, y1, x2, y2],
    crops the lower-middle portion of the vehicle (where plates usually are),
    runs OCR, and returns the plate string if found.

    Returns None if no valid plate found.
    """
    reader = get_reader()
    if reader is None:
        return None

    try:
        x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
        h, w = frame.shape[:2]

        # Expand bbox slightly
        pad_x = int((x2 - x1) * expand_ratio)
        pad_y = int((y2 - y1) * expand_ratio)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        # Focus on bottom 40% of vehicle bbox (plate region)
        plate_y1 = y1 + int((y2 - y1) * 0.55)
        crop = frame[plate_y1:y2, x1:x2]

        if crop.size == 0:
            return None

        processed = preprocess_plate_crop(crop)

        # Run OCR
        results = reader.readtext(processed, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -')

        for (_, text, conf) in results:
            if conf < 0.4:
                continue
            cleaned = text.upper().replace(' ', '').replace('-', '')
            # Try to match Indian plate pattern
            match = PLATE_PATTERN.search(cleaned)
            if match:
                plate = match.group(1).upper().replace(' ', '').replace('-', '')
                log.info(f"ANPR: Plate detected = {plate} (conf={conf:.2f})")
                return plate

        return None

    except Exception as e:
        log.warning(f"ANPR error: {e}")
        return None


def extract_plate_from_vehicle_crop(crop: np.ndarray) -> Optional[str]:
    """
    Given an already cropped vehicle image, extracts the plate text.
    Focuses on the bottom 45% of the vehicle where plates typically reside.
    """
    reader = get_reader()
    if reader is None or crop is None or crop.size == 0:
        return None

    try:
        h, w = crop.shape[:2]
        
        # Focus on bottom 45% of vehicle
        plate_y1 = int(h * 0.55)
        plate_crop = crop[plate_y1:h, 0:w]

        if plate_crop.size == 0:
            return None

        processed = preprocess_plate_crop(plate_crop)

        # Run OCR
        results = reader.readtext(processed, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -')

        for (_, text, conf) in results:
            if conf < 0.4:
                continue
            cleaned = text.upper().replace(' ', '').replace('-', '')
            match = PLATE_PATTERN.search(cleaned)
            if match:
                plate = match.group(1).upper().replace(' ', '').replace('-', '')
                log.info(f"ANPR Optimized: Plate detected = {plate} (conf={conf:.2f})")
                return plate

        return None
    except Exception as e:
        log.warning(f"ANPR Optimized error: {e}")
        return None
