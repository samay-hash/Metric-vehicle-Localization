def compute_confidence(x1, y1, x2, y2, z_m, depth_variance, img_w, img_h):
    """
    Confidence = f(bbox_size, distance, depth_stability, edge_proximity)
    NOT model softmax — reflects expected measurement reliability
    """
    # 1. Bbox size (larger = more reliable)
    bbox_area = max((x2 - x1) * (y2 - y1), 1)
    img_area = max(img_w * img_h, 1)
    size_score = min((bbox_area / img_area) * 50, 1.0) # Assume 2% area is max score
    
    # 2. Distance (closer = more reliable)
    dist_score = max(0.0, 1.0 - (z_m / 100.0))
    
    # 3. Depth consistency (low variance = stable)
    var_score = max(0.0, 1.0 - (depth_variance / 50.0))
    
    # 4. Edge proximity (avoid cropped vehicles)
    edge_margin = min(x1, y1, img_w - x2, img_h - y2)
    edge_score = min(edge_margin / 30.0, 1.0)
    
    # Weights
    confidence = 0.3 * size_score + 0.3 * dist_score + 0.25 * var_score + 0.15 * edge_score
    return round(min(max(confidence, 0.01), 0.99), 3)
