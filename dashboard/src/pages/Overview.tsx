function Overview() {
  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-2xl font-bold mb-6">Dashboard Overview</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Traces" value="1,234" change="+12%" />
        <StatCard title="Total Spans" value="5,678" change="+8%" />
        <StatCard title="Total Cost" value="$123.45" change="+15%" />
        <StatCard title="Avg Latency" value="245ms" change="-5%" />
      </div>

      {/* Charts placeholder */}
      <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Cost Over Time</h2>
          <div className="h-64 flex items-center justify-center text-gray-500">
            Chart will be rendered here
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Latency Distribution</h2>
          <div className="h-64 flex items-center justify-center text-gray-500">
            Chart will be rendered here
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  change,
}: {
  title: string;
  value: string;
  change: string;
}) {
  const isPositive = change.startsWith('+');

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <dt className="text-sm font-medium text-gray-400 truncate">{title}</dt>
      <dd className="mt-1 text-3xl font-semibold text-white">{value}</dd>
      <dd
        className={`mt-2 text-sm ${
          isPositive ? 'text-green-400' : 'text-red-400'
        }`}
      >
        {change} from last period
      </dd>
    </div>
  );
}

export default Overview;
