import { useState, useRef } from 'react';
import { Upload, Search, Image as ImageIcon, X } from 'lucide-react';
import { apiService } from '../services/api.js';

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
    <div className="p-6">
      <div className="mb-8">
        <h2 className="text-4xl font-bold text-gradient-saffron mb-3">Chakra Inquiry - Sudarshana Search</h2>
        <p className="text-parchment-300">Offer an image to the Chakra to reveal its duplicates across all realms</p>
      </div>

      <div className="space-y-8">
        <div className="space-y-4">
          <div
            className={`border-2 border-dashed rounded-lg p-8 cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-96 ${
              previewUrl
                ? 'border-saffron-400 bg-saffron-400/5'
                : 'border-saffron-400/40 hover:border-saffron-400 hover:bg-saffron-400/10'
            }`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              e.currentTarget.classList.add('ring-2', 'ring-saffron-300', 'ring-offset-2', 'ring-offset-maya-dark');
            }}
            onDragLeave={(e) => {
              e.currentTarget.classList.remove('ring-2', 'ring-saffron-300', 'ring-offset-2', 'ring-offset-maya-dark');
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove('ring-2', 'ring-saffron-300', 'ring-offset-2', 'ring-offset-maya-dark');
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
              <div className="relative w-full h-full flex items-center justify-center group">
                <img src={previewUrl} alt="Preview" className="max-w-full max-h-80 rounded-lg object-contain" />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleClear();
                  }}
                  className="absolute top-2 right-2 p-2 bg-red-600 hover:bg-red-700 rounded-full text-white shadow-lg transform group-hover:scale-110 transition-transform"
                >
                  <X size={20} />
                </button>
              </div>
            ) : (
              <>
                <Upload size={48} className="text-saffron-400 mb-4 animate-bounce" />
                <p className="text-xl text-parchment-200 font-medium">Offer your image to the Chakra</p>
                <p className="text-parchment-400 text-sm mt-2">JPG, PNG, BMP supported</p>
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {selectedFile && (
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className={`w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all duration-300 ${
                isSearching
                  ? 'bg-saffron-500 text-maya-darker cursor-wait opacity-80'
                  : 'btn-primary'
              }`}
            >
              {isSearching ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-maya-darker border-t-parchment-300"></div>
                  Searching...
                </>
              ) : (
                <>
                  <Search size={20} />
                  Invoke Sudarshana
                </>
              )}
            </button>
          )}
        </div>

        {results.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-2xl font-bold text-saffron-400">Maya Detected - {results.length} form{results.length !== 1 ? 's' : ''}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.map((result, idx) => {
                const imageUrl = getImageUrl(result.path);
                const fileName = result.path.split(/[/\\]/).pop() || result.path;

                return (
                  <div
                    key={idx}
                    className="card group hover:shadow-lg hover:shadow-saffron-400/20 transform hover:-translate-y-1 transition-all duration-300"
                  >
                    <div className="relative mb-3 overflow-hidden rounded-md h-48 bg-maya-darker flex items-center justify-center">
                      <img
                        src={imageUrl}
                        alt={fileName}
                        className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzJBMkEyQSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM3RjdGN0YiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';
                        }}
                      />
                      <div className="absolute top-2 right-2 px-3 py-1 bg-gradient-to-r from-saffron-400 to-gold rounded-full text-maya-darker font-bold text-sm shadow-lg">
                        {(result.score * 100).toFixed(1)}%
                      </div>
                    </div>
                    <p className="text-parchment-200 font-medium truncate" title={fileName}>
                      {fileName}
                    </p>
                    <p className="text-parchment-400 text-sm">
                      Similarity: {(result.score * 100).toFixed(2)}%
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {results.length === 0 && selectedFile && !isSearching && (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <ImageIcon size={48} className="text-indigo-400 animate-float" />
            <p className="text-parchment-300 text-lg">No illusions detected. The source soul stands unique and true.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default QueryTool;

