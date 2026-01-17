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
from utils import walk_image_files

os.environ["KMP_DUPLICATE_LIB_OK"] = config.ENV_KMP_DUPLICATE_LIB

class DuplicateDetector:
    def __init__(self):
        print(f"Initializing Hybrid Detector on {config.DEVICE}")
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
        
        self.phash_map = {} 
        self.fast_duplicates = []
        self.stored_files = []

    def _generate_embedding(self, image_path, use_tta=False):
        
        if use_tta:
            return self._generate_robust_embedding(image_path)
        return self._generate_standard_embedding(image_path)

    def _generate_standard_embedding(self, image_path):
        
        try:
            img = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=img, return_tensors="pt")
            
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                emb = F.normalize(outputs.last_hidden_state[:, 0, :], p=2, dim=1)
            
            return emb.cpu().numpy()
        except Exception:
            return None

    def _generate_robust_embedding(self, image_path):
        
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
            
            avg_emb = embeddings.mean(dim=0).cpu().numpy()
            norm = np.linalg.norm(avg_emb)
            return avg_emb / norm if norm > 0 else avg_emb
        except Exception:
            return None

    def _compute_phash(self, image_path):
        
        try:
            img = Image.open(image_path)
            return str(imagehash.phash(img, hash_size=config.HASH_SIZE))
        except:
            return None

    def bulk_index(self, folder):
        
        if not os.path.exists(folder):
            return

        print(f"Scanning {folder}")
        image_files = list(walk_image_files(folder))
        
        if not image_files:
            return

        self._reset_index()
        
        print(f"Processing {len(image_files)} images")
        files_to_embed = self._phase1_phash_filtering(image_files)
        self._phase2_embedding(files_to_embed)

    def _reset_index(self):
        
        self.index = faiss.IndexFlatIP(self.dimension)
        self.stored_files = []
        self.phash_map = {}
        self.fast_duplicates = []

    def _phase1_phash_filtering(self, image_files):
        
        files_to_embed = []
        
        print("Phase 1: pHash Fast-Pass")
        for f in tqdm(image_files):
            h = self._compute_phash(f)
            if h is None:
                continue
            
            if h in self.phash_map:
                original_file = self.phash_map[h]
                print(f"pHash Hit: {os.path.basename(f)}")
                self.fast_duplicates.append({
                    "file1": original_file,
                    "file2": f,
                    "score": 1.0,
                    "method": "pHash"
                })
            else:
                self.phash_map[h] = f
                files_to_embed.append(f)
        
        return files_to_embed

    def _phase2_embedding(self, files_to_embed):
        
        print(f"Phase 2: Embedding {len(files_to_embed)} unique images")
        
        batch_embeddings = []
        batch_files = []
        
        for f in tqdm(files_to_embed):
            emb = self._generate_standard_embedding(f)
            if emb is not None:
                batch_embeddings.append(emb)
                batch_files.append(f)
                
                if len(batch_embeddings) >= config.BATCH_SIZE:
                    self._add_batch_to_index(batch_embeddings, batch_files)
                    batch_embeddings = []
                    batch_files = []
        
        if batch_embeddings:
            self._add_batch_to_index(batch_embeddings, batch_files)

    def _add_batch_to_index(self, embeddings, files):
        
        self.index.add(np.vstack(embeddings))
        self.stored_files.extend(files)

    def find_duplicates(self, threshold=None):
        
        threshold = threshold or config.SIMILARITY_THRESHOLD
        
        all_duplicates = self.fast_duplicates.copy()
        visited = self._create_visited_set(all_duplicates)

        if self.index.ntotal < 2:
            return all_duplicates

        all_duplicates.extend(self._find_embedding_duplicates(threshold, visited))
        return all_duplicates

    def _create_visited_set(self, duplicates):
        
        visited = set()
        for d in duplicates:
            pair = tuple(sorted((d['file1'], d['file2'])))
            visited.add(pair)
        return visited

    def _find_embedding_duplicates(self, threshold, visited):
        
        k = min(config.MAX_SEARCH_RESULTS, self.index.ntotal)
        D, I = self.index.search(self.index.reconstruct_n(0, self.index.ntotal), k)

        new_duplicates = []
        for i in range(len(I)):
            for j in range(1, len(I[i])):
                score = D[i][j]
                if score < threshold:
                    break
                
                idx = I[i][j]
                if idx != -1:
                    idx1, idx2 = i, idx
                    if idx1 < len(self.stored_files) and idx2 < len(self.stored_files):
                        pair = tuple(sorted((self.stored_files[idx1], self.stored_files[idx2])))
                        if pair not in visited:
                            new_duplicates.append({
                                "file1": pair[0],
                                "file2": pair[1],
                                "score": float(score),
                                "method": "DINOv2"
                            })
                            visited.add(pair)
        
        return new_duplicates

    def find_matches_for_file(self, query_image_path, threshold=None):
        
        threshold = threshold or config.SIMILARITY_THRESHOLD
        query_emb = self._generate_robust_embedding(query_image_path)
        
        if query_emb is None:
            return []
        
        query_emb = query_emb.reshape(1, -1)
        k = min(config.MAX_SEARCH_RESULTS, self.index.ntotal)
        D, I = self.index.search(query_emb, k)
        
        matches = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score > threshold:
                matches.append({
                    "path": self.stored_files[idx],
                    "score": float(score),
                    "method": "DINOv2"
                })
            else:
                break
        
        return matches