import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { apiService } from '../services/api.js';

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
      <div className="p-6 flex items-center justify-center">
        <p className="text-parchment-300 text-lg">No sacred insights available. Begin discernment with the Chakra first.</p>
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
    <div className="p-6">
      <div className="mb-8">
        <h2 className="text-4xl font-bold text-gradient-saffron mb-3">Chakra Enlightenment & Insights</h2>
        <p className="text-parchment-300">Sacred analysis of the Chakra's discernment performance</p>
      </div>

      <div className="space-y-8">
        <div className="card">
          <h3 className="text-2xl font-bold text-saffron-400 mb-6">Form & Substance Analysis</h3>
          <div className="bg-maya-darker rounded-lg p-4 mb-6">
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-gradient-to-br from-indigo-900/30 to-maya-darker border border-indigo-400/30 rounded-lg">
              <span className="text-parchment-400 text-sm">Sacred Archive:</span>
              <p className="text-2xl font-bold text-indigo-300">{localMetrics.storage.total_mb.toFixed(2)} MB</p>
            </div>
            <div className="p-4 bg-gradient-to-br from-orange-900/30 to-maya-darker border border-orange-400/30 rounded-lg">
              <span className="text-parchment-400 text-sm">Illusory Space:</span>
              <p className="text-2xl font-bold text-orange-300">{localMetrics.storage.wasted_mb.toFixed(2)} MB</p>
            </div>
            <div className="p-4 bg-gradient-to-br from-saffron-900/30 to-maya-darker border border-saffron-400/30 rounded-lg">
              <span className="text-parchment-400 text-sm">Liberated Form:</span>
              <p className="text-2xl font-bold text-saffron-300">{localMetrics.storage.optimized_mb.toFixed(2)} MB</p>
            </div>
            <div className="p-4 bg-gradient-to-br from-gold/30 to-maya-darker border border-gold/50 rounded-lg shadow-lg shadow-gold/10">
              <span className="text-parchment-400 text-sm">Truth Revealed:</span>
              <p className="text-2xl font-bold text-gold">{localMetrics.storage.percent_saved.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-2xl font-bold text-saffron-400 mb-6">Manifestation Patterns</h3>
          <div className="bg-maya-darker rounded-lg p-4">
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

        <div className="card">
          <h3 className="text-2xl font-bold text-saffron-400 mb-6">Chakra Potency</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-6 bg-gradient-to-br from-green-900/30 to-maya-darker border border-green-400/30 rounded-lg hover:shadow-lg hover:shadow-green-400/10 transition-all duration-300">
              <h4 className="text-parchment-300 font-semibold mb-2">Discernment Power</h4>
              <p className="text-3xl font-bold text-green-300">{localMetrics.model.f1_score.toFixed(4)}</p>
              <p className="text-parchment-400 text-sm mt-2">
                {localMetrics.model.f1_score >= 0.8
                  ? 'Exceptional clarity'
                  : localMetrics.model.f1_score >= 0.6
                  ? 'Substantial insight'
                  : 'Needs refinement'}
              </p>
            </div>
            <div className="p-6 bg-gradient-to-br from-blue-900/30 to-maya-darker border border-blue-400/30 rounded-lg hover:shadow-lg hover:shadow-blue-400/10 transition-all duration-300">
              <h4 className="text-parchment-300 font-semibold mb-2">Forms Witnessed</h4>
              <p className="text-3xl font-bold text-blue-300">{localMetrics.index.total_images}</p>
            </div>
            <div className="p-6 bg-gradient-to-br from-purple-900/30 to-maya-darker border border-purple-400/30 rounded-lg hover:shadow-lg hover:shadow-purple-400/10 transition-all duration-300">
              <h4 className="text-parchment-300 font-semibold mb-2">Maya Pairs Detected</h4>
              <p className="text-3xl font-bold text-purple-300">{localMetrics.duplicates.total_pairs}</p>
            </div>
            <div className="p-6 bg-gradient-to-br from-cyan-900/30 to-maya-darker border border-cyan-400/30 rounded-lg hover:shadow-lg hover:shadow-cyan-400/10 transition-all duration-300">
              <h4 className="text-parchment-300 font-semibold mb-2">Source Souls Found</h4>
              <p className="text-3xl font-bold text-cyan-300">{localMetrics.duplicates.clusters}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsView;

