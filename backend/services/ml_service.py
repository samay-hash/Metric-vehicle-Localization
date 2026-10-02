import os
DISABLE_ML = os.getenv("DISABLE_ML", "false").lower() == "true" or os.getenv("RENDER", "false").lower() == "true"
if not DISABLE_ML:
    import torch
    from transformers import PaliGemmaProcessor, PaliGemmaForConditionalGeneration
    from peft import PeftModel
from PIL import Image

class ThreatDetector:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cpu" if DISABLE_ML else ("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
        self.is_loaded = False
        self.model_id = "google/paligemma-3b-pt-224"
        self.weights_dir = os.path.join(os.path.dirname(__file__), "..", "paligemma-1k-weights")

    def load_model(self):
        if self.is_loaded or DISABLE_ML:
            self.is_loaded = True
            return

        print(f"Loading PaliGemma Base Model on {self.device}...")
        # In production, this loads the 3B parameter model.
        self.processor = PaliGemmaProcessor.from_pretrained(self.model_id)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        base_model = PaliGemmaForConditionalGeneration.from_pretrained(
            self.model_id, torch_dtype=dtype
        ).to(self.device)
        self.model = PeftModel.from_pretrained(base_model, self.weights_dir)
            
        self.is_loaded = True

    def analyze_frame(self, image_path: str) -> bool:
        """
        Analyzes an image and returns True if a weapon is detected, False otherwise.
        """
        if not self.is_loaded:
            self.load_model()

        try:
            raw_image = Image.open(image_path).convert("RGB")
        except Exception as e:
            print(f"Error opening image {image_path}: {e}")
            return False

        # Use a standard detection prompt
        prompt = "detect weapon"
        
        if DISABLE_ML:
            is_threat = False
            print(f"ML Output: mock | Threat: {is_threat}")
            return is_threat
        
        # Production Code:
        inputs = self.processor(text=prompt, images=raw_image, return_tensors="pt").to(self.device)
        
        # Convert inputs to the correct dtype (float16 for cuda)
        if self.device == "cuda":
             inputs = {k: v.to(torch.float16) if v.dtype == torch.float32 else v for k, v in inputs.items()}

        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=20)
        
        result = self.processor.decode(output[0], skip_special_tokens=True).lower()
        is_threat = "weapon" in result or "gun" in result or "knife" in result or "detected" in result
        
        print(f"ML Output: {result} | Threat: {is_threat}")
        return is_threat

# Singleton instance
threat_detector = ThreatDetector()
