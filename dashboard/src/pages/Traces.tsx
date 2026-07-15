import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';

interface Trace {
  id: string;
  name: string;
  session_id: string | null;
  start_time: string;
  end_time: string | null;
  status: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

function Traces() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const limit = 20;

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchTraces = useCallback(async (offset: number) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      if (statusFilter) params.set('status', statusFilter);
      if (debouncedSearch) params.set('search', debouncedSearch);

      const response = await fetch(`/api/v1/traces?${params}`);
      if (!response.ok) throw new Error('Failed to fetch traces');

      const data = await response.json();
      setTraces(data.traces);
      setTotal(data.total);
      setHasMore(offset + data.traces.length < data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, debouncedSearch]);

  // Reset to page 0 when filters change, then fetch
  useEffect(() => {
    setPage(0);
    fetchTraces(0);
  }, [fetchTraces]);

  // Fetch when page changes (but not on initial mount or filter change)
  const prevPageRef = useRef(page);
  useEffect(() => {
    if (prevPageRef.current !== page) {
      prevPageRef.current = page;
      fetchTraces(page * limit);
    }
  }, [page, fetchTraces]);

  const formatDuration = (start: string, end: string | null) => {
    if (!end) return '-';
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTimeAgo = (dateStr: string) => {
    const now = new Date();
    const date = new Date(dateStr);
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Traces</h1>

      {/* Filters */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="Search traces..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-gray-700 text-white px-4 py-2 rounded-md flex-1 min-w-[200px]"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-700 text-white px-4 py-2 rounded-md"
          >
            <option value="">All Statuses</option>
            <option value="ok">OK</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Traces Table */}
      {error ? (
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">Error: {error}</p>
          <p className="text-gray-500 text-sm mt-2">Make sure the backend is running on port 8000</p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-750">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-400">
                    Loading...
                  </td>
                </tr>
              ) : traces.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-400">
                    No traces found
                  </td>
                </tr>
              ) : (
                traces.map((trace) => (
                  <tr key={trace.id} className="hover:bg-gray-750">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      <Link
                        to={`/traces/${trace.id}`}
                        className="hover:text-blue-400"
                      >
                        {trace.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={trace.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {formatDuration(trace.start_time, trace.end_time)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {formatTimeAgo(trace.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between">
        <div className="text-sm text-gray-400">
          Page {page + 1} of {Math.ceil(total / limit)} ({total} traces total)
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore}
            className="px-3 py-1 bg-gray-700 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'ok') {
    return (
      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
        OK
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
        ERROR
      </span>
    );
  }
  return (
    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
      {status.toUpperCase()}
    </span>
  );
}

export default Traces;
