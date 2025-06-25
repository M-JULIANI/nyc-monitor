import React from 'react';
import { useAlerts } from '../contexts/AlertsContext';

const Dashboard: React.FC = () => {
  const { alertsWithReports, stats, error, isLoading, isLoadingReports } = useAlerts();
  const isConnected = !isLoading;

  const handleViewReport = (reportUrl: string) => {
    console.log('reportUrl', reportUrl);
    
    // Convert edit URLs to view URLs for better public access
    let viewUrl = reportUrl;
    if (reportUrl.includes('/edit')) {
      // Convert from: https://docs.google.com/presentation/d/{id}/edit?usp=sharing
      // To: https://docs.google.com/presentation/d/{id}/preview
      viewUrl = reportUrl.replace('/edit?usp=sharing', '/preview').replace('/edit', '/preview');
    }
    
    console.log('Opening URL:', viewUrl);
    window.open(viewUrl, '_blank');
  };

  return (
    <div className="w-full h-full bg-zinc-900 text-white">
      <div className="h-full overflow-y-auto">
        <div className="min-h-full p-4 md:p-6">
          <div className="max-w-7xl mx-auto space-y-4 pb-8">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
              <h2 className="text-2xl md:text-3xl font-bold text-white">
                NYC Alert Dashboard & Reports
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
            
            {/* Compact Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="card p-3">
                <h3 className="text-sm font-semibold mb-1 text-white">
                  Active Alerts
                </h3>
                <p className="text-xl font-bold text-primary">
                  {stats.active}
                </p>
                <p className="text-xs text-zinc-300">
                  {stats.total} total
                </p>
              </div>
              
              <div className="card p-3">
                <h3 className="text-sm font-semibold mb-1 text-white">
                  Critical
                </h3>
                <p className="text-xl font-bold text-red-400">
                  {stats.critical}
                </p>
                <p className="text-xs text-zinc-300">
                  Immediate attention
                </p>
              </div>
              
              <div className="card p-3">
                <h3 className="text-sm font-semibold mb-1 text-white">
                  High Priority
                </h3>
                <p className="text-xl font-bold text-orange-400">
                  {stats.high}
                </p>
                <p className="text-xs text-zinc-300">
                  Urgent response
                </p>
              </div>
              
              <div className="card p-3">
                <h3 className="text-sm font-semibold mb-1 text-white">
                  Data Sources
                </h3>
                <p className="text-xl font-bold text-yellow-400">
                  {Object.keys(stats.bySource).length}
                </p>
                <p className="text-xs text-zinc-300">
                  Reddit, 311, Twitter
                </p>
              </div>
            </div>

            {/* Compact Priority & Status Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="card p-3">
                <h3 className="text-lg font-semibold mb-2 text-white">Priority Breakdown</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">Critical</span>
                    <span className="text-red-400 font-bold">{stats.critical}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">High</span>
                    <span className="text-orange-400 font-bold">{stats.high}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">Medium</span>
                    <span className="text-yellow-400 font-bold">{stats.medium}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">Low</span>
                    <span className="text-green-400 font-bold">{stats.low}</span>
                  </div>
                </div>
              </div>

              <div className="card p-3">
                <h3 className="text-lg font-semibold mb-2 text-white">Status Overview</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">New</span>
                    <span className="text-yellow-400 font-bold">{stats.byStatus.new || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">Investigating</span>
                    <span className="text-blue-400 font-bold">{stats.byStatus.investigating || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">Active</span>
                    <span className="text-orange-400 font-bold">{stats.byStatus.active || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-300 text-sm">Resolved</span>
                    <span className="text-green-400 font-bold">{stats.resolved}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Alert Reports Section */}
            <div className="card">
              <div className="p-4">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-white">Completed Investigation Reports</h3>
                    <p className="text-sm text-zinc-400 mt-1">View detailed reports from completed investigations</p>
                  </div>
                  <span className="text-sm text-zinc-400">
                    {isLoadingReports ? 'Loading...' : `${alertsWithReports.length} reports available`}
                  </span>
                </div>
                
                {isLoadingReports ? (
                  <div className="py-8 text-center">
                    <p className="text-zinc-400">Loading alert reports...</p>
                  </div>
                ) : alertsWithReports.length === 0 ? (
                  <div className="py-8 text-center">
                    <p className="text-zinc-400">No completed investigation reports available</p>
                    <p className="text-sm text-zinc-500 mt-2">Investigation reports will appear here after alerts are investigated and completed</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {alertsWithReports.slice(0, 24).map((alert) => {
                      // Debug: log each alert to see its structure
                      console.log('Alert object:', alert);
                      console.log('Alert reportUrl:', alert.reportUrl);
                      
                      return (
                      <div key={alert.id} className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
                        <div className="flex items-start justify-between mb-3">
                          <div className="w-3 h-3 rounded-full mt-1 bg-green-600"></div>
                          <span className="text-xs px-2 py-1 rounded bg-green-900 text-green-300">
                            Resolved
                          </span>
                        </div>
                        
                        <h4 className="text-white font-medium text-sm mb-2 line-clamp-2">
                          {alert.title}
                        </h4>
                        <p className="text-xs text-zinc-300 mb-3 line-clamp-2">
                          {alert.description || 'Investigation report available'}
                        </p>
                        
                        <div className="text-xs text-zinc-400 mb-3">
                          <div>{alert.source}</div>
                          <div className="flex justify-between mt-1">
                            <span>Status: {alert.status}</span>
                            <span>{alert.date ? new Date(alert.date).toLocaleDateString() : 'No date'}</span>
                          </div>
                        </div>
                        
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleViewReport(alert.reportUrl!)}
                            title="Open investigation report in new tab"
                            className="flex-1 text-xs px-3 py-2 rounded transition-colors bg-green-600 hover:bg-green-700 text-white flex items-center justify-center gap-1"
                          >
                            <span>View Report</span>
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 