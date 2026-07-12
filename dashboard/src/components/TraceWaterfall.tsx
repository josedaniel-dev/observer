import { useEffect, useState } from 'react';

interface Span {
  id: string;
  name: string;
  span_type: string;
  start_time: number;
  end_time?: number;
  status: string;
  tokens_input?: number;
  tokens_output?: number;
}

interface TraceWaterfallProps {
  traceId: string;
}

function TraceWaterfall({ traceId }: TraceWaterfallProps) {
  const [spans, setSpans] = useState<Span[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSpans();
  }, [traceId]);

  const fetchSpans = async () => {
    try {
      const response = await fetch(`/api/v1/traces/${traceId}/spans`);
      if (response.ok) {
        const data = await response.json();
        setSpans(data);
      }
    } catch (error) {
      console.error('Failed to fetch spans:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading spans...</div>
      </div>
    );
  }

  if (spans.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">No spans found</div>
      </div>
    );
  }

  const minStart = Math.min(...spans.map((s) => s.start_time));
  const maxEnd = Math.max(...spans.map((s) => s.end_time || s.start_time));
  const totalDuration = maxEnd - minStart;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-4">Trace Waterfall</h3>
      <div className="space-y-2">
        {spans.map((span) => {
          const startOffset = span.start_time - minStart;
          const duration = (span.end_time || span.start_time) - span.start_time;
          const leftPercent = (startOffset / totalDuration) * 100;
          const widthPercent = (duration / totalDuration) * 100;

          return (
            <div key={span.id} className="flex items-center">
              <div className="w-1/3 text-sm text-gray-300 truncate pr-4">
                {span.name}
              </div>
              <div className="w-2/3 relative h-6">
                <div
                  className={`absolute h-full rounded ${
                    span.status === 'ok' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  style={{
                    left: `${leftPercent}%`,
                    width: `${Math.max(widthPercent, 1)}%`,
                  }}
                />
              </div>
              <div className="w-24 text-right text-xs text-gray-400 pl-2">
                {duration.toFixed(0)}ms
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TraceWaterfall;
