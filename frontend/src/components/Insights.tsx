import React, { useState, useMemo } from "react";
import { useAlerts } from "../contexts/AlertsContext";
import { useAlertStats } from "../contexts/AlertStatsContext";
import { Alert } from "../types";
import Spinner from "./Spinner";
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
  Legend,
} from "recharts";

const Insights: React.FC = () => {
  // Get alerts from AlertsContext
  const { alerts, isLoading: alertsLoading } = useAlerts();

  // Get stats and categories from AlertStatsContext
  const { alertStats, alertCategories, isLoading: statsLoading, error: statsError } = useAlertStats();

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // Overall loading state
  const isLoading = alertsLoading || statsLoading;

  // Day names array - moved before chartData useMemo
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // Category colors for consistent theming
  const categoryColors = {
    infrastructure: "#3b82f6", // blue
    emergency: "#ef4444", // red
    transportation: "#8b5cf6", // purple
    events: "#ec4899", // pink
    safety: "#f97316", // orange
    environment: "#10b981", // green
    housing: "#eab308", // yellow
    general: "#6b7280", // gray
  };

  // Process alerts data for charts
  const chartData = useMemo(() => {
    if (!alerts.length) return { categoryData: [], timeData: [], priorityData: [], dateInfo: [], debugInfo: null };

    // Debug: Log alert timestamps to understand date range
    const timestamps = alerts.map((alert) => new Date(alert.timestamp));
    const minDate = new Date(Math.min(...timestamps.map((d) => d.getTime())));
    const maxDate = new Date(Math.max(...timestamps.map((d) => d.getTime())));

    // Category breakdown
    const categoryCount = alerts.reduce((acc, alert) => {
      const category = alert.category || "general";
      acc[category] = (acc[category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const categoryData = Object.entries(categoryCount).map(([category, count]) => ({
      name: category.charAt(0).toUpperCase() + category.slice(1),
      value: count,
      color: categoryColors[category as keyof typeof categoryColors] || "#6b7280",
    }));

    // Get unique dates from alerts and sort them chronologically
    const uniqueDates = [
      ...new Set(
        alerts.map((alert) => {
          const date = new Date(alert.timestamp);
          return date.toDateString(); // This gives us "Mon Jan 01 2024" format
        }),
      ),
    ].sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

    // Create date info for X-axis
    const dateInfo = uniqueDates.map((dateStr, index) => {
      const date = new Date(dateStr);
      const alertsOnThisDate = alerts.filter((alert) => new Date(alert.timestamp).toDateString() === dateStr).length;

      return {
        index,
        dateStr,
        shortLabel: `${date.getMonth() + 1}/${date.getDate()}`, // MM/DD format
        dayName: dayNames[date.getDay()],
        alertCount: alertsOnThisDate,
      };
    });

    // Time-based scatter plot data with intelligent clustering prevention
    const timeData = alerts.map((alert, alertIndex) => {
      const date = new Date(alert.timestamp);
      const dateStr = date.toDateString();
      const dateIndex = uniqueDates.indexOf(dateStr);
      const hourOfDay = date.getHours();

      return {
        originalX: dateIndex,
        originalY: hourOfDay,
        category: alert.category || "general",
        title: alert.title,
        priority: alert.priority,
        color: categoryColors[alert.category as keyof typeof categoryColors] || "#6b7280",
        alert: alert,
        alertIndex, // Store original index for stable jitter
      };
    });

    // Apply intelligent spreading to prevent clustering
    const maxDateIndex = uniqueDates.length - 1;
    const spreadTimeData = timeData.map((point) => {
      // Scale the position to use more chart width (map 0-2 to 0-10 for better spacing)
      const scaleFactor = maxDateIndex > 0 ? 10 / maxDateIndex : 1;
      const scaledOriginalX = point.originalX * scaleFactor;

      // Find all points with same or very similar coordinates
      const similarPoints = timeData.filter(
        (p) => Math.abs(p.originalX - point.originalX) < 0.1 && Math.abs(p.originalY - point.originalY) < 0.5, // Smaller tolerance for hour grouping
      );

      if (similarPoints.length <= 1) {
        // If no clustering, just add small horizontal jitter only
        return {
          ...point,
          x: scaledOriginalX + (Math.random() - 0.5) * 0.5,
          y: point.originalY, // Keep exact hour - no vertical jitter
        };
      }

      // For clustered points, spread them out horizontally only
      const pointIndex = similarPoints.findIndex((p) => p.alertIndex === point.alertIndex);
      const totalSimilar = similarPoints.length;

      // Create horizontal spread pattern for clustered points
      const horizontalSpread = (pointIndex - totalSimilar / 2) * 0.15; // Systematic horizontal spacing

      // Add some horizontal randomness to avoid perfect lines
      const randomX = (Math.random() - 0.5) * 0.2;

      return {
        ...point,
        x: scaledOriginalX + horizontalSpread + randomX,
        y: point.originalY, // Keep exact hour - preserve time accuracy
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
      color:
        priority === "critical"
          ? "#ef4444"
          : priority === "high"
          ? "#f97316"
          : priority === "medium"
          ? "#eab308"
          : "#10b981",
    }));

    const debugInfo = {
      totalAlerts: alerts.length,
      dateRange: { minDate: minDate.toDateString(), maxDate: maxDate.toDateString() },
      uniqueDates: uniqueDates.length,
      pointsGenerated: spreadTimeData.length,
    };

    return { categoryData, timeData: spreadTimeData, priorityData, dateInfo, debugInfo };
  }, [alerts]);

  const handleScatterClick = (data: any) => {
    if (data && data.alert) {
      setSelectedAlert(data.alert);
    }
  };

  const closeAlertModal = () => {
    setSelectedAlert(null);
  };

  // Custom tooltip for scatter plot
  const ScatterTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      const dateInfo = chartData.dateInfo[data.x];
      return (
        <div className="bg-zinc-800 p-3 rounded-lg border border-zinc-700 shadow-lg">
          <p className="text-white font-medium">{data.title}</p>
          <p className="text-zinc-300 text-sm">Category: {data.category}</p>
          <p className="text-zinc-300 text-sm">Priority: {data.priority}</p>
          <p className="text-zinc-300 text-sm">
            {dateInfo?.dayName} {dateInfo?.shortLabel} at {data.y}:00
          </p>
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <div className="w-full h-full bg-zinc-900 relative">
        <Spinner />
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-zinc-900">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-2">Error loading insights</p>
          <p className="text-zinc-400">{statsError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-zinc-900 text-white overflow-y-auto">
      <div className="max-w-7xl mx-auto p-4 md:p-6 space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold text-white">NYC Alert Insights</h2>
            <p className="text-zinc-400 text-sm mt-1">
              Analytics from the last 3 days • {alerts.length} alerts (of {alertStats?.stats.total || "..."} total)
            </p>
          </div>
        </div>

        {/* Stats Overview */}
        {alertStats ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card p-4">
              <h3 className="text-lg font-semibold mb-2">Monitor Alerts</h3>
              <p className="text-3xl font-bold text-blue-400">{alertStats.stats.monitor_alerts}</p>
              <p className="text-sm text-zinc-300">Reddit, Twitter, etc.</p>
            </div>
            <div className="card p-4">
              <h3 className="text-lg font-semibold mb-2">311 Signals</h3>
              <p className="text-3xl font-bold text-yellow-400">{alertStats.stats.nyc_311_signals}</p>
              <p className="text-sm text-zinc-300">Official city reports</p>
            </div>
            <div className="card p-4">
              <h3 className="text-lg font-semibold mb-2">Total Alerts</h3>
              <p className="text-3xl font-bold text-green-400">{alertStats.stats.total}</p>
              <p className="text-sm text-zinc-300">{alertStats.timeframe}</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card relative h-24">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-zinc-600 rounded-full"></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Category Pie Chart */}
          <div className="card p-4">
            <h3 className="text-xl font-semibold mb-4">Alerts by Category</h3>
            {chartData.categoryData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData.categoryData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {chartData.categoryData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [value, "Alerts"]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 relative">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-zinc-600 rounded-full"></div>
                </div>
              </div>
            )}
          </div>

          {/* Priority Breakdown */}
          <div className="card p-4">
            <h3 className="text-xl font-semibold mb-4">Alerts by Priority</h3>
            {chartData.priorityData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData.priorityData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1f2937",
                        border: "1px solid #374151",
                        borderRadius: "8px",
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
            ) : (
              <div className="h-64 relative">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-zinc-600 rounded-full"></div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Time-based Scatter Plot */}
        <div className="card p-4">
          <h3 className="text-xl font-semibold mb-4">Alert Timing Patterns</h3>
          <p className="text-sm text-zinc-400 mb-4">
            Click on dots to see alert details. X-axis: Date, Y-axis: Hour of day (Last 3 days)
          </p>
          {chartData.debugInfo && (
            <p className="text-xs text-zinc-500 mb-2">
              Debug: {chartData.debugInfo.totalAlerts} alerts across {chartData.debugInfo.uniqueDates} days (
              {chartData.debugInfo.dateRange.minDate} to {chartData.debugInfo.dateRange.maxDate})
            </p>
          )}
          {chartData.timeData.length > 0 ? (
            <div className="h-[28rem] sm:h-96 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 30, bottom: 90, left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="x"
                    type="number"
                    domain={["dataMin - 1", "dataMax + 1"]}
                    ticks={chartData.dateInfo.map((_, index) => {
                      const scaleFactor = chartData.dateInfo.length > 1 ? 10 / (chartData.dateInfo.length - 1) : 1;
                      return index * scaleFactor;
                    })}
                    tickFormatter={(value) => {
                      const scaleFactor = chartData.dateInfo.length > 1 ? 10 / (chartData.dateInfo.length - 1) : 1;
                      const dateIndex = Math.round(value / scaleFactor);
                      const dateInfo = chartData.dateInfo[dateIndex];
                      return dateInfo ? `${dateInfo.dayName} ${dateInfo.shortLabel}` : "";
                    }}
                    stroke="#9ca3af"
                    interval={0}
                    angle={-45}
                    tick={{ textAnchor: "end", fontSize: 11 }}
                    allowDecimals={false}
                    includeHidden={false}
                  />
                  <YAxis
                    dataKey="y"
                    type="number"
                    domain={[-2, 25]}
                    stroke="#9ca3af"
                    label={{
                      value: "Hour of Day",
                      angle: -90,
                      position: "insideLeft",
                      style: { textAnchor: "middle" },
                    }}
                  />
                  <Tooltip content={<ScatterTooltip />} />
                  {Object.entries(categoryColors).map(([category, color]) => {
                    const categoryData = chartData.timeData.filter((d) => d.category === category);
                    return (
                      <Scatter
                        key={category}
                        name={category.charAt(0).toUpperCase() + category.slice(1)}
                        data={categoryData}
                        fill={color}
                        onClick={handleScatterClick}
                        style={{ cursor: "pointer" }}
                      />
                    );
                  })}
                  <Legend
                    verticalAlign="bottom"
                    height={60}
                    wrapperStyle={{ paddingTop: "15px", paddingBottom: "0px" }}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-[28rem] sm:h-96 relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-zinc-600 border-t-white rounded-full animate-spin"></div>
              </div>
            </div>
          )}
        </div>

        {/* Category Details */}
        {alertCategories ? (
          <div className="card p-4">
            <h3 className="text-xl font-semibold mb-4">Category Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(alertCategories.categories).map(([key, category]) => (
                <div key={key} className="bg-zinc-800 p-4 rounded-lg">
                  <h4
                    className="font-semibold text-lg mb-2"
                    style={{ color: categoryColors[key as keyof typeof categoryColors] }}
                  >
                    {category.name}
                  </h4>
                  <p className="text-sm text-zinc-300 mb-2">{category.types.length} alert types</p>
                  <div className="space-y-1">
                    {category.types.slice(0, 3).map((type) => (
                      <div key={type.key} className="text-xs text-zinc-400">
                        • {type.name}
                      </div>
                    ))}
                    {category.types.length > 3 && (
                      <div className="text-xs text-zinc-500">+{category.types.length - 3} more...</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="card p-4">
            <h3 className="text-xl font-semibold mb-4">Category Information</h3>
            <div className="relative h-40">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-zinc-600 border-t-white rounded-full animate-spin"></div>
              </div>
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
              <button onClick={closeAlertModal} className="text-zinc-400 hover:text-white">
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
                  <span className={`ml-2 capitalize priority-${selectedAlert.priority}`}>{selectedAlert.priority}</span>
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
                <span className="text-white ml-2 text-sm">{new Date(selectedAlert.timestamp).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Insights;
