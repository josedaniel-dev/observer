import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from 'recharts';
import { useWebSocket } from '../hooks/useWebSocket';

interface SummaryData {
  total_traces: number;
  total_spans: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  error_count: number;
  error_rate: number;
  total_evaluations: number;
  avg_evaluation_score: number | null;
}

interface TimelinePoint {
  timestamp: string;
  count: number;
  cost_usd: number;
}

interface CostByModel {
  model: string;
  cost_usd: number;
  span_count: number;
}

function Overview() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [costByModel, setCostByModel] = useState<CostByModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [summaryRes, timelineRes, costRes] = await Promise.all([
        fetch('/api/v1/analytics/summary?hours=168'),
        fetch('/api/v1/analytics/timeline?hours=168&interval_minutes=360'),
        fetch('/api/v1/analytics/cost-by-model?hours=168'),
      ]);

      if (!summaryRes.ok || !timelineRes.ok || !costRes.ok) {
        throw new Error('Failed to fetch analytics data');
      }

      const [summaryData, timelineData, costData] = await Promise.all([
        summaryRes.json(),
        timelineRes.json(),
        costRes.json(),
      ]);

      setSummary(summaryData);
      setTimeline(timelineData);
      setCostByModel(costData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh on new trace or evaluation events
  useWebSocket({
    onMessage: useCallback((msg: { type: string }) => {
      if (msg.type === 'new_trace' || msg.type === 'new_evaluation') {
        fetchData();
      }
    }, [fetchData]),
  });

  if (loading) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-400">Loading...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">Error: {error}</p>
          <p className="text-gray-500 text-sm mt-2">Make sure the backend is running on port 8000</p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Dashboard Overview</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Traces"
          value={summary?.total_traces.toLocaleString() ?? '0'}
        />
        <StatCard
          title="Total Spans"
          value={summary?.total_spans.toLocaleString() ?? '0'}
        />
        <StatCard
          title="Total Cost"
          value={`$${(summary?.total_cost_usd ?? 0).toFixed(4)}`}
        />
        <StatCard
          title="Avg Latency"
          value={`${Math.round(summary?.avg_latency_ms ?? 0)}ms`}
        />
      </div>

      {/* Error Rate */}
      {summary && summary.error_count > 0 && (
        <div className="mt-4 bg-red-900/20 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">
            {summary.error_count} error{summary.error_count !== 1 ? 's' : ''}{' '}
            ({(summary.error_rate * 100).toFixed(1)}% error rate)
          </p>
        </div>
      )}

      {/* Charts */}
      <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Cost Over Time */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Cost Over Time</h2>
          {timeline.length > 0 ? (
            <ResponsiveContainer width="100%" height={256}>
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="timestamp"
                  stroke="#9CA3AF"
                  tickFormatter={(ts) => {
                    const d = new Date(ts);
                    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:00`;
                  }}
                />
                <YAxis stroke="#9CA3AF" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                  formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']}
                  labelFormatter={(ts) => new Date(ts).toLocaleString()}
                />
                <Line type="monotone" dataKey="cost_usd" stroke="#10B981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No data yet
            </div>
          )}
        </div>

        {/* Cost by Model */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Cost by Model</h2>
          {costByModel.length > 0 ? (
            <ResponsiveContainer width="100%" height={256}>
              <BarChart data={costByModel}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="model" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                  formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']}
                />
                <Bar dataKey="cost_usd" fill="#6366F1" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No data yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <dt className="text-sm font-medium text-gray-400 truncate">{title}</dt>
      <dd className="mt-1 text-3xl font-semibold text-white">{value}</dd>
    </div>
  );
}

export default Overview;
