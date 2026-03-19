import React, { useState, useEffect } from 'react';
import { api } from './services/api';

function Dashboard() {
  const [queries, setQueries] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedQuery, setSelectedQuery] = useState('');
  const [results, setResults] = useState({ without: null, with: null });
  const [loading, setLoading] = useState({ without: false, with: false });
  const [indexExists, setIndexExists] = useState(false);

  useEffect(() => {
    loadQueries();
    loadStats();
    checkIndexStatus();
  }, []);

  const loadQueries = async () => {
    const data = await api.getQueries();
    setQueries(data.queries);
    if (data.queries.length > 0) {
      setSelectedQuery(data.queries[0].id);
    }
  };

  const loadStats = async () => {
    const data = await api.getStats();
    setStats(data);
  };

  const checkIndexStatus = async () => {
    const data = await api.getIndexStatus();
    setIndexExists(data.exists);
  };

  const runBenchmark = async (useIndex) => {
    const key = useIndex ? 'with' : 'without';
    setLoading(prev => ({ ...prev, [key]: true }));

    try {
      const data = await api.runBenchmark(selectedQuery, useIndex);
      setResults(prev => ({ ...prev, [key]: data }));
      // Use index_exists from the response directly — mirrors what the backend
      // did (created or dropped the index before running the query).
      // Falls back to checkIndexStatus() for real backend compatibility.
      if (typeof data.index_exists === 'boolean') {
        setIndexExists(data.index_exists);
      } else {
        await checkIndexStatus();
      }
    } catch (err) {
      console.error('Benchmark failed:', err);
      alert('Benchmark failed: ' + err.message);
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const toggleIndex = async (create) => {
    try {
      if (create) {
        await api.createIndex();
      } else {
        await api.dropIndex();
      }
      await checkIndexStatus();
    } catch (err) {
      console.error('Index operation failed:', err);
      alert('Index operation failed: ' + err.message);
    }
  };

  const speedup = results.without && results.with 
    ? (results.without.execution_time_ms / results.with.execution_time_ms).toFixed(1)
    : null;

  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Spatial Query Performance Dashboard
          </h1>
          <p className="text-gray-600">
            Benchmark PostGIS spatial queries with/without GiST indexes
          </p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Total Features</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.total_rows.toLocaleString()}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Table Size</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.table_size}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Index Status</div>
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${indexExists ? 'bg-green-500' : 'bg-red-500'}`} />
                <div className="text-2xl font-bold text-gray-900">
                  {indexExists ? 'Active' : 'None'}
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Index Size</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.index_size}
              </div>
            </div>
          </div>
        )}

        {/* Query Selector */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Query
          </label>
          <select 
            value={selectedQuery}
            onChange={(e) => setSelectedQuery(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {queries.map(q => (
              <option key={q.id} value={q.id}>
                {q.name} - {q.use_case}
              </option>
            ))}
          </select>
        </div>

        {/* Benchmark Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Without Index */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Without Index
              </h3>
              <button
                onClick={() => runBenchmark(false)}
                disabled={loading.without}
                className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading.without ? 'Running...' : 'Run Benchmark'}
              </button>
            </div>

            {results.without && (
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Execution Time</span>
                  <span className="font-bold text-red-600">
                    {results.without.execution_time_ms.toFixed(2)} ms
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Planning Time</span>
                  <span className="font-semibold">
                    {results.without.planning_time_ms.toFixed(2)} ms
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Rows Returned</span>
                  <span className="font-semibold">
                    {results.without.row_count.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-gray-600">Scan Type</span>
                  <span className="font-semibold text-sm">
                    {results.without.query_plan.Plan['Node Type']}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* With Index */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                With Index
              </h3>
              <button
                onClick={() => runBenchmark(true)}
                disabled={loading.with}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading.with ? 'Running...' : 'Run Benchmark'}
              </button>
            </div>

            {results.with && (
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Execution Time</span>
                  <span className="font-bold text-green-600">
                    {results.with.execution_time_ms.toFixed(2)} ms
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Planning Time</span>
                  <span className="font-semibold">
                    {results.with.planning_time_ms.toFixed(2)} ms
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">Rows Returned</span>
                  <span className="font-semibold">
                    {results.with.row_count.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-gray-600">Scan Type</span>
                  <span className="font-semibold text-sm">
                    {results.with.query_plan.Plan['Node Type']}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Speedup Card */}
        {speedup && (
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg p-8 text-white text-center mb-8">
            <div className="text-6xl font-bold mb-2">{speedup}x</div>
            <div className="text-xl">Faster with Index</div>
            <div className="text-sm mt-2 opacity-90">
              {results.without.execution_time_ms.toFixed(2)}ms → {results.with.execution_time_ms.toFixed(2)}ms
            </div>
          </div>
        )}

        {/* Index Management */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Index Management
          </h3>
          <div className="flex gap-4">
            <button
              onClick={() => toggleIndex(true)}
              disabled={indexExists}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Create Index
            </button>
            <button
              onClick={() => toggleIndex(false)}
              disabled={!indexExists}
              className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Drop Index
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;