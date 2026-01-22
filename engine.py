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
import pickle
import hashlib
import config
from utils import walk_image_files, auto_generate_ground_truth, normalize_pair

warnings.filterwarnings('ignore')
os.environ["KMP_DUPLICATE_LIB_OK"] = config.ENV_KMP_DUPLICATE_LIB

class DuplicateDetector:
    def __init__(self):
        print(f"🚀 Initializing Detector on {config.DEVICE}")
        self.device = config.DEVICE
        
        # Load model
        self.processor = AutoImageProcessor.from_pretrained(config.MODEL_ID)
        self.model = AutoModel.from_pretrained(config.MODEL_ID).to(self.device)
        self.model.eval()
        
        # Initialize FAISS index
        self.dimension = self.model.config.hidden_size
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Storage
        self.stored_files = []
        self.hash_buckets = defaultdict(list)
        self.fast_duplicates = []
        self.optimal_threshold = config.DEFAULT_THRESHOLD
        self.file_checksums = {}  # For incremental indexing
        
        # Try to load existing index
        if config.ENABLE_INCREMENTAL_INDEXING:
            self._load_index()
    
    def _compute_file_checksum(self, filepath):
        """Compute MD5 checksum for file change detection"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None
    
    def _generate_embedding(self, image_path):
        """Generate DINOv2 embedding for image"""
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
            print(f"⚠️ Failed to process {image_path}: {str(e)}")
            return None
    
    def _compute_hash(self, image_path):
        """Compute perceptual hash for image"""
        try:
            img = Image.open(image_path).convert('RGB')
            return str(imagehash.dhash(img, hash_size=config.HASH_SIZE))
        except:
            return None
    
    def bulk_index(self, folder, force_rescan=False):
        """
        Index all images in folder with incremental support.
        
        Args:
            folder: Path to image directory
            force_rescan: If True, rebuild index from scratch
        """
        if not os.path.exists(folder):
            print(f"❌ Folder not found: {folder}")
            return
        
        files = list(walk_image_files(folder))
        print(f"📁 Found {len(files)} images")
        
        if not force_rescan and config.ENABLE_INCREMENTAL_INDEXING:
            # Incremental mode: only process new/changed files
            files_to_process = []
            for f in files:
                checksum = self._compute_file_checksum(f)
                if checksum and (f not in self.file_checksums or self.file_checksums[f] != checksum):
                    files_to_process.append(f)
                    self.file_checksums[f] = checksum
            
            if files_to_process:
                print(f"⚡ Incremental update: {len(files_to_process)} new/modified files")
                files = files_to_process
            else:
                print("✓ No changes detected - index is up to date")
                return
        else:
            # Full rescan
            self.stored_files = []
            self.hash_buckets = defaultdict(list)
            self.fast_duplicates = []
            self.index = faiss.IndexFlatIP(self.dimension)
            self.file_checksums = {}
            
            for f in files:
                checksum = self._compute_file_checksum(f)
                if checksum:
                    self.file_checksums[f] = checksum
        
        # Phase 1: Hash-based deduplication
        print(f"⚡ Phase 1: Hashing {len(files)} images...")
        files_for_dino = []
        
        for f in tqdm(files, desc="Hashing"):
            h = self._compute_hash(f)
            if not h:
                continue
            
            # Check for hash collisions
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
        
        # Phase 2: DINOv2 embedding
        if files_for_dino:
            print(f"🧠 Phase 2: DINOv2 Embedding ({len(files_for_dino)} unique images)...")
            batch_vecs = []
            batch_files = []
            
            for f in tqdm(files_for_dino, desc="Embedding"):
                vec = self._generate_embedding(f)
                if vec is not None:
                    batch_vecs.append(vec)
                    batch_files.append(f)
                    
                    # Process in batches
                    if len(batch_vecs) >= config.BATCH_SIZE:
                        self.index.add(np.vstack(batch_vecs))
                        self.stored_files.extend(batch_files)
                        batch_vecs = []
                        batch_files = []
            
            # Add remaining
            if batch_vecs:
                self.index.add(np.vstack(batch_vecs))
                self.stored_files.extend(batch_files)
        
        print(f"✅ Indexed {self.index.ntotal} images ({len(self.fast_duplicates)} hash matches)")
        
        # Save index
        if config.ENABLE_INCREMENTAL_INDEXING:
            self._save_index()
    
    def calibrate_threshold(self, dataset_path):
        """
        Auto-calibrate optimal similarity threshold using ground truth.
        
        Returns:
            (optimal_threshold, best_f1_score, calibration_history)
        """
        print("⚖️ Calibrating optimal threshold...")
        
        gt_pairs = auto_generate_ground_truth(dataset_path)
        history = []
        
        if not gt_pairs:
            print("⚠️ No ground truth pairs found")
            return config.DEFAULT_THRESHOLD, 0.0, []
        
        print(f"📊 Found {len(gt_pairs)} ground truth pairs")
        
        best_f1 = -1
        best_thresh = config.DEFAULT_THRESHOLD
        
        # Get all candidates once at lowest threshold
        min_thresh = min(config.CALIBRATION_THRESHOLDS)
        base_duplicates = self._find_duplicates_internal(threshold=min_thresh, silent=True)
        
        for thresh in config.CALIBRATION_THRESHOLDS:
            # Filter by current threshold
            filtered = [d for d in base_duplicates if d['score'] >= thresh]
            
            # Calculate metrics
            det_set = set(normalize_pair((d['file1'], d['file2'])) for d in filtered)
            gt_set = set(normalize_pair(p) for p in gt_pairs)
            
            tp = len(det_set.intersection(gt_set))
            fp = len(det_set - gt_set)
            fn = len(gt_set - det_set)
            
            prec = tp / (tp + fp + config.EPSILON)
            rec = tp / (tp + fn + config.EPSILON)
            f1 = 2 * (prec * rec) / (prec + rec + config.EPSILON)
            
            history.append({
                "threshold": thresh,
                "f1": f1,
                "precision": prec,
                "recall": rec,
                "count": len(filtered)
            })
            
            if f1 >= best_f1:
                best_f1 = f1
                best_thresh = thresh
        
        print(f"✅ Optimal Threshold: {best_thresh:.2f} (F1: {best_f1:.4f})")
        self.optimal_threshold = best_thresh
        
        return best_thresh, best_f1, history
    
    def _find_duplicates_internal(self, threshold, silent=False):
        """Internal method to find duplicates at given threshold"""
        duplicates = list(self.fast_duplicates)
        
        if self.index.ntotal < 2:
            return duplicates
        
        chunk_size = 1000
        k = 20  # Higher k to capture loose matches
        seen_pairs = set()
        
        total_chunks = (self.index.ntotal + chunk_size - 1) // chunk_size
        
        iterator = range(0, self.index.ntotal, chunk_size)
        if not silent:
            iterator = tqdm(iterator, desc="Finding duplicates", total=total_chunks)
        
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
        """
        Find all duplicate pairs at given threshold.
        
        Args:
            threshold: Similarity threshold (uses optimal if None)
        
        Returns:
            List of duplicate pairs with scores
        """
        t = threshold if threshold is not None else self.optimal_threshold
        return self._find_duplicates_internal(t)
    
    def find_matches_for_file(self, file_path, threshold=None, top_k=10):
        """
        Find similar images for a query file.
        
        Args:
            file_path: Path to query image
            threshold: Minimum similarity score
            top_k: Maximum number of results
        
        Returns:
            List of matching images with scores
        """
        threshold = threshold or self.optimal_threshold
        
        vec = self._generate_embedding(file_path)
        if vec is None:
            return []
        
        D, I = self.index.search(vec, top_k)
        
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and score >= threshold:
                results.append({
                    "path": self.stored_files[idx],
                    "score": float(score),
                    "method": "DINOv2"
                })
        
        return results
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            os.makedirs(config.INDEX_SAVE_PATH, exist_ok=True)
            
            # Save FAISS index
            index_path = os.path.join(config.INDEX_SAVE_PATH, "faiss.index")
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            metadata = {
                'stored_files': self.stored_files,
                'hash_buckets': dict(self.hash_buckets),
                'fast_duplicates': self.fast_duplicates,
                'optimal_threshold': self.optimal_threshold,
                'file_checksums': self.file_checksums
            }
            
            metadata_path = os.path.join(config.INDEX_SAVE_PATH, "metadata.pkl")
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            print(f"💾 Index saved to {config.INDEX_SAVE_PATH}")
        except Exception as e:
            print(f"⚠️ Failed to save index: {str(e)}")
    
    def _load_index(self):
        """Load existing FAISS index and metadata from disk"""
        try:
            index_path = os.path.join(config.INDEX_SAVE_PATH, "faiss.index")
            metadata_path = os.path.join(config.INDEX_SAVE_PATH, "metadata.pkl")
            
            if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
                return False
            
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.stored_files = metadata.get('stored_files', [])
            self.hash_buckets = defaultdict(list, metadata.get('hash_buckets', {}))
            self.fast_duplicates = metadata.get('fast_duplicates', [])
            self.optimal_threshold = metadata.get('optimal_threshold', config.DEFAULT_THRESHOLD)
            self.file_checksums = metadata.get('file_checksums', {})
            
            print(f"✅ Loaded existing index: {len(self.stored_files)} images")
            return True
        except Exception as e:
            print(f"⚠️ Could not load index: {str(e)}")
            return False
    
    def get_stats(self):
        """Return detector statistics"""
        return {
            'total_indexed': self.index.ntotal,
            'hash_matches': len(self.fast_duplicates),
            'total_files': len(self.stored_files),
            'optimal_threshold': self.optimal_threshold
        }
