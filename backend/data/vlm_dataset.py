import json
import os
from datetime import datetime
class VLMDatasetLogger:
    def __init__(self, dataset_file: str = "vlm_finetune_data.jsonl"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dataset_path = os.path.join(self.base_dir, "..", "frontend", "public", dataset_file)
    def log_event(self, image_path: str, prompt: str, vlm_response: dict):
        record = {
            "id": f"FT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "image": image_path,
            "conversations": [
                {
                    "from": "human",
                    "value": f"<image>\n{prompt}"
                },
                {
                    "from": "gpt",
                    "value": json.dumps(vlm_response)
                }
            ]
        }
        with open(self.dataset_path, "a") as f:
            f.write(json.dumps(record) + "\n")