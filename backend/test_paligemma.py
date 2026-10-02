import sys
from transformers import PaliGemmaForConditionalGeneration, AutoProcessor
from PIL import Image
import torch

def test_paligemma(image_path: str):
    print("Loading PaliGemma model... (This might take a few minutes the first time)")
    
    model_id = "google/paligemma-3b-pt-224"
    
    # Check if Mac Apple Silicon (MPS) is available, else CPU
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")

    # Load processor and model
    try:
        processor = AutoProcessor.from_pretrained(model_id)
        model = PaliGemmaForConditionalGeneration.from_pretrained(model_id).to(device)
    except Exception as e:
        print(f"Error loading model. Did you run 'huggingface-cli login'? Error: {e}")
        return

    print(f"Model loaded successfully! Analyzing {image_path}...")
    
    # Load Image
    try:
        raw_image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Could not open image {image_path}: {e}")
        return

    # Prepare prompt
    prompt = "Describe this CCTV image in detail, looking for anomalies:"
    
    # Run Inference
    inputs = processor(text=prompt, images=raw_image, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=50)
    
    result = processor.decode(output[0], skip_special_tokens=True)
    
    print("\n" + "="*50)
    print("🤖 PaliGemma Output:")
    print(result.replace(prompt, "").strip())
    print("="*50)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_paligemma.py <path_to_image.jpg>")
    else:
        test_paligemma(sys.argv[1])
