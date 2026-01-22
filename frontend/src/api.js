// frontend/src/api.js
import axios from "axios";

const API_BASE = "http://localhost:8000";

export const api = {
  // Start scan
  startScan: async (datasetPath, threshold, model) => {
    return axios.post(`${API_BASE}/api/scan`, {
      dataset_path: datasetPath,
      threshold: threshold / 100,
      model: model,
    });
  },

  // Get scan status
  getStatus: async () => {
    return axios.get(`${API_BASE}/api/status`);
  },

  // Get metrics
  getMetrics: async () => {
    return axios.get(`${API_BASE}/api/metrics`);
  },

  // Get clusters
  getClusters: async (page = 0, perPage = 3) => {
    return axios.get(
      `${API_BASE}/api/clusters?page=${page}&per_page=${perPage}`,
    );
  },

  // Query image
  queryImage: async (file, threshold) => {
    const formData = new FormData();
    formData.append("file", file);
    return axios.post(
      `${API_BASE}/api/query?threshold=${threshold / 100}`,
      formData,
    );
  },

  // Delete files
  deleteFiles: async (filePaths) => {
    return axios.post(`${API_BASE}/api/delete`, {
      file_paths: filePaths,
    });
  },

  // Auto-select all
  autoSelectAll: async () => {
    return axios.get(`${API_BASE}/api/auto-select`);
  },

  // Get image URL
  getImageUrl: (path) => {
    return `${API_BASE}/api/image/${encodeURIComponent(path)}`;
  },
};
