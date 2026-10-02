def pixel_to_camera_x(u_center, z_m, fx, cx):
    """
    Pinhole camera model:
    X = (u - cx) * Z / fx
    """
    if fx <= 0:
        return 0.0
    return (u_center - cx) * z_m / fx
