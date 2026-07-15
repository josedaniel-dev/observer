import { lazy, Suspense } from 'react';
import { Routes, Route, Link } from 'react-router-dom';

// Code-split page components
const Overview = lazy(() => import('./pages/Overview'));
const Traces = lazy(() => import('./pages/Traces'));
const TraceDetail = lazy(() => import('./pages/TraceDetail'));
const Evaluations = lazy(() => import('./pages/Evaluations'));

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-gray-400">Loading...</div>
    </div>
  );
}

function App() {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Navigation */}
      <nav className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold text-white">
                LLM Observatory
              </Link>
              <div className="ml-10 flex items-baseline space-x-4">
                <Link
                  to="/"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  Overview
                </Link>
                <Link
                  to="/traces"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  Traces
                </Link>
                <Link
                  to="/evaluations"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  Evaluations
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/traces" element={<Traces />} />
            <Route path="/traces/:traceId" element={<TraceDetail />} />
            <Route path="/evaluations" element={<Evaluations />} />
            <Route path="*" element={
              <div className="text-center py-20">
                <h1 className="text-4xl font-bold text-white mb-4">404</h1>
                <p className="text-gray-400">Page not found</p>
              </div>
            } />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

export default App;
