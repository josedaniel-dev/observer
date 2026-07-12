function Traces() {
  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Traces</h1>

      {/* Filters */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="Search traces..."
            className="bg-gray-700 text-white px-4 py-2 rounded-md flex-1 min-w-[200px]"
          />
          <select className="bg-gray-700 text-white px-4 py-2 rounded-md">
            <option value="">All Statuses</option>
            <option value="ok">OK</option>
            <option value="error">Error</option>
          </select>
          <input
            type="date"
            className="bg-gray-700 text-white px-4 py-2 rounded-md"
          />
        </div>
      </div>

      {/* Traces Table */}
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
                Cost
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Created
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            <tr className="hover:bg-gray-750">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                openai.chat.completions.create
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  OK
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                245ms
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                $0.0032
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                2 min ago
              </td>
            </tr>
            <tr className="hover:bg-gray-750">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                anthropic.messages.create
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  OK
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                512ms
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                $0.0089
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                5 min ago
              </td>
            </tr>
            <tr className="hover:bg-gray-750">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                summarize
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                  ERROR
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                1234ms
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                $0.0156
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                10 min ago
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between">
        <div className="text-sm text-gray-400">
          Showing 1-10 of 100 traces
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1 bg-gray-700 text-white rounded-md hover:bg-gray-600">
            Previous
          </button>
          <button className="px-3 py-1 bg-gray-700 text-white rounded-md hover:bg-gray-600">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

export default Traces;
