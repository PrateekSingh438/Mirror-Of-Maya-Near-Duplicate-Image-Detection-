
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import base64
from pathlib import Path

from engine import DuplicateDetector
from evaluate import calculate_metrics, analyze_match_types
from utils import (
    get_dir_size, 
    auto_generate_ground_truth,
    calculate_wasted_space,
    organize_clusters_with_originals,
    auto_select_duplicates_for_deletion
)
import config

# Initialize FastAPI
app = FastAPI(
    title="Mirror of Maya API",
    description="Sudarshana Chakra of Digital Truth - Near-Duplicate Image Detection",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global detector instance
detector = None
current_duplicates = []
scan_progress = {"status": "idle", "progress": 0, "message": ""}

# Request/Response Models
class ScanRequest(BaseModel):
    dataset_path: str
    threshold: float = 0.85
    model: str = "Small"

class DeleteRequest(BaseModel):
    file_paths: List[str]

class ScanStatus(BaseModel):
    status: str
    progress: int
    message: str

# Helper Functions
def get_image_base64(image_path: str) -> str:
    """Convert image to base64 for frontend display"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except:
        return None

def update_scan_progress(status: str, progress: int, message: str):
    """Update global scan progress"""
    scan_progress["status"] = status
    scan_progress["progress"] = progress
    scan_progress["message"] = message

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Mirror of Maya API",
        "status": "active",
        "version": "1.0.0"
    }

@app.get("/api/status")
async def get_status():
    """Get current scan status"""
    return scan_progress

@app.post("/api/scan")
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Start scanning for duplicates
    This runs in background to avoid timeout
    """
    global detector, current_duplicates
    
    # Validate dataset path
    if not os.path.exists(request.dataset_path):
        raise HTTPException(status_code=400, detail="Dataset path does not exist")
    
    # Update model if changed
    model_map = {
        "Small": "facebook/dinov2-small",
        "Base": "facebook/dinov2-base",
        "Large": "facebook/dinov2-large"
    }
    
    if request.model in model_map:
        config.MODEL_ID = model_map[request.model]
    
    # Start background task
    def scan_task():
        global detector, current_duplicates
        try:
            update_scan_progress("scanning", 10, "Initializing detector...")
            detector = DuplicateDetector()
            
            update_scan_progress("scanning", 30, "Indexing images...")
            detector.bulk_index(request.dataset_path)
            
            update_scan_progress("scanning", 70, "Finding duplicates...")
            current_duplicates = detector.find_duplicates(threshold=request.threshold)
            
            update_scan_progress("complete", 100, f"Found {len(current_duplicates)} duplicate pairs")
        except Exception as e:
            update_scan_progress("error", 0, str(e))
    
    background_tasks.add_task(scan_task)
    
    return {
        "status": "started",
        "message": "Scan started in background. Check /api/status for progress."
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get detection metrics and statistics"""
    global current_duplicates
    
    if not current_duplicates:
        raise HTTPException(status_code=400, detail="No scan results available. Run scan first.")
    
    dataset_path = config.DATASET_PATH
    
    # Calculate metrics
    original_mb = get_dir_size(dataset_path)
    wasted_size_mb = calculate_wasted_space(current_duplicates)
    
    ground_truth = auto_generate_ground_truth(dataset_path)
    f1_score = calculate_metrics(
        [(d['file1'], d['file2']) for d in current_duplicates],
        ground_truth
    ) if ground_truth else 0.0
    
    analysis = analyze_match_types(current_duplicates)
    
    return {
        "totalStorage": round(original_mb, 2),
        "potentialSavings": round(wasted_size_mb, 2),
        "duplicatePairs": len(current_duplicates),
        "f1Score": round(f1_score, 4),
        "savingsPercentage": round((wasted_size_mb / original_mb * 100) if original_mb > 0 else 0, 2),
        "qualityCheck": {
            "originalsRecovered": analysis['recovery'],
            "crossMatches": analysis['cross'],
            "recoveryPercent": round(analysis['recovery_pct'], 2),
            "crossPercent": round(analysis['cross_pct'], 2)
        }
    }

@app.get("/api/clusters")
async def get_clusters(page: int = 0, per_page: int = 5):
    """Get organized duplicate clusters with pagination"""
    global current_duplicates
    
    if not current_duplicates:
        raise HTTPException(status_code=400, detail="No scan results available")
    
    # Organize clusters
    organized = organize_clusters_with_originals(current_duplicates)
    
    # Pagination
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_clusters = organized[start_idx:end_idx]
    
    # Convert to response format with base64 images
    response_clusters = []
    for cluster in page_clusters:
        response_clusters.append({
            "id": organized.index(cluster) + 1,
            "original": cluster['original'],
            "originalBase64": get_image_base64(cluster['original']),
            "duplicates": [
                {
                    "path": dup['path'],
                    "score": round(dup['score'], 4),
                    "imageBase64": get_image_base64(dup['path'])
                }
                for dup in cluster['duplicates']
            ],
            "totalCount": cluster['total_count']
        })
    
    return {
        "clusters": response_clusters,
        "totalClusters": len(organized),
        "currentPage": page,
        "totalPages": (len(organized) + per_page - 1) // per_page,
        "hasMore": end_idx < len(organized)
    }

@app.get("/api/image/{image_path:path}")
async def get_image(image_path: str):
    """Serve image file"""
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path)

@app.post("/api/query")
async def query_image(file: UploadFile = File(...), threshold: float = 0.85):
    """
    Query for similar images
    Upload an image and find matches in the database
    """
    global detector
    
    if detector is None:
        raise HTTPException(status_code=400, detail="No index available. Run scan first.")
    
    # Save uploaded file temporarily
    temp_path = config.TEMP_QUERY_FILE
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Find matches
        results = detector.find_matches_for_file(temp_path, threshold=threshold)
        
        # Format response
        formatted_results = [
            {
                "path": result['path'],
                "score": round(result['score'], 4),
                "method": result['method'],
                "imageBase64": get_image_base64(result['path'])
            }
            for result in results
        ]
        
        return {
            "queryImage": get_image_base64(temp_path),
            "matches": formatted_results,
            "totalMatches": len(formatted_results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/delete")
async def delete_files(request: DeleteRequest):
    """
    Delete selected duplicate files
    """
    deleted = []
    failed = []
    
    for file_path in request.file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted.append(file_path)
            else:
                failed.append({"path": file_path, "reason": "File not found"})
        except Exception as e:
            failed.append({"path": file_path, "reason": str(e)})
    
    return {
        "deleted": len(deleted),
        "failed": len(failed),
        "deletedFiles": deleted,
        "failedFiles": failed
    }

@app.post("/api/auto-select")
async def auto_select_all():
    """
    Get list of all duplicate files for auto-selection
    """
    global current_duplicates
    
    if not current_duplicates:
        raise HTTPException(status_code=400, detail="No scan results available")
    
    organized = organize_clusters_with_originals(current_duplicates)
    selected = auto_select_duplicates_for_deletion(organized)
    
    return {
        "selectedFiles": list(selected),
        "totalFiles": len(selected)
    }

@app.get("/api/galaxy-data")
async def get_galaxy_visualization():
    """
    Get PCA-reduced embedding data for galaxy visualization
    """
    global detector
    
    if detector is None or detector.index.ntotal == 0:
        raise HTTPException(status_code=400, detail="No embeddings available")
    
    from sklearn.decomposition import PCA
    import pandas as pd
    
    ntotal = detector.index.ntotal
    limit = min(ntotal, config.MAX_GALAXY_PLOT_IMAGES)
    
    # Get embeddings
    vectors = detector.index.reconstruct_n(0, limit)
    filenames = [os.path.basename(f) for f in detector.stored_files[:limit]]
    
    # Reduce dimensions
    pca = PCA(n_components=2)
    vecs_2d = pca.fit_transform(vectors)
    
    # Format for frontend
    points = [
        {
            "x": float(vecs_2d[i][0]),
            "y": float(vecs_2d[i][1]),
            "filename": filenames[i]
        }
        for i in range(len(vecs_2d))
    ]
    
    return {
        "points": points,
        "totalPoints": len(points),
        "variance": pca.explained_variance_ratio_.tolist()
    }

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "model": config.MODEL_ID,
        "device": config.DEVICE,
        "threshold": config.SIMILARITY_THRESHOLD,
        "batchSize": config.BATCH_SIZE,
        "datasetPath": config.DATASET_PATH
    }

@app.post("/api/config")
async def update_config(
    model: Optional[str] = None,
    threshold: Optional[float] = None,
    dataset_path: Optional[str] = None
):
    """Update configuration"""
    if model:
        model_map = {
            "Small": "facebook/dinov2-small",
            "Base": "facebook/dinov2-base",
            "Large": "facebook/dinov2-large"
        }
        if model in model_map:
            config.MODEL_ID = model_map[model]
    
    if threshold:
        config.SIMILARITY_THRESHOLD = threshold
    
    if dataset_path:
        if os.path.exists(dataset_path):
            config.DATASET_PATH = dataset_path
        else:
            raise HTTPException(status_code=400, detail="Dataset path does not exist")
    
    return {"message": "Configuration updated", "config": await get_config()}

# Run with: uvicorn api:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)