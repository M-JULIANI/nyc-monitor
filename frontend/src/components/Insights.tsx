import React, { useState, useMemo } from 'react';
import { useAlerts } from '../contexts/AlertsContext';
import { useAlertStats } from '../contexts/AlertStatsContext';
import { Alert } from '../types';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Legend
} from 'recharts';

const Insights: React.FC = () => {
  const { alerts, error: alertsError, isLoading: alertsLoading } = useAlerts();
  const { 
    alertStats, 
    alertCategories, 
    isLoading: statsLoading, 
    error: statsError,
    timeRange,
    setTimeRange 
  } = useAlertStats();
  
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const isLoading = alertsLoading || statsLoading;
  const error = alertsError || statsError;

  // Category colors for consistent theming
  const categoryColors = {
    infrastructure: '#3b82f6', // blue
    emergency: '#ef4444', // red
    transportation: '#8b5cf6', // purple
    events: '#ec4899', // pink
    safety: '#f97316', // orange
    environment: '#10b981', // green
    housing: '#eab308', // yellow
    general: '#6b7280' // gray
  };

  // Process alerts data for charts
  const chartData = useMemo(() => {
    if (!alerts.length) return { categoryData: [], timeData: [], priorityData: [] };

    // Category breakdown
    const categoryCount = alerts.reduce((acc, alert) => {
      const category = alert.category || 'general';
      acc[category] = (acc[category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const categoryData = Object.entries(categoryCount).map(([category, count]) => ({
      name: category.charAt(0).toUpperCase() + category.slice(1),
      value: count,
      color: categoryColors[category as keyof typeof categoryColors] || '#6b7280'
    }));

    // Time-based scatter plot data
    const timeData = alerts.map(alert => {
      const date = new Date(alert.timestamp);
      const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
      const hourOfDay = date.getHours();
      
      return {
        x: dayOfWeek,
        y: hourOfDay,
        category: alert.category || 'general',
        title: alert.title,
        priority: alert.priority,
        color: categoryColors[alert.category as keyof typeof categoryColors] || '#6b7280',
        alert: alert // Store full alert for click handling
      };
    });

    // Priority breakdown
    const priorityCount = alerts.reduce((acc, alert) => {
      acc[alert.priority] = (acc[alert.priority] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const priorityData = Object.entries(priorityCount).map(([priority, count]) => ({
      name: priority.charAt(0).toUpperCase() + priority.slice(1),
      value: count,
      color: priority === 'critical' ? '#ef4444' :
             priority === 'high' ? '#f97316' :
             priority === 'medium' ? '#eab308' : '#10b981'
    }));

    return { categoryData, timeData, priorityData };
  }, [alerts]);

  const handleScatterClick = (data: any) => {
    if (data && data.alert) {
      setSelectedAlert(data.alert);
    }
  };

  const closeAlertModal = () => {
    setSelectedAlert(null);
  };

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  // Custom tooltip for scatter plot
  const ScatterTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      return (
        <div className="bg-zinc-800 p-3 rounded-lg border border-zinc-700 shadow-lg">
          <p className="text-white font-medium">{data.title}</p>
          <p className="text-zinc-300 text-sm">Category: {data.category}</p>
          <p className="text-zinc-300 text-sm">Priority: {data.priority}</p>
          <p className="text-zinc-300 text-sm">
            {dayNames[data.x]} at {data.y}:00
          </p>
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-zinc-900">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-white border-t-transparent"></div>
          <p className="text-white">Loading insights...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-zinc-900">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-2">Error loading insights</p>
          <p className="text-zinc-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full p-4 md:p-6 bg-zinc-900 text-white overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl md:text-3xl font-bold text-white">
            NYC Alert Insights
          </h2>
          
          {/* Time Range Selector */}
          <div className="flex items-center gap-4">
            <label className="text-sm text-zinc-300">Time Range:</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="bg-zinc-800 text-white border border-zinc-600 rounded px-3 py-1 text-sm"
            >
              <option value={24}>Last 24 hours</option>
              <option value={72}>Last 3 days</option>
              <option value={168}>Last 7 days</option>
            </select>
          </div>
        </div>

        {/* Stats Overview */}
        {alertStats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="card">
              <h3 className="text-lg font-semibold mb-2">Monitor Alerts</h3>
              <p className="text-3xl font-bold text-blue-400">{alertStats.stats.monitor_alerts}</p>
              <p className="text-sm text-zinc-300">Reddit, Twitter, etc.</p>
            </div>
            <div className="card">
              <h3 className="text-lg font-semibold mb-2">311 Signals</h3>
              <p className="text-3xl font-bold text-yellow-400">{alertStats.stats.nyc_311_signals}</p>
              <p className="text-sm text-zinc-300">Official city reports</p>
            </div>
            <div className="card">
              <h3 className="text-lg font-semibold mb-2">Total Alerts</h3>
              <p className="text-3xl font-bold text-green-400">{alertStats.stats.total}</p>
              <p className="text-sm text-zinc-300">{alertStats.timeframe}</p>
            </div>
          </div>
        )}

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Category Pie Chart */}
          <div className="card">
            <h3 className="text-xl font-semibold mb-4">Alerts by Category</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData.categoryData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {chartData.categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [value, 'Alerts']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Priority Breakdown */}
          <div className="card">
            <h3 className="text-xl font-semibold mb-4">Alerts by Priority</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData.priorityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1f2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="value">
                    {chartData.priorityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Time-based Scatter Plot */}
        <div className="card mb-8">
          <h3 className="text-xl font-semibold mb-4">Alert Timing Patterns</h3>
          <p className="text-sm text-zinc-400 mb-4">
            Click on dots to see alert details. X-axis: Day of week, Y-axis: Hour of day
          </p>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="x"
                  domain={[0, 6]}
                  ticks={[0, 1, 2, 3, 4, 5, 6]}
                  tickFormatter={(value) => dayNames[value]}
                  stroke="#9ca3af"
                />
                <YAxis
                  dataKey="y"
                  domain={[0, 23]}
                  stroke="#9ca3af"
                  label={{ value: 'Hour of Day', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                />
                <Tooltip content={<ScatterTooltip />} />
                {Object.entries(categoryColors).map(([category, color]) => {
                  const categoryData = chartData.timeData.filter(d => d.category === category);
                  return (
                    <Scatter
                      key={category}
                      name={category.charAt(0).toUpperCase() + category.slice(1)}
                      data={categoryData}
                      fill={color}
                      onClick={handleScatterClick}
                      style={{ cursor: 'pointer' }}
                    />
                  );
                })}
                <Legend />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Details */}
        {alertCategories && (
          <div className="card">
            <h3 className="text-xl font-semibold mb-4">Category Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(alertCategories.categories).map(([key, category]) => (
                <div key={key} className="bg-zinc-800 p-4 rounded-lg">
                  <h4 className="font-semibold text-lg mb-2" style={{ color: categoryColors[key as keyof typeof categoryColors] }}>
                    {category.name}
                  </h4>
                  <p className="text-sm text-zinc-300 mb-2">
                    {category.types.length} alert types
                  </p>
                  <div className="space-y-1">
                    {category.types.slice(0, 3).map((type) => (
                      <div key={type.key} className="text-xs text-zinc-400">
                        • {type.name}
                      </div>
                    ))}
                    {category.types.length > 3 && (
                      <div className="text-xs text-zinc-500">
                        +{category.types.length - 3} more...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-800 border border-zinc-700 rounded-xl p-6 max-w-md w-full">
            <div className="flex justify-between items-start mb-4">
              <h4 className="text-lg font-semibold text-white">Alert Details</h4>
              <button
                onClick={closeAlertModal}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-3">
              <div>
                <h5 className="font-medium text-white">{selectedAlert.title}</h5>
                <p className="text-sm text-zinc-300">{selectedAlert.description}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-zinc-400">Category:</span>
                  <span className="text-white ml-2 capitalize">{selectedAlert.category}</span>
                </div>
                <div>
                  <span className="text-zinc-400">Priority:</span>
                  <span className={`ml-2 capitalize priority-${selectedAlert.priority}`}>
                    {selectedAlert.priority}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-400">Source:</span>
                  <span className="text-white ml-2">{selectedAlert.source}</span>
                </div>
                <div>
                  <span className="text-zinc-400">Status:</span>
                  <span className="text-white ml-2 capitalize">{selectedAlert.status}</span>
                </div>
              </div>
              
              <div>
                <span className="text-zinc-400 text-sm">Location:</span>
                <span className="text-white ml-2 text-sm">
                  {selectedAlert.neighborhood}, {selectedAlert.borough}
                </span>
              </div>
              
              <div>
                <span className="text-zinc-400 text-sm">Time:</span>
                <span className="text-white ml-2 text-sm">
                  {new Date(selectedAlert.timestamp).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Insights; 