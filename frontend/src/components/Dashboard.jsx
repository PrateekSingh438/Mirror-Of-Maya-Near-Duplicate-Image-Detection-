import { useEffect, useState } from 'react';
import { Database, TrendingUp, Image as ImageIcon, Zap } from 'lucide-react';
import { apiService } from '../services/api.js';
import './Dashboard.css';

const Dashboard = ({ metrics }) => {
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
      <div className="dashboard-empty">
        <div className="empty-content">
          <Zap size={64} className="empty-icon" />
          <h2>Welcome to Mirror of Maya</h2>
          <p>Click "Fresh Scan" in the sidebar to start detecting near-duplicate images</p>
          <p className="empty-subtitle">The Sudarshana Chakra will cut through compression and edits to reveal the true source</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Overview</h2>
        <p className="dashboard-subtitle">System Status & Quick Metrics</p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card primary">
          <div className="metric-icon">
            <Database size={24} />
          </div>
          <div className="metric-content">
            <h3>Total Storage</h3>
            <p className="metric-value">{localMetrics.storage.total_mb.toFixed(2)} MB</p>
          </div>
        </div>

        <div className="metric-card success">
          <div className="metric-icon">
            <TrendingUp size={24} />
          </div>
          <div className="metric-content">
            <h3>Potential Savings</h3>
            <p className="metric-value">{localMetrics.storage.wasted_mb.toFixed(2)} MB</p>
            <p className="metric-delta">+{localMetrics.storage.percent_saved.toFixed(1)}%</p>
          </div>
        </div>

        <div className="metric-card warning">
          <div className="metric-icon">
            <ImageIcon size={24} />
          </div>
          <div className="metric-content">
            <h3>Duplicate Pairs</h3>
            <p className="metric-value">{localMetrics.duplicates.total_pairs}</p>
            <p className="metric-delta">{localMetrics.duplicates.clusters} clusters</p>
          </div>
        </div>

        <div className="metric-card accent">
          <div className="metric-icon">
            <Zap size={24} />
          </div>
          <div className="metric-content">
            <h3>Model F1 Score</h3>
            <p className="metric-value">{localMetrics.model.f1_score.toFixed(4)}</p>
            <p className="metric-delta">
              {localMetrics.model.analysis.recovery_pct.toFixed(1)}% originals recovered
            </p>
          </div>
        </div>
      </div>

      <div className="quality-section">
        <h3>Quality Check</h3>
        <div className="quality-grid">
          <div className="quality-card recovery">
            <h4>Originals Recovered</h4>
            <p className="quality-value">{localMetrics.model.analysis.recovery}</p>
            <p className="quality-percent">
              {localMetrics.model.analysis.recovery_pct.toFixed(1)}% of total
            </p>
          </div>
          <div className="quality-card cross">
            <h4>Cross-Matches</h4>
            <p className="quality-value">{localMetrics.model.analysis.cross}</p>
            <p className="quality-percent">
              {localMetrics.model.analysis.cross_pct.toFixed(1)}% of total
            </p>
          </div>
        </div>
        {localMetrics.model.analysis.cross_pct > 50 ? (
          <div className="warning-banner">
            ⚠️ Warning: High cross-match rate. Consider adjusting threshold.
          </div>
        ) : (
          <div className="success-banner">
            ✓ System is anchoring to originals correctly.
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

