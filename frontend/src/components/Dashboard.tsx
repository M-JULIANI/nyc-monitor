import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="w-full h-full p-4 md:p-8 bg-background text-text-primary">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold mb-8 text-text-primary">
          NYC Alert Dashboard
        </h2>
        
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-text-primary">
              Active Alerts
            </h3>
            <p className="text-4xl font-bold text-critical">
              23
            </p>
            <p className="text-sm text-text-muted">
              +4 from last hour
            </p>
          </div>
          
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-text-primary">
              Critical Priority
            </h3>
            <p className="text-4xl font-bold text-critical">
              3
            </p>
            <p className="text-sm text-text-muted">
              Requires immediate attention
            </p>
          </div>
          
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-text-primary">
              Reports Generated
            </h3>
            <p className="text-4xl font-bold text-accent">
              7
            </p>
            <p className="text-sm text-text-muted">
              Today
            </p>
          </div>
          
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-text-primary">
              Data Sources
            </h3>
            <p className="text-4xl font-bold text-primary">
              3
            </p>
            <p className="text-sm text-text-muted">
              Reddit, 311, Twitter
            </p>
          </div>
        </div>

        {/* Content area for future dashboard widgets */}
        <div className="card text-center">
          <h3 className="text-xl md:text-2xl font-semibold mb-4 text-text-primary">
            Dashboard Coming Soon
          </h3>
          <p className="text-text-muted mb-4">
            This dashboard will include:
          </p>
          <ul className="list-none p-0 text-text-secondary text-left max-w-2xl mx-auto space-y-2">
            <li className="flex items-center gap-2">
              <span className="text-xl">📊</span>
              <span>Real-time alert analytics</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-xl">📈</span>
              <span>Trend analysis and patterns</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-xl">🗺️</span>
              <span>Geographic distribution insights</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-xl">⏱️</span>
              <span>Response time metrics</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-xl">🔍</span>
              <span>Predictive hotspot analysis</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 