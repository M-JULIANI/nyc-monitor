import {useState, useRef, useEffect, useMemo} from "react";
import Map, {Layer, Source, Popup, Marker} from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import {Alert} from "../types";
import {useAlerts} from "../contexts/AlertsContext";
import {useMapState} from "../contexts/MapStateContext";
import Spinner from "./Spinner";
import AgentTraceModal from "./AgentTraceModal";
import {useAuth} from "@/contexts/AuthContext";

const MAPBOX_TOKEN = "pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA";

// Custom slider styles
const sliderStyles = `
  .slider::-webkit-slider-thumb {
    appearance: none;
    height: 20px;
    width: 20px;
    border-radius: 50%;
    background: #3b82f6;
    cursor: pointer;
    border: 2px solid #ffffff;
    box-shadow: 0 0 0 1px #374151;
  }

  .slider::-moz-range-thumb {
    height: 20px;
    width: 20px;
    border-radius: 50%;
    background: #3b82f6;
    cursor: pointer;
    border: 2px solid #ffffff;
    box-shadow: 0 0 0 1px #374151;
  }

  .slider::-webkit-slider-track {
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(to right, #dc2626 0%, #ea580c 25%, #d97706 50%, #65a30d 75%, #16a34a 100%);
  }

  .slider::-moz-range-track {
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(to right, #dc2626 0%, #ea580c 25%, #d97706 50%, #65a30d 75%, #16a34a 100%);
    border: none;
  }

  /* Mobile and iOS specific styles */
  @media (max-width: 768px) {
    .mobile-map-container {
      height: calc(100vh - 120px) !important;
      height: calc(100vh - 120px - env(safe-area-inset-bottom)) !important;
      max-height: calc(100vh - 120px) !important;
      max-height: calc(100vh - 120px - env(safe-area-inset-bottom)) !important;
    }
    
    .mobile-timeline-slider {
      bottom: calc(16px + env(safe-area-inset-bottom)) !important;
      padding-bottom: env(safe-area-inset-bottom);
    }
  }

  /* iOS specific fixes */
  @supports (-webkit-touch-callout: none) {
    .ios-map-container {
      height: calc(100vh - 120px - env(safe-area-inset-top) - env(safe-area-inset-bottom)) !important;
      max-height: calc(100vh - 120px - env(safe-area-inset-top) - env(safe-area-inset-bottom)) !important;
    }
  }
`;

const MapView: React.FC = () => {
const mapRef = useRef<any>(null);
//const markerClickedRef = useRef(false);
const {alerts, error, isLoading, generateReport, refetchAlert} = useAlerts();
const {user} = useAuth();
const isConnected = !isLoading;
const {viewport, setViewport, filter, setFilter, viewMode, setViewMode} = useMapState();
const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
const [selectedAlertLoading, setSelectedAlertLoading] = useState(false);
const [isFilterCollapsed, setIsFilterCollapsed] = useState(false);
const [traceModal, setTraceModal] = useState<{isOpen: boolean; traceId: string; alertTitle: string}>({
isOpen: false,
traceId: "",
alertTitle: "",
});

// Track if we should auto-fit to alerts (only on first load or filter changes)
const [shouldAutoFit, setShouldAutoFit] = useState(true);

// Calculate bounds for all visible alerts
const calculateAlertBounds = (alerts: Alert[]) => {
if (alerts.length === 0) return null;

let minLat = Infinity;
let maxLat = -Infinity;
let minLng = Infinity;
let maxLng = -Infinity;

alerts.forEach((alert) => {
const {lat, lng} = alert.coordinates;
minLat = Math.min(minLat, lat);
maxLat = Math.max(maxLat, lat);
minLng = Math.min(minLng, lng);
maxLng = Math.max(maxLng, lng);
});

// Add padding (roughly 0.01 degrees = ~1km)
const padding = 0.01;
const paddedBounds: [[number, number], [number, number]] = [
[minLng - padding, minLat - padding], // Southwest corner
[maxLng + padding, maxLat + padding], // Northeast corner
];

return paddedBounds;
};

// Filter alerts based on current filter settings
const filteredAlerts = useMemo(() => {
//console.log('Filtering with timeRangeHours:', filter.timeRangeHours);

const filtered = alerts.filter((alert) => {
// Priority filter
if (filter.priority !== "all" && alert.priority !== filter.priority) return false;

// Source filter
if (filter.source !== "all" && alert.source !== filter.source) return false;

// Status filter
if (filter.status !== "all" && alert.status !== filter.status) return false;

// Time range filter - API sends 'date' field, not 'timestamp'
const alertTime = new Date(alert.timestamp);
const now = new Date();
const hoursAgo = (now.getTime() - alertTime.getTime()) / (1000 * 60 * 60);
if (hoursAgo > filter.timeRangeHours) return false;

return true;
});

//console.log(`Filtered from ${alerts.length} to ${filtered.length} alerts`);
return filtered;
}, [alerts, filter]);

// Update map bounds when alerts change, but only if we should auto-fit
useEffect(() => {
if (mapRef.current && filteredAlerts.length > 0 && shouldAutoFit) {
const bounds = calculateAlertBounds(filteredAlerts);
if (bounds) {
try {
mapRef.current.fitBounds(bounds, {
padding: {top: 100, bottom: 150, left: 300, right: 100}, // Extra bottom padding for slider
duration: 1000, // Smooth animation
maxZoom: 16, // Don't zoom in too close
});

// Update viewport state after fitBounds completes
setTimeout(() => {
if (mapRef.current) {
const newViewState = mapRef.current.getMap().getCenter();
const newZoom = mapRef.current.getMap().getZoom();
setViewport({
longitude: newViewState.lng,
latitude: newViewState.lat,
zoom: newZoom,
});
}
}, 1100); // Wait slightly longer than the animation duration

// Disable auto-fit after first automatic fit
setShouldAutoFit(false);
} catch (error) {
console.warn("Error fitting bounds:", error);
}
}
}
}, [filteredAlerts, shouldAutoFit, setViewport]); // Re-run when filtered alerts change

// Reset auto-fit when filters change
useEffect(() => {
setShouldAutoFit(true);
}, [filter]);

// Handle viewport changes from the map
const handleViewportChange = (evt: any) => {
setViewport({
longitude: evt.viewState.longitude,
latitude: evt.viewState.latitude,
zoom: evt.viewState.zoom,
});
};

const getSourceIcon = (source: string): string => {
switch (source) {
case "reddit":
return "👽"; // Reddit alien mascot
case "311":
return "📞";
case "twitter":
return "🐦";
default:
return "📍";
}
};

const getCategoryIcon = (category: string): string => {
switch (category) {
case "infrastructure":
return "🔧"; // Wrench for infrastructure
case "emergency":
return "🚨"; // Emergency siren
case "transportation":
return "🚗"; // Car for transportation
case "events":
return "🎪"; // Circus tent for events
case "safety":
return "🛡️"; // Shield for safety
case "environment":
return "🌿"; // Leaf for environment
case "housing":
return "🏠"; // House for housing
case "general":
return "📋"; // Clipboard for general
default:
return "📍"; // Default pin
}
};

const getBackgroundIconColor = (source: "reddit" | "311" | "twitter"): string => {
switch (source) {
case "reddit":
return "bg-orange-400";
case "311":
return "bg-yellow-400";
case "twitter":
return "bg-blue-400";
default:
return "bg-gray-400";
}
};

const getCategoryBackgroundColor = (category: string): string => {
switch (category) {
case "infrastructure":
return "bg-blue-500"; // Blue for infrastructure
case "emergency":
return "bg-red-500"; // Red for emergency
case "transportation":
return "bg-purple-500"; // Purple for transportation
case "events":
return "bg-pink-500"; // Pink for events
case "safety":
return "bg-orange-500"; // Orange for safety
case "environment":
return "bg-green-500"; // Green for environment
case "housing":
return "bg-yellow-500"; // Yellow for housing
case "general":
return "bg-gray-500"; // Gray for general
default:
return "bg-gray-400";
}
};

const getIconSize = (priority: string): number => {
switch (priority) {
case "critical":
return 18;
case "high":
return 12;
case "medium":
return 8;
case "low":
return 4;
default:
return 8;
}
};

// Create GeoJSON for alert points (only used in priority mode)
const alertsGeoJSON: GeoJSON.FeatureCollection = {
type: "FeatureCollection",
features: filteredAlerts.map((alert) => ({
type: "Feature" as const,
geometry: {
type: "Point" as const,
coordinates: [alert.coordinates.lng, alert.coordinates.lat],
},
properties: {
id: alert.id,
title: alert.title,
priority: alert.priority,
source: alert.source,
color: `priority-${alert.priority}`,
},
})),
};

const handleMarkerClick = (alert: Alert) => {
console.log("🖱️ MARKER CLICKED! Alert ID:", alert.id);
console.log("🖱️ isConnected:", isConnected);
// console.log('🖱️ Alert object:', alert);

if (!isConnected) {
console.log("🖱️ Not connected, returning early");
return;
}

console.log("🖱️ Calling handleAlertSelection...");
handleAlertSelection(alert);
};

const handleAlertSelection = (alert: Alert) => {
console.log("🎯 HANDLE ALERT SELECTION CALLED! Alert ID:", alert.id);

// Step 1: Set the alert immediately for instant popup
console.log("🎯 Setting selectedAlert to:", alert);
setSelectedAlert(alert);

// Step 1.5: Fly to center the marker on the map
if (mapRef.current) {
console.log("🗺️ Flying to marker coordinates:", alert.coordinates);

// Calculate offset to account for popup height
// Popup appears above the marker, so we need to shift the map center down
// This ensures the popup is fully visible without top clipping
const map = mapRef.current.getMap();
const containerHeight = map.getContainer().clientHeight;
const popupOffset = -200; // Approximate popup height in pixels
const offsetInDegrees = (popupOffset / containerHeight) * (map.getBounds().getNorth() - map.getBounds().getSouth());

mapRef.current.flyTo({
center: [alert.coordinates.lng, alert.coordinates.lat - offsetInDegrees], // Offset south to show popup fully
duration: 800, // Smooth 800ms animation
essential: true, // This animation is essential and will not be interrupted
});

// Update viewport state after flyTo completes
setTimeout(() => {
if (mapRef.current) {
const newViewState = mapRef.current.getMap().getCenter();
const newZoom = mapRef.current.getMap().getZoom();
setViewport({
longitude: newViewState.lng,
latitude: newViewState.lat,
zoom: newZoom,
});
}
}, 850); // Wait slightly longer than the animation duration
}

if (alert.source === "311") {
console.log("🎯 311 alert, returning early");
return;
}

// Step 2: Set loading state
console.log("🎯 Setting loading state to true");
setSelectedAlertLoading(true);

// Step 3: Start refetch in background (non-blocking)
console.log("🎯 Starting background refetch...");
setTimeout(() => {
console.log("🔄 Refetching alert data for:", alert.id);

refetchAlert(alert.id)
.then((result) => {
console.log("📥 Refetch completed for:", alert.id, result);
if (result.success && result.alert) {
console.log("✅ Updating with fresh data");
setSelectedAlert(result.alert);
} else {
console.warn("⚠️ Refetch failed, keeping cached data");
}
})
.catch((err) => {
console.warn("⚠️ Refetch error, keeping cached data:", err);
})
.finally(() => {
console.log("🏁 Clearing loading state");
setSelectedAlertLoading(false);
});
}, 50); // Small delay to ensure UI updates first
};

const handleViewTrace = (alert: Alert) => {
if (alert.traceId) {
setTraceModal({
isOpen: true,
traceId: alert.traceId,
alertTitle: alert.title,
});
}
};

const getReportButtonContent = (alert: Alert) => {
if (alert.status === "investigating") {
return (
<div className="flex items-center gap-2">
<div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
<span>Investigating...</span>
</div>
);
}

// Only show "View Report" if BOTH status is resolved AND reportUrl exists
if (alert.status === "resolved" && alert.reportUrl) {
return "View Report";
}

// Default to "Generate Report" for all other cases
return "Generate Report";
};

const handleReportButtonClick = async (alert: Alert) => {
// Enhanced status checking with double-click prevention
console.log(`Report button clicked for alert ${alert.id}:`, {
status: alert.status,
reportUrl: alert.reportUrl,
investigationId: alert.investigationId,
traceId: alert.traceId,
});

if (alert.status === "investigating") {
// Do nothing - investigation in progress, button should be disabled
console.log(`Investigation in progress for alert ${alert.id}, button click ignored`);
return;
}

// STRICT CHECK: Only open report if BOTH conditions are true
if (alert.status === "resolved" && alert.reportUrl) {
// Open report in new tab
console.log(`Opening existing report for alert ${alert.id}: ${alert.reportUrl}`);
window.open(alert.reportUrl, "_blank");
return; // Early return to prevent fallback
}

// Immediately update the alert state to show investigating AND set local loading
console.log(`Setting alert ${alert.id} to investigating state immediately`);
setSelectedAlert((prev) => (prev ? {...prev, status: "investigating" as const} : null));
setSelectedAlertLoading(true);

// Generate new report using local state management (avoid global loading)
console.log(`Generating new report for alert ${alert.id} - Status: ${alert.status}, ReportUrl: ${alert.reportUrl}`);

try {
const result = await generateReport(alert.id);
if (result.success) {
console.log("Report generation started:", result.investigationId);
// Update the selected alert with investigation details
setSelectedAlert((prev) =>
prev
? {
  ...prev,
  investigationId: result.investigationId,
  status: "investigating" as const,
  }
: null
);
} else {
console.error("Failed to generate report:", result.message);
// Revert the status on failure
setSelectedAlert((prev) => (prev ? {...prev, status: "active" as const} : null));
window.alert(`Failed to generate report: ${result.message}`);
}
} catch (err) {
console.error("Error generating report:", err);
// Revert the status on error
setSelectedAlert((prev) => (prev ? {...prev, status: "active" as const} : null));
window.alert("Failed to generate report");
} finally {
setSelectedAlertLoading(false);
}
};

const isInvestigationDisabled = (alert: Alert) => {
// Button should be disabled when investigating or when not connected
return !isConnected || alert.status === "investigating";
};

return (
<div className="relative w-full h-full">
{/* Inject custom slider styles */}
<style dangerouslySetInnerHTML={{__html: sliderStyles}} />

{/* Connection Status */}
{error && <div className="absolute top-4 right-4 z-20 bg-status-error/95 px-4 py-2 rounded-lg text-white text-sm">Error: {error}</div>}

{!isConnected && !error && <div className="absolute top-4 right-4 z-20 bg-status-connecting/95 px-4 py-2 rounded-lg text-white text-sm">Connecting to alert stream...</div>}

{/* Disconnected State Overlay */}
{!isConnected && (
<>
<div className="absolute inset-0 bg-black/50 z-20"></div>
<Spinner />
</>
)}

{/* Hamburger Menu Button - Always visible with better mobile positioning */}
<button
onClick={() => setIsFilterCollapsed(!isFilterCollapsed)}
className={`absolute top-4 left-4 z-20 bg-zinc-800/95 backdrop-blur-sm p-3 rounded-lg text-white hover:bg-zinc-700 transition-all duration-300 ease-in-out touch-manipulation ${!isConnected ? "opacity-50 pointer-events-none" : ""}`}
disabled={!isConnected}
style={{
minHeight: "48px", // Minimum touch target size for mobile
minWidth: "48px",
}}
>
<div className="flex flex-col space-y-1">
<div className="w-5 h-0.5 bg-white"></div>
<div className="w-5 h-0.5 bg-white"></div>
<div className="w-5 h-0.5 bg-white"></div>
</div>
</button>

{/* Filter Controls - Collapsible with better mobile sizing */}
{!isFilterCollapsed && (
<div className={`absolute top-16 left-4 z-10 bg-zinc-800/95 backdrop-blur-sm p-4 rounded-lg text-white min-w-[200px] w-[calc(100vw-32px)] sm:w-auto sm:max-w-[280px] transition-all duration-300 ease-in-out ${!isConnected ? "opacity-50 pointer-events-none" : ""}`}>
<h3 className="text-xs font-semibold mb-2 text-zinc-300">Filters</h3>

<div className="mb-2">
<label className="block text-xs mb-1 text-zinc-300">Priority</label>
<select
value={filter.priority}
onChange={(e) => setFilter((prev) => ({...prev, priority: e.target.value}))}
className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-xs"
disabled={!isConnected}
>
<option value="all">All</option>
<option value="critical">Critical</option>
<option value="high">High</option>
<option value="medium">Medium</option>
<option value="low">Low</option>
</select>
</div>

<div className="mb-2">
<label className="block text-xs mb-1 text-zinc-300">Source</label>
<select
value={filter.source}
onChange={(e) => setFilter((prev) => ({...prev, source: e.target.value}))}
className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-xs"
disabled={!isConnected}
>
<option value="all">All Sources</option>
<option value="reddit">Reddit</option>
<option value="311">311</option>
<option value="twitter">Twitter</option>
</select>
</div>

<div className="mb-4">
<label className="block text-xs mb-1 text-zinc-300">Status</label>
<select
value={filter.status}
onChange={(e) => setFilter((prev) => ({...prev, status: e.target.value}))}
className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-xs"
disabled={!isConnected}
>
<option value="all">All Status</option>
<option value="new">New</option>
<option value="investigating">Investigating</option>
<option value="resolved">Resolved</option>
</select>
</div>

{/* View Mode Toggles */}
<div className="border-t border-zinc-700 pt-3 mb-4">
<h4 className="text-xs font-semibold mb-2 text-zinc-300">View Mode</h4>
<div className="flex flex-col gap-2">
<label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
<input
type="radio"
name="viewMode"
value="category"
checked={viewMode === "category"}
onChange={(e) => setViewMode(e.target.value as "priority" | "source" | "category")}
className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
disabled={!isConnected}
/>
<span>By Category</span>
<span className="text-zinc-500 hidden sm:inline">(category icons)</span>
</label>
<label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
<input
type="radio"
name="viewMode"
value="source"
checked={viewMode === "source"}
onChange={(e) => setViewMode(e.target.value as "priority" | "source" | "category")}
className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
disabled={!isConnected}
/>
<span>By Source</span>
<span className="text-zinc-500 hidden sm:inline">(source icons)</span>
</label>
<label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
<input
type="radio"
name="viewMode"
value="priority"
checked={viewMode === "priority"}
onChange={(e) => setViewMode(e.target.value as "priority" | "source" | "category")}
className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
disabled={!isConnected}
/>
<span>By Priority</span>
<span className="text-zinc-500 hidden sm:inline">(colored circles)</span>
</label>
</div>
</div>

{/* Legend */}
<div className="border-t border-zinc-700 pt-3">
<h4 className="text-xs font-semibold mb-2 text-zinc-300">Legend</h4>

{/* Priority Mode Legend */}
{viewMode === "priority" && (
<div className="flex flex-col gap-1">
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-3 h-3 rounded-full bg-red-600"></div>
<span>Critical</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-3 h-3 rounded-full bg-orange-600"></div>
<span>High</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-3 h-3 rounded-full bg-yellow-600"></div>
<span>Medium</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-3 h-3 rounded-full bg-green-600"></div>
<span>Low</span>
</div>
</div>
)}

{/* Source Mode Legend */}
{viewMode === "source" && (
<div className="flex flex-col gap-1">
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-orange-400 flex items-center justify-center text-xs">👽</div>
<span>Reddit</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-yellow-400 flex items-center justify-center text-xs">📞</div>
<span>311</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-blue-400 flex items-center justify-center text-xs">🐦</div>
<span>Twitter</span>
</div>
</div>
)}

{/* Category Mode Legend */}
{viewMode === "category" && (
<div className="flex flex-col gap-1">
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center text-xs">🔧</div>
<span>Infrastructure</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-red-500 flex items-center justify-center text-xs">🚨</div>
<span>Emergency</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-purple-500 flex items-center justify-center text-xs">🚗</div>
<span>Transportation</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-pink-500 flex items-center justify-center text-xs">🎪</div>
<span>Events</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-orange-500 flex items-center justify-center text-xs">🛡️</div>
<span>Safety</span>
</div>
<div className="flex items-center gap-2 text-xs text-zinc-300">
<div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center text-xs">🌿</div>
<span>Environment</span>
</div>
</div>
)}
</div>
</div>
)}

{/* Alert Count - Mobile responsive */}
<div className={`absolute top-4 right-4 z-10 bg-zinc-800/95 px-3 sm:px-4 py-2 rounded-lg text-white text-xs sm:text-sm ${!isConnected ? "opacity-50" : ""}`}>
<span className="hidden sm:inline">{filteredAlerts.length} alerts visible</span>
<span className="sm:hidden">{filteredAlerts.length}</span>
{isConnected && <span className="ml-2 text-status-connected">●</span>}
</div>

{/* Time Range Slider - Responsive with better mobile positioning */}
<div className={`absolute bottom-4 sm:bottom-6 left-1/2 transform -translate-x-1/2 z-10 bg-zinc-800/95 backdrop-blur-sm px-3 sm:px-6 py-2 sm:py-4 rounded-lg text-white w-[95%] sm:w-auto sm:min-w-[400px] max-w-[500px] mobile-timeline-slider ${!isConnected ? "opacity-50 pointer-events-none" : ""}`}>
<div className="text-center mb-1 sm:mb-3">
<h4 className="text-xs font-semibold text-zinc-300 mb-1">Time Filter</h4>
</div>

<div className="relative">
{/* Hour markers - positioned to align with actual slider values */}
<div className="relative text-[9px] sm:text-xs text-zinc-400 mb-1 sm:mb-2 h-3 sm:h-4">
{/* -7d at position 1 = 0% */}
<span className="absolute left-0 transform -translate-x-1/2">-7d</span>
{/* -5d at position 49 = 28.7% */}
<span
className="absolute hidden sm:inline transform -translate-x-1/2"
style={{left: "28.7%"}}
>
-5d
</span>
{/* -3d at position 97 = 57.5% */}
<span
className="absolute transform -translate-x-1/2"
style={{left: "57.5%"}}
>
-3d
</span>
{/* -1d at position 145 = 86.3% */}
<span
className="absolute hidden sm:inline transform -translate-x-1/2"
style={{left: "86.3%"}}
>
-1d
</span>
{/* -12h at position 157 = 93.4% */}
<span
className="absolute transform -translate-x-1/2"
style={{left: "93.4%"}}
>
-12h
</span>
{/* -1h at position 168 = 100% */}
<span className="absolute right-0 transform translate-x-1/2">-1h</span>
</div>

{/* Slider - inverted so right side = fewer hours (more recent) */}
<input
type="range"
min="1"
max="168"
step="1"
value={169 - filter.timeRangeHours}
onChange={(e) => setFilter((prev) => ({...prev, timeRangeHours: 169 - parseInt(e.target.value)}))}
className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer slider"
disabled={!isConnected}
/>

{/* Current value indicator - responsive text */}
<div className="text-center">
<h3 className="text-xs font-semibold mt-2 sm:mt-4 text-white">Last {getTimeLabel(filter.timeRangeHours)}</h3>
</div>
</div>
</div>

{/* Map container with proper mobile height accounting for iOS safe areas */}
<div
className={`w-full h-full mobile-map-container ios-map-container ${!isConnected ? "grayscale opacity-50" : ""} relative`}
style={{
minHeight: "calc(100vh - 120px)", // Account for navbar + tab navigation + safe areas
maxHeight: "calc(100vh - 120px)",
}}
>
<Map
ref={mapRef}
initialViewState={viewport}
mapboxAccessToken={MAPBOX_TOKEN}
style={{width: "100%", height: "100%"}}
mapStyle="mapbox://styles/mapbox/dark-v11"
interactiveLayerIds={viewMode === "priority" ? ["alert-points"] : []}
interactive={isConnected}
dragPan={isConnected}
dragRotate={isConnected}
scrollZoom={isConnected}
keyboard={isConnected}
doubleClickZoom={isConnected}
onMove={handleViewportChange}
>
{/* Priority Mode - Circle Layer */}
{viewMode === "priority" && (
<Source
type="geojson"
data={alertsGeoJSON}
>
<Layer
id="alert-points"
type="circle"
paint={{
"circle-radius": ["case", ["==", ["get", "priority"], "critical"], 10, ["==", ["get", "priority"], "high"], 8, ["==", ["get", "priority"], "medium"], 6, 6],
"circle-color": ["case", ["==", ["get", "priority"], "critical"], "#dc2626", ["==", ["get", "priority"], "high"], "#ea580c", ["==", ["get", "priority"], "medium"], "#d97706", "#65a30d"],
"circle-opacity": 0.8,
"circle-stroke-width": 1,
"circle-stroke-color": "#ffffff",
}}
/>
</Source>
)}

{/* Source Mode - HTML Markers */}
{viewMode === "source" &&
filteredAlerts.map((alert) => (
<Marker
key={alert.id}
longitude={alert.coordinates.lng}
latitude={alert.coordinates.lat}
anchor="center"
onClick={() => handleMarkerClick(alert)}
>
<div
className={`cursor-pointer transition-transform hover:scale-110 flex items-center justify-center rounded-full ${getBackgroundIconColor(alert.source as "reddit" | "311" | "twitter")}`}
style={{
fontSize: `${getIconSize(alert.priority)}px`,
width: `${getIconSize(alert.priority) + 8}px`,
height: `${getIconSize(alert.priority) + 8}px`,
}}
>
{getSourceIcon(alert.source)}
</div>
</Marker>
))}

{/* Category Mode - HTML Markers */}
{viewMode === "category" &&
filteredAlerts.map((alert) => (
<Marker
key={alert.id}
longitude={alert.coordinates.lng}
latitude={alert.coordinates.lat}
anchor="center"
onClick={() => handleMarkerClick(alert)}
>
<div
className={`cursor-pointer transition-transform hover:scale-110 flex items-center justify-center rounded-full ${getCategoryBackgroundColor(alert.category || "general")}`}
style={{
fontSize: `${getIconSize(alert.priority)}px`,
width: `${getIconSize(alert.priority) + 8}px`,
height: `${getIconSize(alert.priority) + 8}px`,
}}
>
{getCategoryIcon(alert.category || "general")}
</div>
</Marker>
))}

{/* Popup for selected alert */}
{selectedAlert && (
<Popup
longitude={selectedAlert.coordinates.lng}
latitude={selectedAlert.coordinates.lat}
anchor="bottom"
onClose={() => {
console.log("❌ Closing popup");
setSelectedAlert(null);
setSelectedAlertLoading(false);
}}
closeButton={true}
closeOnClick={false}
className="max-w-[calc(100vw-40px)] sm:max-w-[360px]"
>
<div className="p-4 bg-zinc-800 border border-zinc-700 rounded-xl text-white shadow-xl relative">
{/* Loading Spinner Overlay */}
{selectedAlertLoading && (
<div className="absolute inset-0 bg-zinc-800/50 backdrop-blur-[1px] rounded-xl flex items-center justify-center z-10">
<div className="flex flex-col items-center gap-2 bg-zinc-900/90 px-4 py-3 rounded-lg">
<div className="animate-spin rounded-full h-6 w-6 border-2 border-white border-t-transparent"></div>
<span className="text-xs text-zinc-200 font-medium">Updating...</span>
</div>
</div>
)}

{/* Header */}
<div className="flex items-start gap-3 mb-3">
<span className="text-xl">{getSourceIcon(selectedAlert.source)}</span>
<div className="flex-1">
<h4 className="text-base font-semibold text-white leading-tight">{selectedAlert.title}</h4>
<span className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-1 ${selectedAlert.priority === "critical" ? "bg-red-500 text-white" : selectedAlert.priority === "high" ? "bg-orange-500 text-white" : selectedAlert.priority === "medium" ? "bg-yellow-500 text-black" : "bg-green-500 text-white"}`}>{selectedAlert.priority.toUpperCase()}</span>
</div>
</div>

{/* Description */}
<p className="text-sm text-zinc-300 mb-4 leading-relaxed">{selectedAlert.description}</p>

{/* Key-Value Pairs */}
<div className="space-y-2 mb-4">
<div className="flex justify-between items-center">
<span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Location</span>
<span className="text-sm text-white text-right">{[selectedAlert.neighborhood !== "Unknown" ? selectedAlert.neighborhood : null, selectedAlert.borough !== "Unknown" ? selectedAlert.borough : null].filter(Boolean).join(", ") || "Location not specified"}</span>
</div>

<div className="flex justify-between items-center">
<span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Category</span>
<span className="text-sm text-white capitalize flex items-center gap-1">
<span>{getCategoryIcon(selectedAlert.category || "general")}</span>
{selectedAlert.category || "General"}
</span>
</div>

<div className="flex justify-between items-center">
<span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Status</span>
<span className="text-sm text-white capitalize">{selectedAlert.status}</span>
</div>

<div className="flex justify-between items-center">
<span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Source</span>
<span className="text-sm text-white capitalize">{selectedAlert.source}</span>
</div>

<div className="flex justify-between items-center">
<span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Time</span>
<span className="text-sm text-white">{new Date(selectedAlert.timestamp).toLocaleString()}</span>
</div>
</div>

{/* Action Buttons */}
{selectedAlert.source !== "311" && (
<div className="space-y-2">
{/* Generate/View Report Button - always show unless disabled */}
{(() => {
// Check if this is a "View Report" scenario (completed investigation with report URL)
const isViewReportMode = selectedAlert.status === "resolved" && selectedAlert.reportUrl;

// Determine disabled state - "View Report" is never disabled by role
const isDisabledForInvestigation = isInvestigationDisabled(selectedAlert);
const isDisabledForRole = !isViewReportMode && user?.role === "viewer"; // Only restrict role for "Generate Report"
const isDisabled = isDisabledForInvestigation || isDisabledForRole;

// Determine button styling based on state
const getButtonClasses = () => {
if (isViewReportMode) {
// Always green and accessible for "View Report"
return "btn-success";
} else if (isDisabledForRole) {
// Halftone gray for viewer users trying to generate reports
return "bg-gray-500 text-gray-300 cursor-not-allowed opacity-60";
} else if (isDisabledForInvestigation) {
// Yellow for investigation-level restrictions (existing behavior)
return "bg-yellow-600 cursor-not-allowed text-white";
} else {
// Default primary state for "Generate Report"
return "btn-primary";
}
};

return (
<button
className={`btn w-full text-sm ${getButtonClasses()}`}
onClick={() => handleReportButtonClick(selectedAlert)}
disabled={isDisabled}
>
{getReportButtonContent(selectedAlert)}
</button>
);
})()}

{/* View Trace Button - only show if traceId exists */}
{selectedAlert.traceId && (
<button
className="btn btn-secondary w-full text-sm"
onClick={() => handleViewTrace(selectedAlert)}
disabled={!isConnected}
>
View Investigation Trace
</button>
)}
</div>
)}
</div>
</Popup>
)}
</Map>
</div>

{/* Agent Trace Modal */}
<AgentTraceModal
isOpen={traceModal.isOpen}
onClose={() => setTraceModal({isOpen: false, traceId: "", alertTitle: ""})}
traceId={traceModal.traceId}
alertTitle={traceModal.alertTitle}
/>
</div>
);
};

export default MapView;
