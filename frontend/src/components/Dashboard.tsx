import React from 'react';
import { useAlerts } from '@/hooks/useAlerts';

const Dashboard: React.FC = () => {
  const { alerts, stats, error, isConnected } = useAlerts();

  return (
    <div className="w-full h-full p-4 md:p-8 bg-zinc-900 text-white">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-2xl md:text-3xl font-bold text-white">
            NYC Alert Dashboard
          </h2>
          <div className="flex items-center gap-2 text-sm">
            {isConnected ? (
              <span className="text-green-400">● Live</span>
            ) : (
              <span className="text-yellow-400">● Connecting...</span>
            )}
            {error && (
              <span className="text-red-400">⚠ {error}</span>
            )}
          </div>
        </div>
        
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-white">
              Active Alerts
            </h3>
            <p className="text-4xl font-bold text-primary">
              {stats.active}
            </p>
            <p className="text-sm text-zinc-300">
              {stats.total} total alerts
            </p>
          </div>
          
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-white">
              Critical Priority
            </h3>
            <p className="text-4xl font-bold text-critical">
              {stats.critical}
            </p>
            <p className="text-sm text-zinc-300">
              Requires immediate attention
            </p>
          </div>
          
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-white">
              High Priority
            </h3>
            <p className="text-4xl font-bold text-high">
              {stats.high}
            </p>
            <p className="text-sm text-zinc-300">
              Urgent response needed
            </p>
          </div>
          
          <div className="card">
            <h3 className="text-lg font-semibold mb-2 text-white">
              Data Sources
            </h3>
            <p className="text-4xl font-bold text-accent">
              {Object.keys(stats.bySource).length}
            </p>
            <p className="text-sm text-zinc-300">
              Reddit, 311, Twitter
            </p>
          </div>
        </div>

        {/* Priority Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="card">
            <h3 className="text-xl font-semibold mb-4 text-white">Priority Breakdown</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">Critical</span>
                <span className="text-critical font-bold">{stats.critical}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">High</span>
                <span className="text-high font-bold">{stats.high}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">Medium</span>
                <span className="text-medium font-bold">{stats.medium}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">Low</span>
                <span className="text-low font-bold">{stats.low}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-xl font-semibold mb-4 text-white">Status Overview</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">New</span>
                <span className="text-yellow-400 font-bold">{stats.byStatus.new || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">Investigating</span>
                <span className="text-blue-400 font-bold">{stats.byStatus.investigating || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">Resolved</span>
                <span className="text-green-400 font-bold">{stats.resolved}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="card">
          <h3 className="text-xl font-semibold mb-4 text-white">Recent Alerts</h3>
          {alerts.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-zinc-400">No alerts available</p>
              {!isConnected && (
                <p className="text-sm text-zinc-500 mt-2">Waiting for connection...</p>
              )}
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {alerts.slice(0, 10).map((alert) => (
                <div key={alert.id} className="flex items-start gap-3 p-3 bg-zinc-800 rounded-lg">
                  <div className={`w-3 h-3 rounded-full mt-1 priority-${alert.priority}`}></div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-white font-medium truncate">{alert.title}</h4>
                    <p className="text-sm text-zinc-300 truncate">{alert.description}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-zinc-400">
                      <span>{alert.neighborhood}, {alert.borough}</span>
                      <span>{alert.source}</span>
                      <span>{new Date(alert.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded priority-badge priority-${alert.priority}`}>
                    {alert.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 