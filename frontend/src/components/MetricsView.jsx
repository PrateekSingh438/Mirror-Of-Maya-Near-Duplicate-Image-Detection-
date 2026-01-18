import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { apiService } from '../services/api.js';
import './MetricsView.css';

const MetricsView = ({ metrics }) => {
  const [localMetrics, setLocalMetrics] = useState(metrics);

  useEffect(() => {
    if (!metrics) {
      loadMetrics();
    } else {
      setLocalMetrics(metrics);
    }
  }, [metrics]);

  const loadMetrics = async () => {
    try {
      const data = await apiService.getMetrics();
      if (data.status !== 'no_data') {
        setLocalMetrics(data);
      }
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  if (!localMetrics || localMetrics.status === 'no_data') {
    return (
      <div className="metrics-empty">
        <p>No metrics available. Please scan a dataset first.</p>
      </div>
    );
  }

  const storageData = [
    { name: 'Used', value: localMetrics.storage.total_mb - localMetrics.storage.wasted_mb, color: '#8B4E9E' },
    { name: 'Wasted', value: localMetrics.storage.wasted_mb, color: '#FF9800' },
  ];

  const analysisData = [
    { name: 'Originals Recovered', value: localMetrics.model.analysis.recovery, color: '#4CAF50' },
    { name: 'Cross-Matches', value: localMetrics.model.analysis.cross, color: '#FF9800' },
  ];

  return (
    <div className="metrics-view">
      <div className="metrics-header">
        <h2>Detailed Metrics & Report</h2>
        <p className="metrics-subtitle">Comprehensive analysis of duplicate detection performance</p>
      </div>

      <div className="metrics-content">
        <div className="metrics-section">
          <h3>Storage Analysis</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={storageData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {storageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => `${value.toFixed(2)} MB`}
                  contentStyle={{
                    backgroundColor: 'rgba(26, 13, 31, 0.95)',
                    border: '1px solid rgba(139, 78, 158, 0.3)',
                    borderRadius: '8px',
                    color: '#F5E6F8',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="storage-details">
            <div className="detail-item">
              <span className="detail-label">Total Storage:</span>
              <span className="detail-value">{localMetrics.storage.total_mb.toFixed(2)} MB</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Wasted Space:</span>
              <span className="detail-value">{localMetrics.storage.wasted_mb.toFixed(2)} MB</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Optimized Size:</span>
              <span className="detail-value">{localMetrics.storage.optimized_mb.toFixed(2)} MB</span>
            </div>
            <div className="detail-item highlight">
              <span className="detail-label">Savings:</span>
              <span className="detail-value">{localMetrics.storage.percent_saved.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        <div className="metrics-section">
          <h3>Match Type Analysis</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analysisData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 78, 158, 0.2)" />
                <XAxis dataKey="name" stroke="#C9A6D4" />
                <YAxis stroke="#C9A6D4" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(26, 13, 31, 0.95)',
                    border: '1px solid rgba(139, 78, 158, 0.3)',
                    borderRadius: '8px',
                    color: '#F5E6F8',
                  }}
                />
                <Bar dataKey="value" fill="#8B4E9E" radius={[8, 8, 0, 0]}>
                  {analysisData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="metrics-section">
          <h3>Performance Metrics</h3>
          <div className="performance-grid">
            <div className="performance-card">
              <h4>F1 Score</h4>
              <p className="performance-value">{localMetrics.model.f1_score.toFixed(4)}</p>
              <p className="performance-description">
                {localMetrics.model.f1_score >= 0.8
                  ? 'Excellent performance'
                  : localMetrics.model.f1_score >= 0.6
                  ? 'Good performance'
                  : 'Needs improvement'}
              </p>
            </div>
            <div className="performance-card">
              <h4>Total Images Indexed</h4>
              <p className="performance-value">{localMetrics.index.total_images}</p>
            </div>
            <div className="performance-card">
              <h4>Duplicate Pairs</h4>
              <p className="performance-value">{localMetrics.duplicates.total_pairs}</p>
            </div>
            <div className="performance-card">
              <h4>Clusters Found</h4>
              <p className="performance-value">{localMetrics.duplicates.clusters}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsView;

