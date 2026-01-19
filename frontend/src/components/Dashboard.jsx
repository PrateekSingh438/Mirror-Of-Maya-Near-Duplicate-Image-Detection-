import { useEffect, useState } from 'react';
import { Database, TrendingUp, Image as ImageIcon, Zap, Sparkles } from 'lucide-react';
import { apiService } from '../services/api.js';

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
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center max-w-md space-y-4">
          {/* Animated Chakra */}
          <div className="mx-auto w-24 h-24 rounded-full flex items-center justify-center animate-float">
            <div className="absolute w-24 h-24 rounded-full border-4 border-saffron-400 animate-pulse-chakra"></div>
            <div className="absolute w-16 h-16 rounded-full border-2 border-gold opacity-50 animate-pulse-inner"></div>
            <Zap className="w-10 h-10 text-saffron-400 animate-spin-chakra" />
          </div>
          
          <h2 className="text-3xl font-bold bg-gradient-to-r from-saffron-400 to-parchment-400 bg-clip-text text-transparent">
            Welcome to Mirror of Maya
          </h2>
          <p className="text-parchment-600">
            Invoke the Sudarshana Chakra in the sidebar to begin discernment
          </p>
          <p className="text-parchment-700 italic text-sm">
            The Chakra will cut through compression and edits to reveal the true source soul of each image
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-3xl font-bold text-parchment">Sacred Overview</h2>
        <p className="text-parchment-600 italic">System Consciousness & Vital Measures</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Collection */}
        <div className="metric-card group">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-gradient-to-br from-indigo-600/30 to-indigo-700/20 group-hover:from-saffron-500/30 group-hover:to-saffron-600/20 transition-all duration-300">
              <Database className="w-6 h-6 text-indigo-300 group-hover:text-saffron-300" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-parchment-700 tracking-wide">Total Collection</p>
              <p className="text-2xl font-bold text-parchment mt-1">{localMetrics.storage.total_mb.toFixed(2)}</p>
              <p className="text-xs text-parchment-700 mt-1">MB</p>
            </div>
          </div>
        </div>

        {/* Illusory Forms */}
        <div className="metric-card group">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-gradient-to-br from-green-600/30 to-green-700/20 group-hover:from-saffron-500/30 group-hover:to-saffron-600/20 transition-all duration-300">
              <TrendingUp className="w-6 h-6 text-green-300 group-hover:text-saffron-300" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-parchment-700 tracking-wide">Illusory Forms</p>
              <p className="text-2xl font-bold text-parchment mt-1">{localMetrics.storage.wasted_mb.toFixed(2)}</p>
              <p className="text-xs text-parchment-700 mt-1">+{localMetrics.storage.percent_saved.toFixed(1)}% liberation</p>
            </div>
          </div>
        </div>

        {/* Maya Detected */}
        <div className="metric-card group">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-gradient-to-br from-amber-600/30 to-amber-700/20 group-hover:from-saffron-500/30 group-hover:to-saffron-600/20 transition-all duration-300">
              <ImageIcon className="w-6 h-6 text-amber-300 group-hover:text-saffron-300" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-parchment-700 tracking-wide">Maya Detected</p>
              <p className="text-2xl font-bold text-parchment mt-1">{localMetrics.duplicates.total_pairs}</p>
              <p className="text-xs text-parchment-700 mt-1">{localMetrics.duplicates.clusters} source souls</p>
            </div>
          </div>
        </div>

        {/* Chakra Precision */}
        <div className="metric-card group">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-gradient-to-br from-saffron-600/30 to-gold/20 group-hover:from-saffron-500/30 group-hover:to-saffron-600/20 transition-all duration-300 animate-glow">
              <Zap className="w-6 h-6 text-saffron-300 group-hover:text-saffron-200" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-parchment-700 tracking-wide">Chakra Precision</p>
              <p className="text-2xl font-bold text-parchment mt-1">{localMetrics.model.f1_score.toFixed(4)}</p>
              <p className="text-xs text-parchment-700 mt-1">{localMetrics.model.analysis.recovery_pct.toFixed(1)}% recovered</p>
            </div>
          </div>
        </div>
      </div>

      {/* Dharmic Analysis */}
      <div className="space-y-4">
        <h3 className="text-xl font-bold text-parchment">Dharmic Analysis</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Originals Recovered */}
          <div className="card border-l-4 border-l-green-500">
            <h4 className="text-xs font-semibold uppercase text-parchment-700 tracking-wide mb-2">Originals Recovered</h4>
            <p className="text-3xl font-bold text-parchment">{localMetrics.model.analysis.recovery}</p>
            <p className="text-sm text-parchment-700 mt-2">{localMetrics.model.analysis.recovery_pct.toFixed(1)}% of total</p>
          </div>

          {/* Cross-Matches */}
          <div className="card border-l-4 border-l-amber-500">
            <h4 className="text-xs font-semibold uppercase text-parchment-700 tracking-wide mb-2">Cross-Matches</h4>
            <p className="text-3xl font-bold text-parchment">{localMetrics.model.analysis.cross}</p>
            <p className="text-sm text-parchment-700 mt-2">{localMetrics.model.analysis.cross_pct.toFixed(1)}% of total</p>
          </div>
        </div>

        {/* Alert Banner */}
        {localMetrics.model.analysis.cross_pct > 50 ? (
          <div className="p-4 rounded-lg border border-amber-600/40 bg-amber-900/20 text-amber-300">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 animate-spin" />
              <span>⚠️ High cross-match rate detected. Consider adjusting threshold for better discernment.</span>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-lg border border-green-600/40 bg-green-900/20 text-green-300">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              <span>✓ The Chakra is anchoring to originals correctly!</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

