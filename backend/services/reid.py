import os
import numpy as np

# We wrap the heavy imports so they don't crash the free tier if we're bypassing ML
DISABLE_ML = os.getenv("DISABLE_ML", "false").lower() == "true" or os.getenv("RENDER", "false").lower() == "true"
if not DISABLE_ML:
    import torch
    import torchvision.transforms as T
    from torchvision.models import resnet18, ResNet18_Weights
    from PIL import Image
import numpy as np

import ssl
import urllib.request
ssl._create_default_https_context = ssl._create_unverified_context

class PersonReID:
    def __init__(self, threshold=0.80):
        self.threshold = threshold
        self.global_embeddings = {}
        self.next_id = 1
        
        if DISABLE_ML:
            print("[Re-ID] Running in lightweight mock mode.")
            return

        # We can use cpu or mps. Let's use cpu for simplicity and stability here.
        self.device = torch.device("cpu")
        
        # Load pre-trained ResNet18
        self.model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        # Remove the final classification layer to get the 512-d feature embedding
        self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
        self.model.eval()
        self.model.to(self.device)
        
        self.transform = T.Compose([
            T.Resize((256, 128)), # Standard size for person Re-ID
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
    def get_embedding(self, crop: np.ndarray):
        """Extract a 512-d feature vector from a person crop."""
        try:
            if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                return None
            
            if DISABLE_ML:
                # Return a fake 512-d embedding
                return np.random.rand(512)
                
            # Convert BGR (OpenCV) to RGB (PIL)
            img = Image.fromarray(crop[..., ::-1])
            tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                feat = self.model(tensor)
            # feat shape is [1, 512, 1, 1], flatten and normalize
            feat = feat.view(feat.size(0), -1)
            feat = torch.nn.functional.normalize(feat, p=2, dim=1)
            return feat.squeeze(0).numpy() if hasattr(feat, 'numpy') else feat.squeeze(0) # [512]
        except Exception as e:
            print(f"Re-ID embedding error: {e}")
            return None
            
    def match_person(self, crop: np.ndarray) -> str:
        """Matches a person crop to the global database. Returns the P_XXX ID."""
        emb = self.get_embedding(crop)
        if emb is None:
            return self._new_id()
            
        best_match_id = None
        best_sim = -1.0
        
        for pid, stored_embs in self.global_embeddings.items():
            for stored_emb in stored_embs:
                # Cosine similarity
                if DISABLE_ML:
                    sim = float(np.dot(emb, stored_emb))
                else:
                    sim = torch.dot(emb, stored_emb).item()
                if sim > best_sim:
                    best_sim = sim
                    best_match_id = pid
                    
        if best_match_id and best_sim >= self.threshold:
            print(f"[Re-ID] Matched {best_match_id} with similarity {best_sim:.2f}")
            # Keep up to 5 embeddings per person to capture different angles
            if len(self.global_embeddings[best_match_id]) < 5:
                self.global_embeddings[best_match_id].append(emb)
            return best_match_id
            
        # No match found, create a new ID
        new_id = self._new_id()
        self.global_embeddings[new_id] = [emb]
        print(f"[Re-ID] Created new person {new_id} (Best sim was {best_sim:.2f})")
        return new_id
        
    def _new_id(self) -> str:
        pid = f"P_{self.next_id:03d}"
        self.next_id += 1
        return pid

# Global singleton
reid_system = PersonReID(threshold=0.80)
