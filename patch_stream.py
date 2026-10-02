import re

with open('backend/routers/stream.py', 'r') as f:
    content = f.read()

# Add DISABLE_ML
content = content.replace('import numpy as np', 'import numpy as np\nimport os\nDISABLE_ML = os.getenv("DISABLE_ML", "false").lower() == "true"')

# Mock YOLO
content = content.replace('model = YOLO("yolo11n.pt")', 'model = None\n    if not DISABLE_ML:\n        model = YOLO("yolo11n.pt")')

# Mock EasyOCR
content = content.replace("ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)", "ocr_reader = None\n    if not DISABLE_ML:\n        ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)")

# Mock FastReID
content = content.replace("state = torch.load(model_path, map_location='cpu', weights_only=True)['model']", "if not DISABLE_ML:\n        state = torch.load(model_path, map_location='cpu', weights_only=True)['model']")

# FastReID indented block fix
content = re.sub(
    r"(state = torch\.load.*?)(except Exception as e:)",
    r"if not DISABLE_ML:\n        \1\2",
    content,
    flags=re.DOTALL
)

# A safer way is to just do a string replace for the whole FastReID block
