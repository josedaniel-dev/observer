function Evaluations() {
  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Evaluations</h1>

      {/* Evaluation Summary */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">LLM Judge</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">456</dd>
          <dd className="mt-2 text-sm text-green-400">Avg score: 0.87</dd>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">Rule-Based</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">789</dd>
          <dd className="mt-2 text-sm text-green-400">94% pass rate</dd>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <dt className="text-sm font-medium text-gray-400">Human Feedback</dt>
          <dd className="mt-1 text-3xl font-semibold text-white">123</dd>
          <dd className="mt-2 text-sm text-green-400">Avg rating: 4.2/5</dd>
        </div>
      </div>

      {/* Evaluations Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Trace
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
            <tr className="hover:bg-gray-750">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                abc123
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                  LLM Judge
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                0.92
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                accuracy, safety
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                1 min ago
              </td>
            </tr>
            <tr className="hover:bg-gray-750">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                def456
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                  Rule-Based
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                1.00
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                max_latency, format
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                5 min ago
              </td>
            </tr>
            <tr className="hover:bg-gray-750">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                ghi789
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  Human
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                4/5
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                helpfulness
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                10 min ago
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Evaluations;
