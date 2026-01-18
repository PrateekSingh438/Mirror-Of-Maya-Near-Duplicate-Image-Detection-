import { useState, useEffect } from 'react';
import Header from './components/Header.jsx';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './components/Dashboard.jsx';
import ClustersView from './components/ClustersView.jsx';
import QueryTool from './components/QueryTool.jsx';
import MetricsView from './components/MetricsView.jsx';
import { apiService } from './services/api.js';
import './App.css';

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
    <div className="app">
      <Header />
      <div className="app-container">
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
        <main className="main-content">
          <div className="tab-container">
            <button
              className={`tab-button ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`tab-button ${activeTab === 'metrics' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('metrics');
                loadMetrics();
              }}
            >
              Metrics & Report
            </button>
            <button
              className={`tab-button ${activeTab === 'clusters' ? 'active' : ''}`}
              onClick={() => setActiveTab('clusters')}
            >
              Galaxy Clusters
            </button>
            <button
              className={`tab-button ${activeTab === 'query' ? 'active' : ''}`}
              onClick={() => setActiveTab('query')}
            >
              Query Tool
            </button>
          </div>

          <div className="content-area">
            {activeTab === 'dashboard' && <Dashboard metrics={metrics} />}
            {activeTab === 'metrics' && <MetricsView metrics={metrics} />}
            {activeTab === 'clusters' && <ClustersView />}
            {activeTab === 'query' && <QueryTool threshold={threshold} />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
