import os
import torch
import faiss
import numpy as np
import imagehash
from PIL import Image
from tqdm import tqdm
from collections import defaultdict
import warnings
from transformers import AutoImageProcessor, AutoModel
import config

warnings.filterwarnings('ignore')

class DuplicateDetector:
    def __init__(self):
        print(f"🚀 Initializing on {config.DEVICE}")
        self.device = config.DEVICE
        
        self.processor = AutoImageProcessor.from_pretrained(config.MODEL_ID)
        self.model = AutoModel.from_pretrained(config.MODEL_ID).to(self.device)
        self.model.eval()
        
        self.dimension = self.model.config.hidden_size
        self.index = faiss.IndexFlatIP(self.dimension)
        
        self.stored_files = []
        self.hash_buckets = defaultdict(list)
        self.fast_duplicates = []
        self.optimal_threshold = config.DEFAULT_THRESHOLD
    
    def _generate_embedding(self, image_path):
        try:
            img = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=img, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1)
                vector = embeddings.detach().cpu().numpy().astype('float32')
                faiss.normalize_L2(vector)
            
            return vector
        except Exception as e:
            return None
    
    def _compute_hash(self, image_path):
        try:
            img = Image.open(image_path).convert('RGB')
            return str(imagehash.dhash(img, hash_size=config.HASH_SIZE))
        except:
            return None
    
    def bulk_index(self, folder):
        if not os.path.exists(folder):
            return
        
        from utils import walk_image_files
        files = list(walk_image_files(folder))
        print(f"📁 Found {len(files)} images")
        
        # Phase 1: Hash
        print(f"⚡ Phase 1: Hashing...")
        files_for_dino = []
        
        for f in tqdm(files, desc="Hashing"):
            h = self._compute_hash(f)
            if not h:
                continue
            
            bucket = h[:4]
            found = False
            
            for exist_h, exist_f in self.hash_buckets[bucket]:
                dist = imagehash.hex_to_hash(h) - imagehash.hex_to_hash(exist_h)
                if dist <= config.HASH_THRESHOLD:
                    self.fast_duplicates.append({
                        "file1": exist_f,
                        "file2": f,
                        "score": 0.99,
                        "method": "dHash"
                    })
                    found = True
                    break
            
            if not found:
                self.hash_buckets[bucket].append((h, f))
                files_for_dino.append(f)
        
        # Phase 2: Embedding
        if files_for_dino:
            print(f"🧠 Phase 2: Embedding ({len(files_for_dino)} unique)...")
            batch_vecs = []
            batch_files = []
            
            for f in tqdm(files_for_dino, desc="Embedding"):
                vec = self._generate_embedding(f)
                if vec is not None:
                    batch_vecs.append(vec)
                    batch_files.append(f)
                    
                    if len(batch_vecs) >= config.BATCH_SIZE:
                        self.index.add(np.vstack(batch_vecs))
                        self.stored_files.extend(batch_files)
                        batch_vecs = []
                        batch_files = []
            
            if batch_vecs:
                self.index.add(np.vstack(batch_vecs))
                self.stored_files.extend(batch_files)
        
        print(f"✅ Indexed {self.index.ntotal} images")

    # ------------------------------------------------------------------
    # NEW METHOD ADDED (UNCHANGED AS PROVIDED)
    # ------------------------------------------------------------------

    def calibrate_threshold(self, dataset_path):
        """
        FIXED: Uses full path comparison for accurate metrics
        """
        print("⚖️ Calibrating threshold...")
        
        from utils import generate_proper_ground_truth, normalize_pair
        
        gt_pairs = generate_proper_ground_truth(dataset_path)
        history = []
        
        if not gt_pairs:
            print("⚠️ No ground truth")
            return config.DEFAULT_THRESHOLD, 0.0, [], []
        
        print(f"📊 Ground truth: {len(gt_pairs)} pairs")
        
        best_f1 = -1
        best_thresh = config.DEFAULT_THRESHOLD
        
        # Get ALL duplicates at minimum threshold
        min_thresh = min(config.CALIBRATION_THRESHOLDS)
        all_duplicates = self._find_duplicates_internal(threshold=min_thresh, silent=True)
        
        print(f"\n🔍 Found {len(all_duplicates)} total duplicate pairs at threshold {min_thresh}")
        
        # CRITICAL FIX: Use full paths for ground truth
        gt_set = set(normalize_pair(p) for p in gt_pairs)
        
        print(f"\n📋 Ground truth uses FULL PATHS:")
        for i, pair in enumerate(list(gt_set)[:3]):
            print(f"   {i+1}. {pair}")
        
        for thresh in config.CALIBRATION_THRESHOLDS:
            # Filter duplicates by current threshold
            filtered = [d for d in all_duplicates if d['score'] >= thresh]
            
            # CRITICAL FIX: Normalize detected pairs with FULL PATHS
            det_set = set(normalize_pair((d['file1'], d['file2'])) for d in filtered)
            
            # Calculate metrics
            tp = len(det_set.intersection(gt_set))
            fp = len(det_set - gt_set)
            fn = len(gt_set - det_set)
            
            prec = tp / (tp + fp + config.EPSILON) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn + config.EPSILON) if (tp + fn) > 0 else 0
            f1 = 2 * (prec * rec) / (prec + rec + config.EPSILON) if (prec + rec) > 0 else 0
            
            history.append({
                "threshold": thresh,
                "f1": f1,
                "precision": prec,
                "recall": rec,
                "count": len(filtered),
                "tp": tp,
                "fp": fp,
                "fn": fn
            })
            
            print(f"  Thresh {thresh:.2f}: F1={f1:.4f}, Prec={prec:.4f}, Rec={rec:.4f}, "
                  f"Detected={len(filtered)}, TP={tp}, FP={fp}, FN={fn}")
            
            if f1 >= best_f1:
                best_f1 = f1
                best_thresh = thresh
        
        print(f"\n✅ Optimal: {best_thresh:.2f} (F1: {best_f1:.4f})")
        self.optimal_threshold = best_thresh
        
        return best_thresh, best_f1, history, gt_pairs

    

    
    def _find_duplicates_internal(self, threshold, silent=False):
        duplicates = list(self.fast_duplicates)
        
        if self.index.ntotal < 2:
            return duplicates
        
        chunk_size = 1000
        k = 20
        seen_pairs = set()
        
        iterator = range(0, self.index.ntotal, chunk_size)
        if not silent:
            iterator = tqdm(iterator, desc="Finding duplicates")
        
        for start in iterator:
            end = min(start + chunk_size, self.index.ntotal)
            vecs = self.index.reconstruct_n(start, end - start)
            D, I = self.index.search(vecs, k)
            
            for i in range(len(vecs)):
                abs_i = start + i
                
                for j in range(1, k):
                    score = float(D[i][j])
                    idx_n = int(I[i][j])
                    
                    if idx_n == -1 or abs_i == idx_n:
                        continue
                    
                    if score >= threshold:
                        f1 = self.stored_files[abs_i]
                        f2 = self.stored_files[idx_n]
                        
                        if f1 == f2:
                            continue
                        
                        pair = tuple(sorted((f1, f2)))
                        if pair not in seen_pairs:
                            duplicates.append({
                                "file1": f1,
                                "file2": f2,
                                "score": score,
                                "method": "DINOv2"
                            })
                            seen_pairs.add(pair)
        
        return duplicates
    
    def find_duplicates(self, threshold=None):
        t = threshold if threshold is not None else self.optimal_threshold
        return self._find_duplicates_internal(t)
    
    def find_matches_for_file(self, file_path, threshold=None, top_k=50):
        """Single file matching - works correctly"""
        threshold = threshold or self.optimal_threshold
        
        vec = self._generate_embedding(file_path)
        if vec is None:
            return []
        
        D, I = self.index.search(vec, min(top_k, self.index.ntotal))
        
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score >= threshold:
                results.append({
                    "path": self.stored_files[idx],
                    "score": float(score),
                    "method": "DINOv2"
                })
        
        return results