import React, { useState, useMemo } from "react";
import Map, { Layer, Source } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";
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
} from "recharts";

const MAPBOX_TOKEN = "pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA";

// Lightweight Mapbox component for category visualization
const CategoryMap: React.FC<{
  category: string;
  alerts: Alert[];
  color: string;
  count: number;
}> = ({ category, alerts, color, count }) => {
  // Fixed NYC viewport for all maps - adjusted to show more of Queens
  const viewport = useMemo(() => ({
    longitude: -73.87,
    latitude: 40.7,
    zoom: 9.2           
  }), []);

  // Generate GeoJSON for alert points with weight for heatmap
  const alertsGeoJSON = useMemo(() => {
    const features = alerts.map(alert => ({
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [alert.coordinates.lng, alert.coordinates.lat]
      },
      properties: {
        id: alert.id,
        category: alert.category,
        // Add weight for heatmap intensity
        weight: 1
      }
    }));

    return {
      type: "FeatureCollection" as const,
      features
    };
  }, [alerts]);

  // Generate heatmap colors based on category color
  const getHeatmapColors = useMemo(() => {
    // Convert hex color to RGB
    const hexToRgb = (hex: string) => {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      } : { r: 0, g: 0, b: 0 };
    };

    const rgb = hexToRgb(color);
    
    return [
      `rgba(${rgb.r},${rgb.g},${rgb.b},0)`,     // Transparent
      `rgba(${rgb.r},${rgb.g},${rgb.b},0.2)`,   // Very light
      `rgba(${rgb.r},${rgb.g},${rgb.b},0.4)`,   // Light
      `rgba(${rgb.r},${rgb.g},${rgb.b},0.6)`,   // Medium
      `rgba(${rgb.r},${rgb.g},${rgb.b},0.8)`,   // Strong
      `rgba(${rgb.r},${rgb.g},${rgb.b},1.0)`    // Full intensity
    ];
  }, [color]);

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold capitalize">{category}</h3>
        <span 
          className="px-3 py-1 rounded-full text-xs font-medium text-white"
          style={{ backgroundColor: color }}
        >
          {count} alerts
        </span>
      </div>
      
      <div className="relative overflow-hidden rounded-lg" style={{ height: '400px' }}>
        {alerts.length > 0 ? (
          <Map
            initialViewState={viewport}
            mapboxAccessToken={MAPBOX_TOKEN}
            style={{ width: "100%", height: "100%" }}
            mapStyle="mapbox://styles/mapbox/dark-v11"
            interactive={false}
            dragPan={false}
            dragRotate={false}
            scrollZoom={false}
            keyboard={false}
            doubleClickZoom={false}
          >
            <Source type="geojson" data={alertsGeoJSON}>
              <Layer
                id={`alert-heatmap-${category}`}
                type="heatmap"
                paint={{
                  // Heatmap weight based on properties
                  "heatmap-weight": ["get", "weight"],
                  
                  // Heatmap intensity varies by zoom level
                  "heatmap-intensity": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    0, 1,
                    9, 1.5,
                    15, 2
                  ],
                  
                  // Category-specific color ramp
                  "heatmap-color": [
                    "interpolate",
                    ["linear"],
                    ["heatmap-density"],
                    0, getHeatmapColors[0],
                    0.2, getHeatmapColors[1],
                    0.4, getHeatmapColors[2],
                    0.6, getHeatmapColors[3],
                    0.8, getHeatmapColors[4],
                    1, getHeatmapColors[5]
                  ],
                  
                  // Heatmap radius varies by zoom level
                  "heatmap-radius": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    0, 0.5,
                    9, 4,
                    15, 8
                  ],
                  
                  // Heatmap opacity
                  "heatmap-opacity": 0.8
                }}
              />
            </Source>
          </Map>
        ) : (
          <div className="w-full h-full bg-zinc-800 flex items-center justify-center rounded-lg">
            <span className="text-zinc-500 text-sm">No alerts in this category</span>
          </div>
        )}
        
      </div>
    </div>
  );
};

const Insights: React.FC = () => {
  // Get alerts and pre-computed chart data from AlertsContext
  const { alerts, chartData, isLoading: alertsLoading } = useAlerts();

  // Get stats and categories from AlertStatsContext
  const { alertStats, isLoading: statsLoading, error: statsError } = useAlertStats();

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // Overall loading state
  const isLoading = alertsLoading || statsLoading;

  // Chart data is now pre-computed in useAlerts hook for performance

  // Group alerts by category for maps
  const alertsByCategory = useMemo(() => {
    const grouped: Record<string, Alert[]> = {};
    
    alerts.forEach(alert => {
      const category = alert.category || 'general';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(alert);
    });
    
    return grouped;
  }, [alerts]);

  // Category colors (matching the chart colors)
  const categoryColors = useMemo(() => ({
    infrastructure: "#3b82f6", // blue
    emergency: "#ef4444", // red
    transportation: "#8b5cf6", // purple
    events: "#ec4899", // pink
    safety: "#f97316", // orange
    environment: "#10b981", // green
    housing: "#eab308", // yellow
    general: "#6b7280", // gray
  }), []);

  const closeAlertModal = () => {
    setSelectedAlert(null);
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
            <h2 className="text-2xl md:text-3xl font-bold text-white">Insights</h2>
            <p className="text-zinc-400 text-sm mt-2">
              Last 3 days • {alertStats?.stats.total || "..."} alerts
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

        {/* Category Maps Grid */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">Alerts by Category</h2>
          <p className="text-zinc-400 text-sm">
            Last 6 months {alerts?.length || "..."} alerts
          </p>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Object.entries(alertsByCategory)
              .sort(([,a], [,b]) => b.length - a.length) // Sort by alert count descending
              .map(([category, categoryAlerts]) => (
                <CategoryMap
                  key={category}
                  category={category}
                  alerts={categoryAlerts}
                  color={categoryColors[category as keyof typeof categoryColors] || categoryColors.general}
                  count={categoryAlerts.length}
                />
              ))
            }
          </div>
          
          {Object.keys(alertsByCategory).length === 0 && (
            <div className="text-center py-8">
              <p className="text-zinc-500">No alerts available for category mapping</p>
            </div>
          )}
        </div>

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
