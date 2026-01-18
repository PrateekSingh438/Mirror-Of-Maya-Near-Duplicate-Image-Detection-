from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
import networkx as nx
from typing import List, Optional
import uvicorn

from engine import DuplicateDetector
from evaluate import calculate_metrics, analyze_match_types
from utils import (
    get_dir_size, auto_generate_ground_truth, 
    calculate_wasted_space, is_original_file
)
import config

os.environ["KMP_DUPLICATE_LIB_OK"] = config.ENV_KMP_DUPLICATE_LIB

app = FastAPI(title="Mirror of Maya API", version="1.0.0")

# Request models
class ScanRequest(BaseModel):
    dataset_path: str
    threshold: Optional[float] = None
    model_id: Optional[str] = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (in production, use Redis or database)
detector_instance: Optional[DuplicateDetector] = None
current_duplicates: List[dict] = []
current_dataset_path: str = ""

def group_duplicates_into_clusters(duplicates_list):
    """Group duplicates into connected clusters"""
    if not duplicates_list:
        return []
    
    g = nx.Graph()
    for item in duplicates_list:
        g.add_edge(item['file1'], item['file2'])
    
    clusters = []
    for component in nx.connected_components(g):
        if len(component) > 1:
            clusters.append(list(component))
    return clusters

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Mirror of Maya API is running"}

@app.post("/api/scan")
async def scan_dataset(request: ScanRequest):
    """Scan a dataset for duplicates"""
    global detector_instance, current_duplicates, current_dataset_path
    
    try:
        dataset_path = request.dataset_path
        threshold = request.threshold
        model_id = request.model_id
        
        if model_id and model_id != config.MODEL_ID:
            config.MODEL_ID = model_id
        
        threshold_val = (threshold / 100.0) if threshold else config.SIMILARITY_THRESHOLD
        
        if not os.path.exists(dataset_path):
            raise HTTPException(status_code=404, detail=f"Dataset path not found: {dataset_path}")
        
        detector_instance = DuplicateDetector()
        detector_instance.bulk_index(dataset_path)
        current_duplicates = detector_instance.find_duplicates(threshold=threshold_val)
        current_dataset_path = dataset_path
        
        return {
            "status": "success",
            "message": "Scan complete",
            "duplicate_count": len(current_duplicates),
            "total_images": detector_instance.index.ntotal + len(detector_instance.phash_map)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/duplicates")
async def get_duplicates(page: int = 0, per_page: int = 50):
    """Get duplicate pairs with pagination"""
    global current_duplicates
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    return {
        "duplicates": current_duplicates[start_idx:end_idx],
        "total": len(current_duplicates),
        "page": page,
        "per_page": per_page
    }

@app.get("/api/clusters")
async def get_clusters(page: int = 0, per_page: int = 5):
    """Get duplicate clusters"""
    global current_duplicates
    
    clusters = group_duplicates_into_clusters(current_duplicates)
    clusters.sort(key=len, reverse=True)
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_clusters = clusters[start_idx:end_idx]
    
    # Format clusters with file info
    formatted_clusters = []
    for i, cluster in enumerate(current_clusters):
        cluster.sort()
        formatted_clusters.append({
            "id": start_idx + i + 1,
            "files": cluster,
            "count": len(cluster)
        })
    
    return {
        "clusters": formatted_clusters,
        "total": len(clusters),
        "page": page,
        "per_page": per_page
    }

@app.post("/api/search")
async def search_image(file: UploadFile = File(...), threshold: float = None):
    """Search for similar images"""
    global detector_instance
    
    if not detector_instance or detector_instance.index.ntotal == 0:
        raise HTTPException(status_code=400, detail="Please scan a dataset first")
    
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_search_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        threshold_val = (threshold / 100.0) if threshold else config.SIMILARITY_THRESHOLD
        results = detector_instance.find_matches_for_file(temp_path, threshold=threshold_val)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {
            "status": "success",
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    """Get analytics and metrics"""
    global current_duplicates, current_dataset_path, detector_instance
    
    if not current_duplicates:
        return {
            "status": "no_data",
            "message": "Please scan a dataset first"
        }
    
    original_mb = get_dir_size(current_dataset_path)
    wasted_size_mb = calculate_wasted_space(current_duplicates)
    optimized_mb = original_mb - wasted_size_mb
    pct_saved = (wasted_size_mb / original_mb * 100) if original_mb > 0 else 0
    
    ground_truth = auto_generate_ground_truth(current_dataset_path)
    f1 = calculate_metrics(
        [(d['file1'], d['file2']) for d in current_duplicates], 
        ground_truth
    ) if ground_truth else 0.0
    
    analysis = analyze_match_types(current_duplicates)
    
    return {
        "storage": {
            "total_mb": round(original_mb, 2),
            "wasted_mb": round(wasted_size_mb, 2),
            "optimized_mb": round(optimized_mb, 2),
            "percent_saved": round(pct_saved, 1)
        },
        "duplicates": {
            "total_pairs": len(current_duplicates),
            "clusters": len(group_duplicates_into_clusters(current_duplicates))
        },
        "model": {
            "f1_score": round(f1, 4),
            "analysis": analysis
        },
        "index": {
            "total_images": detector_instance.index.ntotal + len(detector_instance.phash_map) if detector_instance else 0
        }
    }

@app.post("/api/delete")
async def delete_files(file_paths: List[str]):
    """Delete selected files"""
    deleted = []
    errors = []
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted.append(file_path)
        except Exception as e:
            errors.append({"file": file_path, "error": str(e)})
    
    return {
        "status": "success",
        "deleted": deleted,
        "errors": errors,
        "deleted_count": len(deleted)
    }

@app.get("/api/models")
async def get_models():
    """Get available models"""
    return {
        "current": config.MODEL_ID,
        "available": config.MODEL_OPTIONS
    }

@app.get("/images")
async def serve_image(path: str = None):
    """Serve images from the dataset"""
    try:
        if not path:
            raise HTTPException(status_code=400, detail="Path parameter required")
        
        # Decode URL-encoded path
        path = path.replace('%5C', '\\').replace('/', os.sep)
        
        if not os.path.exists(path) or not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Security: Ensure path is within dataset
        dataset_path = os.path.abspath(current_dataset_path or config.DATASET_PATH)
        abs_path = os.path.abspath(path)
        
        # Allow paths within dataset
        if not abs_path.startswith(os.path.abspath(dataset_path)):
            # Fallback: allow if path is relative to current working directory
            cwd = os.path.abspath(os.getcwd())
            if not abs_path.startswith(cwd):
                raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(path, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

