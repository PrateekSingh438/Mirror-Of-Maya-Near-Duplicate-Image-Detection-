import { useState, useRef } from 'react';
import { Upload, Search, Image as ImageIcon, X } from 'lucide-react';
import { apiService } from '../services/api.js';
import './QueryTool.css';

const QueryTool = ({ threshold }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setResults([]);
    }
  };

  const handleSearch = async () => {
    if (!selectedFile) return;

    setIsSearching(true);
    try {
      const data = await apiService.search(selectedFile, threshold);
      setResults(data.results || []);
    } catch (error) {
      console.error('Search failed:', error);
      alert(error.response?.data?.detail || 'Search failed. Please scan a dataset first.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setResults([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getImageUrl = (filePath) => {
    if (filePath.startsWith('http')) {
      return filePath;
    }
    return `/images?path=${encodeURIComponent(filePath)}`;
  };

  return (
    <div className="query-tool">
      <div className="query-header">
        <h2>Query Tool - Sudarshana Chakra Search</h2>
        <p className="query-subtitle">Upload an image to find its duplicates across the dataset</p>
      </div>

      <div className="query-container">
        <div className="upload-section">
          <div
            className="upload-area"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              e.currentTarget.classList.add('dragover');
            }}
            onDragLeave={(e) => {
              e.currentTarget.classList.remove('dragover');
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove('dragover');
              const file = e.dataTransfer.files[0];
              if (file && file.type.startsWith('image/')) {
                setSelectedFile(file);
                const url = URL.createObjectURL(file);
                setPreviewUrl(url);
                setResults([]);
              }
            }}
          >
            {previewUrl ? (
              <div className="preview-container">
                <img src={previewUrl} alt="Preview" className="preview-image" />
                <button onClick={handleClear} className="clear-button">
                  <X size={20} />
                </button>
              </div>
            ) : (
              <>
                <Upload size={48} className="upload-icon" />
                <p className="upload-text">Click or drag an image here</p>
                <p className="upload-hint">Supports JPG, PNG, BMP</p>
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="file-input"
            />
          </div>

          {selectedFile && (
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="search-button"
            >
              {isSearching ? (
                <>
                  <div className="spinner-small"></div>
                  Searching...
                </>
              ) : (
                <>
                  <Search size={20} />
                  Search for Duplicates
                </>
              )}
            </button>
          )}
        </div>

        {results.length > 0 && (
          <div className="results-section">
            <h3>Found {results.length} match{results.length !== 1 ? 'es' : ''}</h3>
            <div className="results-grid">
              {results.map((result, idx) => {
                const imageUrl = getImageUrl(result.path);
                const fileName = result.path.split(/[/\\]/).pop() || result.path;

                return (
                  <div key={idx} className="result-card">
                    <div className="result-image-wrapper">
                      <img
                        src={imageUrl}
                        alt={fileName}
                        onError={(e) => {
                          e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzJBMkEyQSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM3RjdGN0YiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';
                        }}
                      />
                      <div className="similarity-badge">
                        {(result.score * 100).toFixed(1)}%
                      </div>
                    </div>
                    <p className="result-name" title={fileName}>
                      {fileName}
                    </p>
                    <p className="result-score">
                      Similarity: {(result.score * 100).toFixed(2)}%
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {results.length === 0 && selectedFile && !isSearching && (
          <div className="no-results">
            <ImageIcon size={48} className="no-results-icon" />
            <p>No matches found. Try adjusting the similarity threshold.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default QueryTool;

