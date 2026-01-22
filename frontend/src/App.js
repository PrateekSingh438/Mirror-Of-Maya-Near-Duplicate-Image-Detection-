// frontend/src/App.js
import React, { useState, useEffect } from "react";
import {
  Upload,
  Search,
  Eye,
  Trash2,
  Loader,
  CheckCircle,
  XCircle,
  TrendingUp,
  Database,
  Disc,
  Flame,
  Shield,
} from "lucide-react";
import { api } from "./api";

const MirrorOfMaya = () => {
  const [activeTab, setActiveTab] = useState("scan");
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [metrics, setMetrics] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [deletionQueue, setDeletionQueue] = useState(new Set());
  const [selectedModel, setSelectedModel] = useState("Small");
  const [threshold, setThreshold] = useState(85);
  const [datasetPath, setDatasetPath] = useState("./dataset_copydays");

  const handleScan = async () => {
    try {
      setScanning(true);
      setProgress(0);

      await api.startScan(datasetPath, threshold, selectedModel);

      const interval = setInterval(async () => {
        const { data } = await api.getStatus();
        setProgress(data.progress);

        if (data.status === "complete") {
          clearInterval(interval);
          setScanning(false);
          await loadMetrics();
          await loadClusters(0);
        } else if (data.status === "error") {
          clearInterval(interval);
          setScanning(false);
          alert("Scan failed: " + data.message);
        }
      }, 1000);
    } catch (error) {
      setScanning(false);
      alert("Error starting scan: " + error.message);
    }
  };

  const loadMetrics = async () => {
    try {
      const { data } = await api.getMetrics();
      setMetrics(data);
    } catch (error) {
      console.error("Error loading metrics:", error);
    }
  };

  const loadClusters = async (page) => {
    try {
      const { data } = await api.getClusters(page, 3);
      setClusters(data.clusters);
      setTotalPages(data.totalPages);
      setCurrentPage(page);
    } catch (error) {
      console.error("Error loading clusters:", error);
    }
  };

  const toggleDeletion = (path) => {
    const newQueue = new Set(deletionQueue);
    if (newQueue.has(path)) {
      newQueue.delete(path);
    } else {
      newQueue.add(path);
    }
    setDeletionQueue(newQueue);
  };

  const autoSelectAll = async () => {
    try {
      const { data } = await api.autoSelectAll();
      setDeletionQueue(new Set(data.selectedFiles));
    } catch (error) {
      alert("Error auto-selecting: " + error.message);
    }
  };

  const executeDeletion = async () => {
    if (!window.confirm(`Delete ${deletionQueue.size} files?`)) return;

    try {
      const { data } = await api.deleteFiles(Array.from(deletionQueue));
      alert(`Deleted ${data.deleted} files successfully!`);
      setDeletionQueue(new Set());
      await loadClusters(currentPage);
      await loadMetrics();
    } catch (error) {
      alert("Error deleting files: " + error.message);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const { data } = await api.queryImage(file, threshold);
      console.log("Query results:", data);
    } catch (error) {
      alert("Error querying image: " + error.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-red-50 relative overflow-hidden">
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-red-50 relative overflow-hidden">
        {/* Animated Background Mandalas */}
        <div className="fixed inset-0 opacity-10 pointer-events-none">
          <div
            className="absolute top-20 left-20 w-64 h-64 border-4 border-orange-600 rounded-full"
            style={{
              background:
                "radial-gradient(circle, transparent 30%, rgba(234, 88, 12, 0.1) 31%, rgba(234, 88, 12, 0.1) 35%, transparent 36%)",
              animation: "spin 30s linear infinite",
            }}
          ></div>
          <div
            className="absolute bottom-20 right-20 w-96 h-96 border-4 border-red-600 rounded-full"
            style={{
              background:
                "radial-gradient(circle, transparent 30%, rgba(220, 38, 38, 0.1) 31%, rgba(220, 38, 38, 0.1) 35%, transparent 36%)",
              animation: "spin 40s linear infinite reverse",
            }}
          ></div>
        </div>

        {/* Rotating Sudarshana Chakra */}
        <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-5 z-0">
          <svg
            width="600"
            height="600"
            viewBox="0 0 200 200"
            className="animate-spin-slow"
          >
            <defs>
              <radialGradient id="chakraGrad" cx="50%" cy="50%" r="50%">
                <stop
                  offset="0%"
                  style={{ stopColor: "#dc2626", stopOpacity: 1 }}
                />
                <stop
                  offset="100%"
                  style={{ stopColor: "#ea580c", stopOpacity: 0.5 }}
                />
              </radialGradient>
            </defs>
            <circle
              cx="100"
              cy="100"
              r="80"
              fill="none"
              stroke="url(#chakraGrad)"
              strokeWidth="2"
            />
            <circle
              cx="100"
              cy="100"
              r="60"
              fill="none"
              stroke="url(#chakraGrad)"
              strokeWidth="2"
            />
            <circle
              cx="100"
              cy="100"
              r="40"
              fill="none"
              stroke="url(#chakraGrad)"
              strokeWidth="2"
            />
            <circle cx="100" cy="100" r="20" fill="url(#chakraGrad)" />
            {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
              <g key={i} transform={`rotate(${angle} 100 100)`}>
                <path
                  d="M 100 20 L 110 40 L 100 35 L 90 40 Z"
                  fill="url(#chakraGrad)"
                />
                <line
                  x1="100"
                  y1="40"
                  x2="100"
                  y2="80"
                  stroke="url(#chakraGrad)"
                  strokeWidth="2"
                />
              </g>
            ))}
          </svg>
        </div>

        <style>{`
          @keyframes spin-slow { from { transform: rotate(0deg);} to { transform: rotate(360deg);} }
          .animate-spin-slow { animation: spin-slow 60s linear infinite; }
          @keyframes pulse-glow { 0%,100%{box-shadow:0 0 20px rgba(234,88,12,.5);} 50%{box-shadow:0 0 40px rgba(234,88,12,.8);} }
        `}</style>

        {/* Header */}
        <header className="relative bg-gradient-to-r from-red-900 via-orange-800 to-amber-900 text-white shadow-2xl border-b-4 border-amber-500">
          <div className="container mx-auto px-6 py-6 relative">
            <div className="flex items-center justify-between">
              <h1
                className="text-5xl font-bold"
                style={{ fontFamily: "Georgia, serif" }}
              >
                Mirror of Maya
              </h1>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="px-4 py-2 bg-amber-900/80 border-2 border-amber-600 rounded-lg text-white"
              >
                <option>Small</option>
                <option>Base</option>
                <option>Large</option>
              </select>
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className="relative bg-white/80 backdrop-blur-sm shadow-lg border-b-2 border-orange-200">
          <div className="container mx-auto px-6">
            <div className="flex space-x-1">
              {[
                { id: "scan", label: "Scan & Analytics", icon: Search },
                { id: "clusters", label: "Duplicate Clusters", icon: Eye },
                { id: "query", label: "Image Search", icon: Upload },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-6 py-4 border-b-4 ${activeTab === tab.id ? "border-orange-600 bg-orange-50 text-orange-900 font-bold" : "border-transparent hover:bg-amber-50"}`}
                >
                  {" "}
                  <tab.icon className="w-5 h-5" /> <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="container mx-auto px-6 py-8 relative z-10">
          {activeTab === "scan" && (
            <button
              onClick={handleScan}
              disabled={scanning}
              className="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white py-4 rounded-xl"
            >
              {scanning ? `Scanning... ${progress}%` : "Start Scan"}
            </button>
          )}

          {activeTab === "clusters" && (
            <div>
              <button onClick={autoSelectAll}>Auto-Select All</button>
              <button onClick={executeDeletion}>Delete Selected</button>
            </div>
          )}

          {activeTab === "query" && (
            <input type="file" onChange={handleFileUpload} />
          )}
        </main>

        {/* Footer */}
        <footer className="relative bg-gradient-to-r from-red-900 via-orange-800 to-amber-900 text-amber-200 py-6 mt-12 border-t-4 border-amber-500">
          <div className="container mx-auto px-6 text-center">
            <p className="text-sm font-semibold flex items-center justify-center space-x-2">
              <Shield className="w-4 h-4" />
              <span>
                Truth Alone Triumphs • Powered by DINOv2 Vision Transformer
              </span>
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default MirrorOfMaya;
