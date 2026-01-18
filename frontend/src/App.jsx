import { useState, useEffect } from 'react';
import Header from './components/Header.jsx';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './components/Dashboard.jsx';
import ClustersView from './components/ClustersView.jsx';
import QueryTool from './components/QueryTool.jsx';
import MetricsView from './components/MetricsView.jsx';
import { apiService } from './services/api.js';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [datasetPath, setDatasetPath] = useState('./dataset_copydays');
  const [threshold, setThreshold] = useState(82);
  const [selectedModel, setSelectedModel] = useState('facebook/dinov2-base');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [availableModels, setAvailableModels] = useState({});

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const data = await apiService.getModels();
      setAvailableModels(data.available);
      setSelectedModel(data.current);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const handleScan = async () => {
    setIsScanning(true);
    setScanStatus('Scanning dataset...');
    try {
      const result = await apiService.scan({
        dataset_path: datasetPath,
        threshold: threshold,
        model_id: selectedModel,
      });
      setScanStatus(`Scan complete! Found ${result.duplicate_count} duplicate pairs.`);
      loadMetrics();
    } catch (error) {
      setScanStatus(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const loadMetrics = async () => {
    try {
      const data = await apiService.getMetrics();
      if (data.status !== 'no_data') {
        setMetrics(data);
      }
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  return (
    <div className="min-h-screen bg-maya-dark">
      <Header />
      <Sidebar
        datasetPath={datasetPath}
        setDatasetPath={setDatasetPath}
        threshold={threshold}
        setThreshold={setThreshold}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        availableModels={availableModels}
        onScan={handleScan}
        isScanning={isScanning}
        scanStatus={scanStatus}
      />
      <main className="ml-72 mt-20 min-h-screen">
        <div className="sticky top-20 z-40 bg-maya-dark/95 backdrop-blur-lg border-b border-saffron-400/20 px-6 py-4">
          <div className="flex gap-2 flex-wrap">
            <button
              className={`px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${
                activeTab === 'dashboard'
                  ? 'bg-saffron-400 text-maya-darker shadow-lg shadow-saffron-400/30'
                  : 'bg-indigo-900/50 text-parchment-300 hover:bg-indigo-800/70 border border-indigo-400/30'
              }`}
              onClick={() => setActiveTab('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${
                activeTab === 'metrics'
                  ? 'bg-saffron-400 text-maya-darker shadow-lg shadow-saffron-400/30'
                  : 'bg-indigo-900/50 text-parchment-300 hover:bg-indigo-800/70 border border-indigo-400/30'
              }`}
              onClick={() => {
                setActiveTab('metrics');
                loadMetrics();
              }}
            >
              Metrics & Report
            </button>
            <button
              className={`px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${
                activeTab === 'clusters'
                  ? 'bg-saffron-400 text-maya-darker shadow-lg shadow-saffron-400/30'
                  : 'bg-indigo-900/50 text-parchment-300 hover:bg-indigo-800/70 border border-indigo-400/30'
              }`}
              onClick={() => setActiveTab('clusters')}
            >
              Galaxy Clusters
            </button>
            <button
              className={`px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${
                activeTab === 'query'
                  ? 'bg-saffron-400 text-maya-darker shadow-lg shadow-saffron-400/30'
                  : 'bg-indigo-900/50 text-parchment-300 hover:bg-indigo-800/70 border border-indigo-400/30'
              }`}
              onClick={() => setActiveTab('query')}
            >
              Query Tool
            </button>
          </div>
        </div>

        <div>
          {activeTab === 'dashboard' && <Dashboard metrics={metrics} />}
          {activeTab === 'metrics' && <MetricsView metrics={metrics} />}
          {activeTab === 'clusters' && <ClustersView />}
          {activeTab === 'query' && <QueryTool threshold={threshold} />}
        </div>
      </main>
    </div>
  );
}

export default App;
