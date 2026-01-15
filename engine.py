import os
import torch
import torch.nn.functional as F
from transformers import AutoImageProcessor, AutoModel
import faiss
import numpy as np
import imagehash
from PIL import Image
from torch.utils.data import DataLoader
from tqdm import tqdm
import config
from data_loader import ImageDataset

class DuplicateDetector:
    def __init__(self):
        print(f"Initializing Hybrid Detector on {config.DEVICE}...")
        self.device = config.DEVICE
        self.processor = AutoImageProcessor.from_pretrained(config.MODEL_ID)
        self.model = AutoModel.from_pretrained(config.MODEL_ID).to(self.device)
        self.model.eval()
        self.dimension = self.model.config.hidden_size
        self.index = faiss.IndexFlatIP(self.dimension)
        self.hash_map = {}
        self.stored_files = []

    def bulk_index(self, folder):
        if not os.path.exists(folder):
            return

        image_files = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(root, f))

        unique_after_hash = []
        for f in tqdm(image_files):
            try:
                img = Image.open(f).convert("RGB")
                h = str(imagehash.phash(img, hash_size=config.HASH_SIZE))
                if h in self.hash_map:
                    continue
                else:
                    self.hash_map[h] = f
                    unique_after_hash.append(f)
            except:
                continue

        if not unique_after_hash:
            print("All duplicates caught by Hash Filter.")
            return

        print(f"Running DINOv2 on {len(unique_after_hash)} images...")
        dataset = ImageDataset(unique_after_hash, self.processor)
        dataloader = DataLoader(dataset, batch_size=config.BATCH_SIZE, shuffle=False)

        all_embeddings = []
        with torch.no_grad():
            for batch_imgs, batch_paths in tqdm(dataloader):
                valid_mask = [p != "ERROR" for p in batch_paths]
                if not any(valid_mask):
                    continue

                batch_imgs = batch_imgs[valid_mask].to(self.device)
                outputs = self.model(pixel_values=batch_imgs)
                embeddings = F.normalize(outputs.last_hidden_state[:, 0, :], p=2, dim=1)
                all_embeddings.append(embeddings.cpu().numpy())
                self.stored_files.extend([p for p, m in zip(batch_paths, valid_mask) if m])

        if all_embeddings:
            self.index.add(np.vstack(all_embeddings))

    def find_duplicates(self, threshold=None):
        threshold = threshold or config.SIMILARITY_THRESHOLD
        if self.index.ntotal < 2:
            return []

        D, I = self.index.search(self.index.reconstruct_n(0, self.index.ntotal), 2)
        duplicates = []
        visited = set()

        for i in range(len(I)):
            if D[i][1] > threshold:
                pair = tuple(sorted((self.stored_files[I[i][0]], self.stored_files[I[i][1]])))
                if pair not in visited:
                    duplicates.append({"file1": pair[0], "file2": pair[1], "score": float(D[i][1])})
                    visited.add(pair)
        return duplicates

    def find_matches_for_file(self, query_image_path, threshold=None):
        threshold = threshold or config.SIMILARITY_THRESHOLD
        try:
            query_img = Image.open(query_image_path).convert("RGB")
            query_hash = str(imagehash.phash(query_img, hash_size=config.HASH_SIZE))
            if query_hash in self.hash_map:
                return [{"path": self.hash_map[query_hash], "score": 1.0, "method": "pHash"}]
        except Exception as e:
            print(f"Hash search failed: {e}")

        inputs = self.processor(images=query_img, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            query_emb = F.normalize(outputs.last_hidden_state[:, 0, :], p=2, dim=1).cpu().numpy()

        D, I = self.index.search(query_emb, 3)
        matches = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score > threshold:
                matches.append({
                    "path": self.stored_files[idx],
                    "score": float(score),
                    "method": "DINOv2"
                })

        return matches
