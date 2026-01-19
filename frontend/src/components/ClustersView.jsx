import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Trash2, Image as ImageIcon } from 'lucide-react';
import { apiService } from '../services/api.js';

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
    <div className="p-6">
      <div className="mb-8">
        <h2 className="text-4xl font-bold text-gradient-saffron mb-3">Cosmic Clusters</h2>
        <p className="text-parchment-300">Organize and purify the illusions - manage duplicate form collections</p>
      </div>

      {selectedFiles.size > 0 && (
        <div className="mb-6 p-4 bg-red-600/20 border border-red-400 rounded-lg flex items-center justify-between animate-pulse">
          <span className="text-red-300">
            {selectedFiles.size} illusory form{selectedFiles.size !== 1 ? 's' : ''} marked for dissolution
          </span>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold transition-all duration-300 transform hover:scale-105"
          >
            <Trash2 size={16} />
            Purify Collection
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-saffron-400 border-t-gold mb-4"></div>
          <p className="text-parchment-300 text-lg">Loading clusters...</p>
        </div>
      ) : clusters.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <ImageIcon size={64} className="text-indigo-400 mb-4 animate-float" />
          <p className="text-parchment-300 text-lg">No clusters found. Begin discernment with the Chakra first.</p>
        </div>
      ) : (
        <>
          <div className="space-y-6">
            {clusters.map((cluster) => (
              <div key={cluster.id} className="card">
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-saffron-400/20">
                  <h3 className="text-xl font-bold text-saffron-400">Source Soul {cluster.id}</h3>
                  <span className="px-3 py-1 bg-indigo-900/50 border border-indigo-400 rounded-full text-indigo-300 text-sm font-semibold">
                    {cluster.count} manifestations
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {cluster.files.map((filePath, idx) => {
                    const fileName = filePath.split(/[/\\]/).pop() || filePath;
                    const isSelected = selectedFiles.has(filePath);
                    const imageUrl = filePath.startsWith('http')
                      ? filePath
                      : `/images?path=${encodeURIComponent(filePath)}`;

                    return (
                      <div
                        key={idx}
                        className="space-y-2 cursor-pointer group"
                        onClick={() => handleFileToggle(filePath)}
                      >
                        <div className={`relative overflow-hidden rounded-lg h-32 bg-maya-darker flex items-center justify-center border-2 transition-all duration-300 ${
                          isSelected
                            ? 'border-saffron-400 shadow-lg shadow-saffron-400/30'
                            : 'border-saffron-400/30 group-hover:border-saffron-400'
                        }`}>
                          <img
                            src={imageUrl}
                            alt={fileName}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                            onError={(e) => {
                              e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzJBMkEyQSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM3RjdGN0YiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';
                            }}
                          />
                          {isSelected && (
                            <div className="absolute inset-0 bg-saffron-400/20 flex items-center justify-center">
                              <div className="text-4xl font-bold text-saffron-300 animate-bounce">✓</div>
                            </div>
                          )}
                        </div>
                        <p className="text-parchment-200 text-sm truncate" title={fileName}>
                          {fileName}
                        </p>
                        <label className="flex items-center gap-2 cursor-pointer text-parchment-400 hover:text-saffron-300 transition-colors">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleFileToggle(filePath)}
                            onClick={(e) => e.stopPropagation()}
                            className="w-4 h-4 accent-saffron-400"
                          />
                          <span className="text-xs font-medium">Delete</span>
                        </label>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${
                currentPage === 0
                  ? 'bg-saffron-400/20 text-saffron-400/50 cursor-not-allowed'
                  : 'btn-primary'
              }`}
            >
              <ChevronLeft size={20} />
              Previous
            </button>
            <span className="text-parchment-300 font-medium text-center min-w-60">
              Page {currentPage + 1} of {totalPages} ({totalClusters} source souls)
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${
                currentPage >= totalPages - 1
                  ? 'bg-saffron-400/20 text-saffron-400/50 cursor-not-allowed'
                  : 'btn-primary'
              }`}
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

