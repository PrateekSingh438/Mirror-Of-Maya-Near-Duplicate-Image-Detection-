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
        print(f"Initializing Robust Detector on {config.DEVICE}")
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

    def _generate_embedding(self, image_path):
        views = get_tta_views(image_path)
        if not views:
            return None
        
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
        if not os.path.exists(folder):
            return

        print(f"Scanning {folder}")
        image_files = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    image_files.append(os.path.join(root, f))
        
        if not image_files:
            return

        print("Phase 1 Hash Filter")
        unique_files = []
        for f in tqdm(image_files):
            try:
                img = Image.open(f).convert("RGB")
                h = str(imagehash.phash(img, hash_size=config.HASH_SIZE))
                if h not in self.hash_map:
                    self.hash_map[h] = f
                    unique_files.append(f)
            except:
                continue

        print(f"Phase 2 Robust Processing {len(unique_files)} images")
        
        batch_embeddings = []
        batch_files = []
        
        for f in tqdm(unique_files):
            emb = self._generate_embedding(f)
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
        if self.index.ntotal < 2:
            return []

        D, I = self.index.search(self.index.reconstruct_n(0, self.index.ntotal), 2)
        duplicates = []
        visited = set()

        for i in range(len(I)):
            if D[i][1] > threshold:
                idx1, idx2 = I[i][0], I[i][1]
                if idx1 < len(self.stored_files) and idx2 < len(self.stored_files):
                    pair = tuple(sorted((self.stored_files[idx1], self.stored_files[idx2])))
                    if pair not in visited:
                        duplicates.append({
                            "file1": pair[0],
                            "file2": pair[1],
                            "score": float(D[i][1])
                        })
                        visited.add(pair)
        return duplicates

    def find_matches_for_file(self, query_image_path, threshold=None):
        threshold = threshold or config.SIMILARITY_THRESHOLD
        
        query_emb = self._generate_embedding(query_image_path)
        if query_emb is None:
            return []
        
        query_emb = query_emb.reshape(1, -1)
        D, I = self.index.search(query_emb, 5)
        
        matches = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score > threshold:
                matches.append({
                    "path": self.stored_files[idx],
                    "score": float(score),
                    "method": "DINOv2 (Robust)"
                })
        return matches
