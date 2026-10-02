import numpy as np
from PIL import Image

class DepthEstimator:
    def __init__(self, model_name="depth-anything/Depth-Anything-V2-Small-hf"):
        # Import inside so it doesn't break if transformers is not installed yet
        try:
            from transformers import pipeline
            self.pipe = pipeline("depth-estimation", model=model_name, device="cpu")
            self.enabled = True
        except ImportError:
            print("WARNING: transformers not installed. Depth estimation will return dummy data.")
            self.enabled = False
            
    def estimate(self, image_path: str) -> np.ndarray:
        img = Image.open(image_path).convert("RGB")
        if not self.enabled:
            # Dummy depth map for scaffolding
            return np.ones((img.height, img.width)) * 10.0
            
        result = self.pipe(img)
        depth = np.array(result["depth"])
        return depth
