import { Scan, Settings, Zap } from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({
  datasetPath,
  setDatasetPath,
  threshold,
  setThreshold,
  selectedModel,
  setSelectedModel,
  availableModels,
  onScan,
  isScanning,
  scanStatus,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-content">
        <div className="sidebar-section">
          <div className="sidebar-header">
            <Settings size={20} />
            <h2>Settings</h2>
          </div>

          <div className="form-group">
            <label htmlFor="model-select">Model</label>
            <select
              id="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="select-input"
            >
              {Object.entries(availableModels).map(([label, value]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="dataset-path">Dataset Path</label>
            <input
              id="dataset-path"
              type="text"
              value={datasetPath}
              onChange={(e) => setDatasetPath(e.target.value)}
              className="text-input"
              placeholder="./dataset_copydays"
            />
          </div>

          <div className="form-group">
            <label htmlFor="threshold">
              Similarity Threshold: {threshold}%
            </label>
            <input
              id="threshold"
              type="range"
              min="50"
              max="100"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="range-input"
            />
            <div className="range-labels">
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <button
            onClick={onScan}
            disabled={isScanning}
            className="scan-button"
          >
            {isScanning ? (
              <>
                <Zap className="button-icon spinning" size={20} />
                Scanning...
              </>
            ) : (
              <>
                <Scan className="button-icon" size={20} />
                Fresh Scan
              </>
            )}
          </button>

          {scanStatus && (
            <div className={`status-message ${isScanning ? 'info' : 'success'}`}>
              {scanStatus}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

