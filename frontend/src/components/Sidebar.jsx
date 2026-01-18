import { Scan, Settings, Zap } from 'lucide-react';

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
    <aside className="fixed left-0 top-20 w-72 h-[calc(100vh-80px)] bg-gradient-to-b from-maya-darker/98 to-indigo-900/95 backdrop-blur-lg border-r border-saffron-400/20 overflow-y-auto z-40">
      <div className="p-6 space-y-6">
        {/* Settings Section */}
        <div>
          <div className="flex items-center gap-2 mb-4 text-saffron-400">
            <Settings size={20} />
            <h2 className="text-lg font-semibold">Sacred Settings</h2>
          </div>

          {/* Model Select */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-parchment-600 mb-2">Chakra Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="input-field text-sm"
            >
              {Object.entries(availableModels).map(([label, value]) => (
                <option key={value} value={value} className="bg-maya-darker">
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Dataset Path */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-parchment-600 mb-2">Image Collection</label>
            <input
              type="text"
              value={datasetPath}
              onChange={(e) => setDatasetPath(e.target.value)}
              className="input-field text-sm"
              placeholder="./dataset_copydays"
            />
          </div>

          {/* Threshold Slider */}
          <div>
            <label className="block text-sm font-medium text-parchment-600 mb-3">
              Discernment Threshold: <span className="text-saffron-400 font-bold">{threshold}%</span>
            </label>
            <input
              type="range"
              min="50"
              max="100"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full h-1 bg-indigo-700/30 rounded-lg appearance-none cursor-pointer accent-saffron-400"
            />
            <div className="flex justify-between text-xs text-parchment-700 mt-2">
              <span>Lenient</span>
              <span>Strict</span>
            </div>
          </div>
        </div>

        {/* Scan Section */}
        <div className="border-t border-indigo-700/30 pt-6">
          <button
            onClick={onScan}
            disabled={isScanning}
            className={`btn-primary w-full ${isScanning ? 'opacity-75 cursor-not-allowed' : ''}`}
          >
            {isScanning ? (
              <>
                <Zap className="w-5 h-5 animate-spin" />
                <span>Invoking Chakra...</span>
              </>
            ) : (
              <>
                <Scan className="w-5 h-5" />
                <span>Begin Discernment</span>
              </>
            )}
          </button>

          {/* Status Message */}
          {scanStatus && (
            <div className={`mt-4 p-3 rounded-lg text-sm ${
              isScanning 
                ? 'status-info' 
                : 'status-success'
            }`}>
              {scanStatus}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

