import React, { useState } from 'react';
import { useAlerts } from '../contexts/AlertsContext';
import { ReportService } from '../services/reportService';
import { useAuth } from '@/contexts/AuthContext';

const Dashboard: React.FC = () => {
  const { alerts, stats, error, isLoading, generateReport } = useAlerts();
  const { user } = useAuth();
  const [generatingReports, setGeneratingReports] = useState<Set<string>>(new Set());
  const isConnected = !isLoading;

  const handleGenerateReport = async (alertId: string) => {
    await ReportService.handleGenerateReportForDashboard(alertId, {
      generateReport,
      generatingReports,
      setGeneratingReports,
      isConnected
    });
  };

  const handleViewReport = (reportUrl: string) => {
    window.open(reportUrl, '_blank');
  };

  const getReportButtonContent = (alert: any) => {
    if (alert.status === 'investigating') {
      return 'Generating...';
    }
    
    // Only show "View Report" if BOTH status is resolved AND reportUrl exists
    if (alert.status === 'resolved' && alert.reportUrl) {
      return 'View Report';
    }
    
    // Default to "Generate Report" for all other cases
    return 'Generate Report';
  };

  const handleReportButtonClick = async (alert: any) => {
    // Check if this is a "View Report" scenario (completed investigation with report URL)
    const isViewReportMode = alert.status === 'resolved' && alert.reportUrl;
    
    if (alert.status === 'investigating') {
      // Do nothing - investigation in progress, button should be disabled
      return;
    }
    
    // STRICT CHECK: Only open report if BOTH conditions are true
    if (isViewReportMode) {
      // Open report in new tab
      handleViewReport(alert.reportUrl);
      return; // Early return to prevent fallback
    }
    
    // Generate new report for all other cases
    await handleGenerateReport(alert.id);
  };

  const isInvestigationDisabled = (alert: any) => {
    // Button should be disabled when investigating or when not connected
    return !isConnected || alert.status === 'investigating';
  };

  const getButtonClasses = (alert: any) => {
    // Check if this is a "View Report" scenario (completed investigation with report URL)
    const isViewReportMode = alert.status === 'resolved' && alert.reportUrl;
    
    // Determine disabled state - "View Report" is never disabled by role
    const isDisabledForInvestigation = isInvestigationDisabled(alert);
    const isDisabledForRole = !isViewReportMode && (user?.role === 'viewer'); // Only restrict role for "Generate Report"
    
    if (isViewReportMode) {
      // Always green and accessible for "View Report"
      return 'bg-green-600 hover:bg-green-700 text-white';
    } else if (isDisabledForRole) {
      // Halftone gray for viewer users trying to generate reports
      return 'bg-gray-500 text-gray-300 cursor-not-allowed opacity-60';
    } else if (isDisabledForInvestigation) {
      // Yellow for investigation-level restrictions
      return 'bg-yellow-600 cursor-not-allowed text-white';
    } else {
      // Default primary state for "Generate Report"
      return 'bg-blue-600 hover:bg-blue-700 text-white';
    }
  };

  const isButtonDisabled = (alert: any) => {
    const isViewReportMode = alert.status === 'resolved' && alert.reportUrl;
    const isDisabledForInvestigation = isInvestigationDisabled(alert);
    const isDisabledForRole = !isViewReportMode && (user?.role === 'viewer');
    
    return isDisabledForInvestigation || isDisabledForRole;
  };

  return (
    <div className="w-full h-full p-4 md:p-8 bg-zinc-900 text-white">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
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
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-1 text-white">
              Active Alerts
            </h3>
            <p className="text-2xl font-bold text-primary">
              {stats.active}
            </p>
            <p className="text-xs text-zinc-300">
              {stats.total} total
            </p>
          </div>
          
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-1 text-white">
              Critical
            </h3>
            <p className="text-2xl font-bold text-red-400">
              {stats.critical}
            </p>
            <p className="text-xs text-zinc-300">
              Immediate attention
            </p>
          </div>
          
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-1 text-white">
              High Priority
            </h3>
            <p className="text-2xl font-bold text-orange-400">
              {stats.high}
            </p>
            <p className="text-xs text-zinc-300">
              Urgent response
            </p>
          </div>
          
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-1 text-white">
              Data Sources
            </h3>
            <p className="text-2xl font-bold text-yellow-400">
              {Object.keys(stats.bySource).length}
            </p>
            <p className="text-xs text-zinc-300">
              Reddit, 311, Twitter
            </p>
          </div>
        </div>

        {/* Compact Priority & Status Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="card p-4">
            <h3 className="text-lg font-semibold mb-3 text-white">Priority Breakdown</h3>
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

          <div className="card p-4">
            <h3 className="text-lg font-semibold mb-3 text-white">Status Overview</h3>
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
          <h3 className="text-xl font-semibold mb-4 text-white">Alert Reports</h3>
          {alerts.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-zinc-400">No alerts available</p>
              {!isConnected && (
                <p className="text-sm text-zinc-500 mt-2">Waiting for connection...</p>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
              {alerts.slice(0, 12).map((alert) => (
                <div key={alert.id} className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
                  <div className="flex items-start justify-between mb-3">
                    <div className={`w-3 h-3 rounded-full mt-1 priority-${alert.priority}`}></div>
                    <span className={`text-xs px-2 py-1 rounded priority-badge priority-${alert.priority}`}>
                      {alert.priority}
                    </span>
                  </div>
                  
                  <h4 className="text-white font-medium text-sm mb-2 line-clamp-2">
                    {alert.title}
                  </h4>
                  <p className="text-xs text-zinc-300 mb-3 line-clamp-2">
                    {alert.description}
                  </p>
                  
                  <div className="text-xs text-zinc-400 mb-3">
                    <div>{alert.neighborhood}, {alert.borough}</div>
                    <div className="flex justify-between mt-1">
                      <span>{alert.source}</span>
                      <span>{new Date(alert.timestamp).toLocaleDateString()}</span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleReportButtonClick(alert)}
                      disabled={isButtonDisabled(alert)}
                      className={`flex-1 text-xs px-3 py-2 rounded transition-colors ${getButtonClasses(alert)}`}
                    >
                      {getReportButtonContent(alert)}
                    </button>
                    
                    <div className={`text-xs px-2 py-2 rounded text-center min-w-16 ${
                      alert.status === 'resolved' ? 'bg-green-900 text-green-300' :
                      alert.status === 'investigating' ? 'bg-blue-900 text-blue-300' :
                      'bg-zinc-700 text-zinc-300'
                    }`}>
                      {alert.status}
                    </div>
                  </div>
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