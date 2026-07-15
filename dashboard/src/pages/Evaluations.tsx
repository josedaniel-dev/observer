import { useState, useEffect } from 'react';

interface Evaluation {
  id: string;
  trace_id: string;
  span_id: string | null;
  evaluator_type: string;
  score: number;
  criteria: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  created_at: string;
}

function Evaluations() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvaluations = async () => {
      try {
        const response = await fetch('/api/v1/evaluations?limit=100');
        if (!response.ok) throw new Error('Failed to fetch evaluations');
        const data = await response.json();
        setEvaluations(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchEvaluations();
  }, []);

  // Compute summary stats
  const llmJudgeEvals = evaluations.filter((e) => e.evaluator_type === 'llm_judge');
  const ruleBasedEvals = evaluations.filter((e) => e.evaluator_type === 'rule_based');
  const humanEvals = evaluations.filter((e) => e.evaluator_type === 'human');

  const avgScore = (evals: Evaluation[]) => {
    if (evals.length === 0) return 0;
    return evals.reduce((sum, e) => sum + e.score, 0) / evals.length;
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

  const getEvaluatorBadge = (type: string) => {
    switch (type) {
      case 'llm_judge':
        return (
          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
            LLM Judge
          </span>
        );
      case 'rule_based':
        return (
          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
            Rule-Based
          </span>
        );
      case 'human':
        return (
          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
            Human
          </span>
        );
      default:
        return (
          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
            {type}
          </span>
        );
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Evaluations</h1>

      {/* Evaluation Summary */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">LLM Judge</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">{llmJudgeEvals.length}</dd>
          <dd className="mt-2 text-sm text-green-400">
            Avg score: {avgScore(llmJudgeEvals).toFixed(2)}
          </dd>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">Rule-Based</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">{ruleBasedEvals.length}</dd>
          <dd className="mt-2 text-sm text-green-400">
            {ruleBasedEvals.length > 0
              ? `${((ruleBasedEvals.filter((e) => e.score >= 0.8).length / ruleBasedEvals.length) * 100).toFixed(0)}% pass rate`
              : 'No data'}
          </dd>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">Human Feedback</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">{humanEvals.length}</dd>
          <dd className="mt-2 text-sm text-green-400">
            {humanEvals.length > 0
              ? `Avg rating: ${avgScore(humanEvals).toFixed(1)}`
              : 'No data'}
          </dd>
        </div>
      </div>

      {/* Evaluations Table */}
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
                  Trace ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Evaluator
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Criteria
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                    Loading...
                  </td>
                </tr>
              ) : evaluations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                    No evaluations found
                  </td>
                </tr>
              ) : (
                evaluations.map((evaluation) => (
                  <tr key={evaluation.id} className="hover:bg-gray-750">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white font-mono">
                      {evaluation.trace_id.slice(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getEvaluatorBadge(evaluation.evaluator_type)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {evaluation.score.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {evaluation.criteria
                        ? Object.keys(evaluation.criteria).join(', ')
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {formatTimeAgo(evaluation.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Evaluations;
