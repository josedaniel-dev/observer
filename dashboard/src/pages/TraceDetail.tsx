import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import TraceWaterfall from '../components/TraceWaterfall';

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

interface Span {
  id: string;
  trace_id: string;
  parent_id: string | null;
  name: string;
  span_type: string;
  start_time: string;
  end_time: string | null;
  status: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  tokens_input: number | null;
  tokens_output: number | null;
  cost_usd: number | null;
  metadata: Record<string, unknown> | null;
  attributes: Record<string, unknown> | null;
}

function TraceDetail() {
  const { traceId } = useParams<{ traceId: string }>();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [spans, setSpans] = useState<Span[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!traceId) return;

      try {
        const [traceRes, spansRes] = await Promise.all([
          fetch(`/api/v1/traces/${traceId}`),
          fetch(`/api/v1/traces/${traceId}/spans`),
        ]);

        if (!traceRes.ok || !spansRes.ok) {
          throw new Error('Failed to fetch trace data');
        }

        const [traceData, spansData] = await Promise.all([
          traceRes.json(),
          spansRes.json(),
        ]);

        setTrace(traceData);
        setSpans(spansData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [traceId]);

  if (loading) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-400">Loading...</div>
        </div>
      </div>
    );
  }

  if (error || !trace) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">Error: {error || 'Trace not found'}</p>
          <Link to="/traces" className="text-blue-400 hover:text-blue-300 text-sm mt-2 inline-block">
            Back to traces
          </Link>
        </div>
      </div>
    );
  }

  const formatDuration = (start: string, end: string | null) => {
    if (!end) return '-';
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      {/* Header */}
      <div className="mb-6">
        <Link to="/traces" className="text-blue-400 hover:text-blue-300 text-sm">
          &larr; Back to traces
        </Link>
        <h1 className="text-2xl font-bold mt-2">{trace.name}</h1>
      </div>

      {/* Trace Info */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <InfoCard label="Status" value={trace.status} />
        <InfoCard label="Duration" value={formatDuration(trace.start_time, trace.end_time)} />
        <InfoCard label="Spans" value={spans.length.toString()} />
        <InfoCard label="Created" value={new Date(trace.created_at).toLocaleString()} />
      </div>

      {/* Waterfall */}
      <div className="mb-6">
        <TraceWaterfall traceId={traceId!} spans={spans} />
      </div>

      {/* Spans Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700">
          <h2 className="text-lg font-semibold">Spans</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Type
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Tokens
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Cost
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {spans.map((span) => (
              <tr
                key={span.id}
                className={`hover:bg-gray-750 cursor-pointer ${
                  selectedSpan?.id === span.id ? 'bg-gray-700' : ''
                }`}
                onClick={() => setSelectedSpan(selectedSpan?.id === span.id ? null : span)}
              >
                <td className="px-4 py-3 text-sm text-white">{span.name}</td>
                <td className="px-4 py-3 text-sm text-gray-300">{span.span_type}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={span.status} />
                </td>
                <td className="px-4 py-3 text-sm text-gray-300">
                  {formatDuration(span.start_time, span.end_time)}
                </td>
                <td className="px-4 py-3 text-sm text-gray-300">
                  {span.tokens_input != null && span.tokens_output != null
                    ? `${span.tokens_input} → ${span.tokens_output}`
                    : '-'}
                </td>
                <td className="px-4 py-3 text-sm text-gray-300">
                  {span.cost_usd != null ? `$${span.cost_usd.toFixed(6)}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Span Detail Panel */}
      {selectedSpan && (
        <div className="mt-6 bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-4">Span Detail: {selectedSpan.name}</h3>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-2">Input</h4>
              <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 overflow-x-auto">
                {selectedSpan.input ? JSON.stringify(selectedSpan.input, null, 2) : 'null'}
              </pre>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-2">Output</h4>
              <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 overflow-x-auto">
                {selectedSpan.output ? JSON.stringify(selectedSpan.output, null, 2) : 'null'}
              </pre>
            </div>
          </div>
          {selectedSpan.attributes && Object.keys(selectedSpan.attributes).length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Attributes</h4>
              <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 overflow-x-auto">
                {JSON.stringify(selectedSpan.attributes, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <dt className="text-sm font-medium text-gray-400">{label}</dt>
      <dd className="mt-1 text-xl font-semibold text-white">{value}</dd>
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

export default TraceDetail;
