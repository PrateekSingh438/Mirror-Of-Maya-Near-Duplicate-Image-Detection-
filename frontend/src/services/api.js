import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  health: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  scan: async (params) => {
    const response = await api.post('/scan', params);
    return response.data;
  },

  getDuplicates: async (page = 0, perPage = 50) => {
    const response = await api.get('/duplicates', {
      params: { page, per_page: perPage },
    });
    return response.data;
  },

  getClusters: async (page = 0, perPage = 5) => {
    const response = await api.get('/clusters', {
      params: { page, per_page: perPage },
    });
    return response.data;
  },

  search: async (file, threshold) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/search', formData, {
      params: { threshold },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getMetrics: async () => {
    const response = await api.get('/metrics');
    return response.data;
  },

  deleteFiles: async (filePaths) => {
    const response = await api.post('/delete', filePaths);
    return response.data;
  },

  getModels: async () => {
    const response = await api.get('/models');
    return response.data;
  },
};