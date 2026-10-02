import numpy as np

def aggregate_depth_baseline(depth_map, x1, y1, x2, y2):
    """Method A: Center pixel only"""
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    
    # Boundary checks
    H, W = depth_map.shape
    cy = max(0, min(H - 1, cy))
    cx = max(0, min(W - 1, cx))
    
    return float(depth_map[cy, cx])

def aggregate_depth_improved(depth_map, x1, y1, x2, y2):
    """Method B: Lower-half trimmed median"""
    H, W = depth_map.shape
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(W, int(x2)), min(H, int(y2))
    
    # Isolate lower half to avoid windshield/sky
    mid_y = (y1 + y2) // 2
    region = depth_map[mid_y:y2, x1:x2]
    
    if region.size == 0:
        return aggregate_depth_baseline(depth_map, x1, y1, x2, y2)
        
    flat = region.flatten()
    # Trimmed median (10th to 90th percentile)
    p10, p90 = np.percentile(flat, [10, 90])
    trimmed = flat[(flat >= p10) & (flat <= p90)]
    
    if trimmed.size == 0:
        return np.median(flat)
        
    return float(np.median(trimmed))

def depth_to_metric_z(relative_depth, fx, bbox_width_px, vehicle_width_m=1.8):
    """
    Recover metric Z using vehicle width prior.
    Z = fx * VEHICLE_WIDTH / bbox_width_px
    We can blend this with relative depth if calibrated, but this is a pure geometric fallback.
    """
    if bbox_width_px <= 0:
        return 10.0 # safe fallback
    return (fx * vehicle_width_m) / bbox_width_px
