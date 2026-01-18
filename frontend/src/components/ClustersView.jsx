import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Trash2, Image as ImageIcon } from 'lucide-react';
import { apiService } from '../services/api.js';
import './ClustersView.css';

const ClustersPerPage = 5;

const ClustersView = () => {
  const [clusters, setClusters] = useState([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalClusters, setTotalClusters] = useState(0);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadClusters();
  }, [currentPage]);

  const loadClusters = async () => {
    setIsLoading(true);
    try {
      const data = await apiService.getClusters(currentPage, ClustersPerPage);
      setClusters(data.clusters);
      setTotalClusters(data.total);
    } catch (error) {
      console.error('Failed to load clusters:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileToggle = (filePath) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(filePath)) {
      newSelected.delete(filePath);
    } else {
      newSelected.add(filePath);
    }
    setSelectedFiles(newSelected);
  };

  const handleDelete = async () => {
    if (selectedFiles.size === 0) return;

    if (!confirm(`Are you sure you want to delete ${selectedFiles.size} files?`)) {
      return;
    }

    try {
      await apiService.deleteFiles(Array.from(selectedFiles));
      setSelectedFiles(new Set());
      loadClusters();
      alert('Files deleted successfully!');
    } catch (error) {
      console.error('Failed to delete files:', error);
      alert('Failed to delete files');
    }
  };

  const totalPages = Math.ceil(totalClusters / ClustersPerPage);

  return (
    <div className="clusters-view">
      <div className="clusters-header">
        <h2>Galaxy Clusters</h2>
        <p className="clusters-subtitle">Visualize and manage duplicate image clusters</p>
      </div>

      {selectedFiles.size > 0 && (
        <div className="delete-banner">
          <span>{selectedFiles.size} files selected for deletion</span>
          <button onClick={handleDelete} className="delete-button">
            <Trash2 size={16} />
            Execute Deletion
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading clusters...</p>
        </div>
      ) : clusters.length === 0 ? (
        <div className="empty-state">
          <ImageIcon size={64} className="empty-icon" />
          <p>No clusters found. Please scan a dataset first.</p>
        </div>
      ) : (
        <>
          <div className="clusters-grid">
            {clusters.map((cluster) => (
              <div key={cluster.id} className="cluster-card">
                <div className="cluster-header">
                  <h3>Cluster {cluster.id}</h3>
                  <span className="cluster-count">{cluster.count} images</span>
                </div>
                <div className="cluster-images">
                  {cluster.files.map((filePath, idx) => {
                    const fileName = filePath.split(/[/\\]/).pop() || filePath;
                    const isSelected = selectedFiles.has(filePath);
                    const imageUrl = filePath.startsWith('http') 
                      ? filePath 
                      : `/images?path=${encodeURIComponent(filePath)}`;

                    return (
                      <div
                        key={idx}
                        className={`image-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => handleFileToggle(filePath)}
                      >
                        <div className="image-wrapper">
                          <img
                            src={imageUrl}
                            alt={fileName}
                            onError={(e) => {
                              e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzJBMkEyQSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM3RjdGN0YiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';
                            }}
                          />
                          {isSelected && (
                            <div className="selected-overlay">
                              <div className="selected-checkmark">✓</div>
                            </div>
                          )}
                        </div>
                        <p className="image-name" title={fileName}>
                          {fileName}
                        </p>
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleFileToggle(filePath)}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <span>Delete</span>
                        </label>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="pagination">
            <button
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className="pagination-button"
            >
              <ChevronLeft size={20} />
              Previous
            </button>
            <span className="pagination-info">
              Page {currentPage + 1} of {totalPages} ({totalClusters} clusters)
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              className="pagination-button"
            >
              Next
              <ChevronRight size={20} />
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ClustersView;

