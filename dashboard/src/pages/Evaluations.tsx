import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { Evaluation } from '../types';
import { formatTimeAgo } from '../components/shared';

function Evaluations() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [evaluatorFilter, setEvaluatorFilter] = useState('');
  const [selectedEval, setSelectedEval] = useState<Evaluation | null>(null);
  const limit = 50;

  const fetchEvaluations = useCallback(async (offset: number) => {
    setLoading(true);
    try {
      const data = await api.listEvaluations({
        limit,
        offset,
        evaluator_type: evaluatorFilter || undefined,
      });
      setEvaluations(data.evaluations);
      setTotal(data.total);
      setHasMore(offset + data.evaluations.length < data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [evaluatorFilter]);

  useEffect(() => {
    setPage(0);
    fetchEvaluations(0);
  }, [fetchEvaluations]);

  useEffect(() => {
    if (page > 0) fetchEvaluations(page * limit);
  }, [page, fetchEvaluations]);

  const llmJudgeEvals = evaluations.filter((e) => e.evaluator_type === 'llm_judge');
  const ruleBasedEvals = evaluations.filter((e) => e.evaluator_type === 'rule_based');
  const humanEvals = evaluations.filter((e) => e.evaluator_type === 'human');

  const avgScore = (evals: Evaluation[]) => {
    const scored = evals.filter((e) => e.score != null);
    if (scored.length === 0) return null;
    return scored.reduce((sum, e) => sum + (e.score ?? 0), 0) / scored.length;
  };

  const getEvaluatorBadge = (type: string) => {
    switch (type) {
      case 'llm_judge':
        return <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">LLM Judge</span>;
      case 'rule_based':
        return <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">Rule-Based</span>;
      case 'human':
        return <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Human</span>;
      default:
        return <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">{type}</span>;
    }
  };

  const renderAvg = (avg: number | null) =>
    avg != null ? avg.toFixed(2) : 'N/A';

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Evaluations</h1>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">LLM Judge</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">{llmJudgeEvals.length}</dd>
          <dd className="mt-2 text-sm text-green-400">Avg score: {renderAvg(avgScore(llmJudgeEvals))}</dd>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">Rule-Based</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">{ruleBasedEvals.length}</dd>
          <dd className="mt-2 text-sm text-green-400">
            {ruleBasedEvals.length > 0
              ? `${((ruleBasedEvals.filter((e) => (e.score ?? 0) >= 0.8).length / ruleBasedEvals.length) * 100).toFixed(0)}% pass rate`
              : 'No data'}
          </dd>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">Human Feedback</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">{humanEvals.length}</dd>
          <dd className="mt-2 text-sm text-green-400">
            {humanEvals.length > 0 ? `Avg rating: ${renderAvg(avgScore(humanEvals))}` : 'No data'}
          </dd>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <select
            value={evaluatorFilter}
            onChange={(e) => setEvaluatorFilter(e.target.value)}
            className="bg-gray-700 text-white px-4 py-2 rounded-md"
          >
            <option value="">All Evaluators</option>
            <option value="llm_judge">LLM Judge</option>
            <option value="rule_based">Rule-Based</option>
            <option value="human">Human</option>
          </select>
          <div className="text-sm text-gray-400 flex items-center">
            {total} evaluation{total !== 1 ? 's' : ''} total
          </div>
        </div>
      </div>

      {error ? (
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">Error: {error}</p>
          <p className="text-gray-500 text-sm mt-2">Make sure the backend is running</p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Trace</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Evaluator</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Criteria</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-400">Loading...</td></tr>
              ) : evaluations.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-400">No evaluations found</td></tr>
              ) : (
                evaluations.map((evaluation) => (
                  <tr
                    key={evaluation.id}
                    className={`hover:bg-gray-700 cursor-pointer ${selectedEval?.id === evaluation.id ? 'bg-gray-700' : ''}`}
                    onClick={() => setSelectedEval(selectedEval?.id === evaluation.id ? null : evaluation)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                      <Link to={`/traces/${evaluation.trace_id}`} className="text-blue-400 hover:text-blue-300">
                        {evaluation.trace_id.slice(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{getEvaluatorBadge(evaluation.evaluator_type)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {evaluation.score != null ? evaluation.score.toFixed(2) : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {evaluation.criteria ? Object.keys(evaluation.criteria).join(', ') : '-'}
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

      <div className="mt-4 flex items-center justify-between">
        <div className="text-sm text-gray-400">
          Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}
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

      {selectedEval && (
        <div className="mt-6 bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-4">Evaluation Detail</h3>
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <span className="text-gray-400">ID: </span>
              <span className="text-white font-mono">{selectedEval.id}</span>
            </div>
            <div>
              <span className="text-gray-400">Score: </span>
              <span className="text-white">{selectedEval.score != null ? selectedEval.score.toFixed(4) : 'N/A'}</span>
            </div>
          </div>
          {selectedEval.criteria && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Criteria</h4>
              <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 overflow-x-auto">
                {JSON.stringify(selectedEval.criteria, null, 2)}
              </pre>
            </div>
          )}
          {selectedEval.result && (
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-2">Result</h4>
              <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 overflow-x-auto">
                {JSON.stringify(selectedEval.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Evaluations;
