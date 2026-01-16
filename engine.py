import os
import torch
import torch.nn.functional as F
from transformers import AutoImageProcessor, AutoModel
import faiss
import numpy as np
import imagehash
from PIL import Image
from tqdm import tqdm
import config
from data_loader import get_tta_views 

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class DuplicateDetector:
    def __init__(self):
        print(f" Initializing Detector on {config.DEVICE}...")
        self.device = config.DEVICE
        self.processor = AutoImageProcessor.from_pretrained(config.MODEL_ID)
        self.model = AutoModel.from_pretrained(config.MODEL_ID)
        
        if self.device == "cpu":
            self.model = torch.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8
            )
        else:
            self.model = self.model.to(self.device)
            
        self.model.eval()
        self.dimension = self.model.config.hidden_size
        self.index = faiss.IndexFlatIP(self.dimension)
        self.hash_map = {}
        self.stored_files = []

    def _generate_standard_embedding(self, image_path):
        try:
            img = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=img, return_tensors="pt")
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                emb = F.normalize(outputs.last_hidden_state[:, 0, :], p=2, dim=1)
            
            return emb.cpu().numpy() if self.device == "cpu" else emb.cpu().numpy()
        except Exception:
            return None

    def _generate_robust_embedding(self, image_path):
        views = get_tta_views(image_path)
        if not views: return None
        
        try:
            inputs = self.processor(images=views, return_tensors="pt")
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0, :]
                embeddings = F.normalize(embeddings, p=2, dim=1)
            
            if self.device == "cpu":
                avg_emb = embeddings.mean(dim=0).numpy()
            else:
                avg_emb = embeddings.mean(dim=0).cpu().numpy()
                
            norm = np.linalg.norm(avg_emb)
            return avg_emb / norm if norm > 0 else avg_emb
        except Exception:
            return None

    def bulk_index(self, folder):
        if not os.path.exists(folder): return

        print(f"Scanning {folder}")
        image_files = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    image_files.append(os.path.join(root, f))
        
        if not image_files: return

        self.index = faiss.IndexFlatIP(self.dimension)
        self.stored_files = []
        self.hash_map = {}

        print(f"Processing {len(image_files)} images...")
        batch_embeddings = []
        batch_files = []
        
        for f in tqdm(image_files):
            emb = self._generate_standard_embedding(f)
            if emb is not None:
                batch_embeddings.append(emb)
                batch_files.append(f)
                
                if len(batch_embeddings) >= config.BATCH_SIZE:
                    self.index.add(np.vstack(batch_embeddings))
                    self.stored_files.extend(batch_files)
                    batch_embeddings = []
                    batch_files = []
        
        if batch_embeddings:
            self.index.add(np.vstack(batch_embeddings))
            self.stored_files.extend(batch_files)

    def find_duplicates(self, threshold=None):
        threshold = threshold or config.SIMILARITY_THRESHOLD
        if self.index.ntotal < 2: return []

        D, I = self.index.search(self.index.reconstruct_n(0, self.index.ntotal), 10)
        duplicates = []
        visited = set()

        for i in range(len(I)):
            for j in range(1, len(I[i])):
                score = D[i][j]
                idx = I[i][j]
                
                if idx != -1 and score > threshold:
                    idx1, idx2 = i, idx
                    if idx1 < len(self.stored_files) and idx2 < len(self.stored_files):
                        pair = tuple(sorted((self.stored_files[idx1], self.stored_files[idx2])))
                        if pair not in visited:
                            duplicates.append({
                                "file1": pair[0],
                                "file2": pair[1],
                                "score": float(score)
                            })
                            visited.add(pair)
        return duplicates

    def find_matches_for_file(self, query_image_path, threshold=None):
        threshold = threshold or config.SIMILARITY_THRESHOLD
        
        query_emb = self._generate_robust_embedding(query_image_path)
        if query_emb is None: return []
        
        query_emb = query_emb.reshape(1, -1)
        D, I = self.index.search(query_emb, 10)
        
        matches = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score > threshold:
                matches.append({
                    "path": self.stored_files[idx],
                    "score": float(score),
                    "method": "DINOv2 (Robust)"
                })
        return matches