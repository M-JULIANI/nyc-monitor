import { useState, useRef, useEffect, useMemo } from "react";
import Map, { Layer, Source, Popup, Marker } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { Alert } from "../types";
import { useAlerts } from "../contexts/AlertsContext";
import { useMapState } from "../contexts/MapStateContext";
import { useMobile } from "../pages/Home";
import Spinner from "./Spinner";
import AgentTraceModal from "./AgentTraceModal";
import PerformancePanel from "./PerformancePanel";
import { useAuth } from "@/contexts/AuthContext";
import { isDevelopmentMode } from "../utils/devMode";

const MAPBOX_TOKEN = "pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA";
const PERFORMANCE_THRESHOLD = 1000;
// Configure mapbox-gl for development environment
if (typeof window !== "undefined") {
  // Set mapbox access token globally via ES import
  import("mapbox-gl").then((mapboxgl) => {
    if (mapboxgl.default) {
      mapboxgl.default.accessToken = MAPBOX_TOKEN;
      console.log("✅ Mapbox access token set via ES import");
    }
  }).catch((importError) => {
    console.error("❌ ES import failed:", importError);
  });
}

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
  const { alerts, error, isLoading, generateReport, getSingleAlert } = useAlerts();
  const { user } = useAuth();
  const { isMobile } = useMobile();
  
  // Performance monitoring (dev mode only)
  const isDevMode = isDevelopmentMode();


  const isConnected = !isLoading;
  const isMapInteractive = true;

  const { viewport, setViewport, filter, setFilter, viewMode, setViewMode, displayMode, setDisplayMode } = useMapState();
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [selectedAlertLoading, setSelectedAlertLoading] = useState(false);
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(false);
  const [traceModal, setTraceModal] = useState<{ isOpen: boolean; traceId: string; alertTitle: string }>({
    isOpen: false,
    traceId: "",
    alertTitle: "",
  });

  // Performance guard state
  const [isAutoHeatmapMode, setIsAutoHeatmapMode] = useState(false);
  const [showPerformanceNotification, setShowPerformanceNotification] = useState(false);
  const autoSwitchDebounceTimer = useRef<NodeJS.Timeout | null>(null);

  // Track if we should auto-fit to alerts (only on first load or filter changes, disabled on mobile)
  const [shouldAutoFit, setShouldAutoFit] = useState(!isMobile);

  // Calculate bounds for all visible alerts
  const calculateAlertBounds = (alerts: Alert[]) => {
    if (alerts.length === 0) return null;

    let minLat = Infinity;
    let maxLat = -Infinity;
    let minLng = Infinity;
    let maxLng = -Infinity;

    alerts.forEach((alert) => {
      const { lat, lng } = alert.coordinates;
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

  // Function to check if an alert is within the current viewport bounds
  const isAlertInViewport = (alert: Alert, bounds: any) => {
    if (!bounds) return true; // If no bounds, show all alerts
    
    const { lat, lng } = alert.coordinates;
    const { north, south, east, west } = bounds;
    
    // Handle longitude wrapping around antimeridian
    let withinLongitude;
    if (west <= east) {
      withinLongitude = lng >= west && lng <= east;
    } else {
      // Longitude wraps around (e.g., spans -180/180 line)
      withinLongitude = lng >= west || lng <= east;
    }
    
    return lat >= south && lat <= north && withinLongitude;
  };

  // Get current map bounds for viewport filtering
  const getCurrentBounds = () => {
    if (!mapRef.current) return null;
    try {
      const map = mapRef.current.getMap();
      const bounds = map.getBounds();
      return {
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest()
      };
    } catch (error) {
      console.warn("Error getting map bounds:", error);
      return null;
    }
  };

  // Filter alerts to only those visible in current viewport
  const visibleAlerts = useMemo(() => {
    const startTime = performance.now();
    const bounds = getCurrentBounds();
    if (!bounds) return filteredAlerts; // Fallback to all filtered alerts if bounds unavailable
    
    const visible = filteredAlerts.filter(alert => isAlertInViewport(alert, bounds));
    const filterTime = performance.now() - startTime;
    
    // Log performance improvement for significant datasets
    if (filteredAlerts.length > 1000) {
      const reductionPercentage = ((1 - visible.length / filteredAlerts.length) * 100).toFixed(1);
    }
    
    return visible;
  }, [filteredAlerts, viewport]); // Re-filter when viewport changes

  // Update map bounds when alerts change, but only if we should auto-fit (desktop only)
  useEffect(() => {
    if (mapRef.current && filteredAlerts.length > 0 && shouldAutoFit && !isMobile) {
      const bounds = calculateAlertBounds(filteredAlerts);
      if (bounds) {
        try {
          mapRef.current.fitBounds(bounds, {
            padding: { top: 100, bottom: 150, left: 300, right: 100 }, // Extra bottom padding for slider
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
  }, [filteredAlerts, shouldAutoFit, isMobile, setViewport]); // Re-run when filtered alerts change

  // Reset auto-fit when filters change (desktop only)
  useEffect(() => {
    if (!isMobile) {
      setShouldAutoFit(true);
    }
  }, [filter, isMobile]);

  // Performance guard: Auto-switch to heatmap when too many alerts are visible
  useEffect(() => {
    const DEBOUNCE_DELAY = 50; // ms

    // Clear existing timer
    if (autoSwitchDebounceTimer.current) {
      clearTimeout(autoSwitchDebounceTimer.current);
    }

    // Debounce the performance check to prevent rapid switching during zoom/pan
    const timer = setTimeout(() => {
      const shouldUseHeatmap = visibleAlerts.length > PERFORMANCE_THRESHOLD;
      
      if (shouldUseHeatmap && displayMode !== "heatmap") {
        console.log(`🚀 Performance guard: Auto-switching to heatmap mode (${visibleAlerts.length} alerts visible)`);
        setDisplayMode("heatmap");
        setIsAutoHeatmapMode(true);
        
        // Show notification briefly
        setShowPerformanceNotification(true);
        setTimeout(() => setShowPerformanceNotification(false), 3000);
      } else if (!shouldUseHeatmap && isAutoHeatmapMode) {
        // Only auto-switch back if we're in auto-heatmap mode
        console.log(`🔄 Performance guard: Switching back to dots mode (${visibleAlerts.length} alerts visible)`);
        setDisplayMode("dots");
        setIsAutoHeatmapMode(false);
      }
    }, DEBOUNCE_DELAY);

    autoSwitchDebounceTimer.current = timer;

    // Cleanup timer on unmount
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [visibleAlerts.length, displayMode, isAutoHeatmapMode, setDisplayMode]);

  // Clean up timer when component unmounts
  useEffect(() => {
    return () => {
      if (autoSwitchDebounceTimer.current) {
        clearTimeout(autoSwitchDebounceTimer.current);
      }
    };
  }, []);

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
        return 12;
      case "high":
        return 10;
      case "medium":
        return 6;
      case "low":
        return 2;
      default:
        return 1;
    }
  };

  const getTimeLabel = (hours: number): string => {
    if (hours === 1) return "1 hour";
    if (hours < 24) return `${hours} hours`;
    if (hours === 24) return "1 day";
    if (hours < 168) return `${Math.round(hours / 24)} days`;
    if (hours < 720) return `${Math.round(hours / 168)} weeks`; // Less than 30 days
    if (hours < 2160) return `${Math.round(hours / 720)} months`; // Less than 90 days
    return `${Math.round(hours / 720)} months`; // 720 hours = 30 days
  };

  // Create GeoJSON for visible alert points (viewport-filtered for performance)
  const visibleAlertsGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: visibleAlerts.map((alert) => ({
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
        category: alert.category || "general",
        // Add weight property for heatmap intensity based on priority
        weight: alert.priority === "critical" ? 4 : alert.priority === "high" ? 3 : alert.priority === "medium" ? 2 : 1,
        color: `priority-${alert.priority}`,
      },
    })),
  };

  const getHeatmapColors = () => {
        return [
          "rgba(0,0,255,0)",       // Transparent
          "rgba(75,0,130,0.3)",    // Indigo
          "rgba(0,128,255,0.5)",   // Blue
          "rgba(0,255,127,0.7)",   // Spring green
          "rgba(255,255,0,0.9)",   // Yellow
          "rgba(255,140,0,1)"      // Orange
        ];

  };

  const handleMarkerClick = (alert: Alert) => {
    console.log("🖱️ MARKER CLICKED! Alert ID:", alert.id);
    console.log("🖱️ isConnected:", isConnected);
    console.log("🖱️ isMapInteractive:", isMapInteractive);

    if (!isMapInteractive) {
      console.log("🖱️ Map not interactive, returning early");
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
      const offsetInDegrees =
        (popupOffset / containerHeight) * (map.getBounds().getNorth() - map.getBounds().getSouth());

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

    // Step 2: Set loading state
    console.log("🎯 Setting loading state to true");
    setSelectedAlertLoading(true);

    // Step 3: Start hydrated alert fetch in background (non-blocking)
    console.log("🎯 Starting hydrated alert fetch...");
    setTimeout(() => {
      console.log("🔄 Fetching hydrated alert data for:", alert.id);

      getSingleAlert(alert.id)
        .then((result: { success: boolean; message: string; alert?: Alert }) => {
          console.log("📥 Hydrated alert fetch completed for:", alert.id, result);
          if (result.success && result.alert) {
            console.log("✅ Updating with hydrated data");
            setSelectedAlert(result.alert);
          } else {
            console.warn("⚠️ Hydrated fetch failed, keeping cached data");
          }
        })
        .catch((err: Error) => {
          console.warn("⚠️ Hydrated fetch error, keeping cached data:", err);
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
    setSelectedAlert((prev) => (prev ? { ...prev, status: "investigating" as const } : null));
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
            : null,
        );
      } else {
        console.error("Failed to generate report:", result.message);
        // Revert the status on failure
        setSelectedAlert((prev) => (prev ? { ...prev, status: "active" as const } : null));
        window.alert(`Failed to generate report: ${result.message}`);
      }
    } catch (err) {
      console.error("Error generating report:", err);
      // Revert the status on error
      setSelectedAlert((prev) => (prev ? { ...prev, status: "active" as const } : null));
      window.alert("Failed to generate report");
    } finally {
      setSelectedAlertLoading(false);
    }
  };

  const isInvestigationDisabled = (alert: Alert) => {
    // Button should be disabled when investigating or when not connected to network
    return !isConnected || alert.status === "investigating";
  };

  return (
    <div className="relative w-full h-full">
      {/* Inject custom slider styles */}
      <style dangerouslySetInnerHTML={{ __html: sliderStyles }} />

      {/* Connection Status */}
      {error && (
        <div className="absolute top-4 right-4 z-20 bg-status-error/95 px-4 py-2 rounded-lg text-white text-sm">
          Error: {error}
        </div>
      )}

      {!isConnected && !error && (
        <div className="absolute top-4 right-4 z-20 bg-status-connecting/95 px-4 py-2 rounded-lg text-white text-sm">
          Connecting to alert stream...
        </div>
      )}

      {/* Performance Auto-Switch Notification */}
      {showPerformanceNotification && (
        <div className="absolute top-16 right-4 z-20 bg-orange-500/95 px-4 py-2 rounded-lg text-white text-sm shadow-lg animate-in slide-in-from-right duration-300">
          <div className="flex items-center gap-2">
            <span>🚀</span>
            <span>Switched to heatmap for performance ({visibleAlerts.length} alerts)</span>
          </div>
        </div>
      )}

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
        className={`absolute top-4 left-4 z-20 bg-zinc-800/95 backdrop-blur-sm p-3 rounded-lg text-white hover:bg-zinc-700 transition-all duration-300 ease-in-out touch-manipulation ${
          !isMapInteractive ? "opacity-50 pointer-events-none" : ""
        }`}
        disabled={!isMapInteractive}
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
        <div
          className={`absolute top-16 left-4 z-10 bg-zinc-800/95 backdrop-blur-sm p-4 rounded-lg text-white min-w-[200px] w-[calc(100vw-32px)] sm:w-auto sm:max-w-[280px] transition-all duration-300 ease-in-out ${
            !isMapInteractive ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          <h3 className="text-xs font-semibold mb-2 text-zinc-300">Filters</h3>

          <div className="mb-2">
            <label className="block text-xs mb-1 text-zinc-300">Priority</label>
            <select
              value={filter.priority}
              onChange={(e) => setFilter((prev) => ({ ...prev, priority: e.target.value }))}
              className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-xs"
              disabled={!isMapInteractive}
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
              onChange={(e) => setFilter((prev) => ({ ...prev, source: e.target.value }))}
              className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-xs"
              disabled={!isMapInteractive}
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
              onChange={(e) => setFilter((prev) => ({ ...prev, status: e.target.value }))}
              className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-xs"
              disabled={!isMapInteractive}
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          {/* Display Mode Toggle */}
          <div className="border-t border-zinc-700 pt-3 mb-4">
            <h4 className="text-xs font-semibold mb-2 text-zinc-300">Display Type</h4>
            <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                <input
                  type="radio"
                  name="displayMode"
                  value="heatmap"
                  checked={displayMode === "heatmap"}
                  onChange={(e) => {
                    setDisplayMode(e.target.value as "dots" | "heatmap");
                    // If user manually selects heatmap, clear auto-mode
                    if (isAutoHeatmapMode) {
                      setIsAutoHeatmapMode(false);
                    }
                  }}
                  className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                  disabled={!isMapInteractive}
                />
                <span>Heatmap</span>
                {isAutoHeatmapMode && (
                  <span className="text-orange-400 text-[9px]">(auto)</span>
                )}
              </label>
              {/* Only show dots option when under performance threshold */}
              {visibleAlerts.length <= PERFORMANCE_THRESHOLD && (
                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="radio"
                    name="displayMode"
                    value="dots"
                    checked={displayMode === "dots"}
                    onChange={(e) => setDisplayMode(e.target.value as "dots" | "heatmap")}
                    className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                    disabled={!isMapInteractive}
                  />
                  <span>Dots</span>
                </label>
              )}
            </div>
            {displayMode === "heatmap" && (
              <p className="text-[9px] text-zinc-500 mt-2">
                Shows alert density. Zoom in/out to see different intensities.
                {isAutoHeatmapMode && (
                  <span className="block text-orange-400 mt-1">
                    Auto-enabled due to {visibleAlerts.length} visible alerts (greater than 1000).
                  </span>
                )}
              </p>
            )}
          </div>

          {/* View Mode Toggles - Only show when in dots mode */}
          {displayMode === "dots" && (
            <div className="border-t border-zinc-700 pt-3 mb-4">
              <h4 className="text-xs font-semibold mb-2 text-zinc-300">Dot Style</h4>
              <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                <input
                  type="radio"
                  name="viewMode"
                  value="category"
                  checked={viewMode === "category"}
                  onChange={(e) => setViewMode(e.target.value as "priority" | "source" | "category")}
                  className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                  disabled={!isMapInteractive}
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
                  disabled={!isMapInteractive}
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
                  disabled={!isMapInteractive}
                />
                <span>By Priority</span>
                <span className="text-zinc-500 hidden sm:inline">(colored circles)</span>
              </label>
            </div>
            </div>
          )}

          {/* Legend - Only show when in dots mode */}
          {displayMode === "dots" && (
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
          )}

          {/* Heatmap Legend - Only show when in heatmap mode */}
          {displayMode === "heatmap" && (
            <div className="border-t border-zinc-700 pt-3">
              <h4 className="text-xs font-semibold mb-2 text-zinc-300">Heatmap Legend</h4>
              <div className="flex items-center gap-2 mb-2">
              <div className="flex w-full text-[9px] text-zinc-400 justify-between">
                <span>Low</span>
                <div 
                  className="w-24 h-3 rounded"
                  style={{
                    background: `linear-gradient(to right, ${getHeatmapColors()[0]}, ${getHeatmapColors()[2]}, ${getHeatmapColors()[4]}, ${getHeatmapColors()[5]})`
                  }}
                />
                  <span>High</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Alert Count - Mobile responsive */}
      <div
        className={`absolute top-4 right-4 z-10 bg-zinc-800/95 px-3 sm:px-4 py-2 rounded-lg text-white text-xs sm:text-sm ${
          !isMapInteractive ? "opacity-50" : ""
        }`}
      >
        <div className="flex flex-col gap-1 text-right">
          <div className="flex items-center justify-end gap-2">
            <span className="hidden sm:inline">
              {visibleAlerts.length.toLocaleString()} alerts visible
            </span>
            <span className="sm:hidden">
              {visibleAlerts.length.toLocaleString()}
            </span>
            {isConnected && <span className="text-status-connected">●</span>}
          </div>
          <div className="text-zinc-400 text-[10px] sm:text-xs">
            <span className="hidden sm:inline">
              {alerts.length.toLocaleString()} total
            </span>
            <span className="sm:hidden">
              {alerts.length.toLocaleString()} total
            </span>
          </div>
        </div>
      </div>

      {/* Time Range Slider - Responsive with better mobile positioning */}
      <div
        className={`absolute bottom-4 sm:bottom-6 left-1/2 transform -translate-x-1/2 z-10 bg-zinc-800/95 backdrop-blur-sm px-3 sm:px-6 py-2 sm:py-4 rounded-lg text-white w-[95%] sm:w-auto sm:min-w-[400px] max-w-[500px] mobile-timeline-slider ${
          !isMapInteractive ? "opacity-50 pointer-events-none" : ""
        }`}
      >
        <div className="text-center mb-1 sm:mb-3">
          <h4 className="text-xs font-semibold text-zinc-300 mb-1">Time Filter</h4>
        </div>

        <div className="relative">
          {/* Time markers - positioned to align with actual slider values for 6 months */}
          <div className="relative text-[9px] sm:text-xs text-zinc-400 mb-1 sm:mb-2 h-3 sm:h-4">
            {/* -6mo at position 1 = 0% */}
            <span className="absolute left-0 transform -translate-x-1/2">-6mo</span>
            {/* -4mo at position ~1441 = 33.3% */}
            <span className="absolute hidden sm:inline transform -translate-x-1/2" style={{ left: "33.3%" }}>
              -4mo
            </span>
            {/* -2mo at position ~2881 = 66.7% */}
            <span className="absolute transform -translate-x-1/2" style={{ left: "66.7%" }}>
              -2mo
            </span>
            {/* -1mo at position ~3601 = 83.3% */}
            <span className="absolute hidden sm:inline transform -translate-x-1/2" style={{ left: "83.3%" }}>
              -1mo
            </span>
            {/* -1w at position ~4153 = 96.1% */}
            <span className="absolute transform -translate-x-1/2" style={{ left: "96.1%" }}>
              -1w
            </span>
            {/* -1h at position 4320 = 100% */}
            <span className="absolute right-0 transform translate-x-1/2">-1h</span>
          </div>

          {/* Slider - inverted so right side = fewer hours (more recent) */}
          <input
            type="range"
            min="1"
            max="4320"
            step="1"
            value={4321 - filter.timeRangeHours}
            onChange={(e) => setFilter((prev) => ({ ...prev, timeRangeHours: 4321 - parseInt(e.target.value) }))}
            className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer slider"
            disabled={!isMapInteractive}
          />

          {/* Current value indicator - responsive text */}
          <div className="text-center">
            <h3 className="text-xs font-semibold mt-2 sm:mt-4 text-white">
              Last {getTimeLabel(filter.timeRangeHours)}
            </h3>
          </div>
        </div>
      </div>

      {/* Map container with proper mobile height accounting for iOS safe areas */}
      <div
        className={`w-full h-full mobile-map-container ios-map-container ${
          !isConnected ? "grayscale opacity-50" : ""
        } relative`}
        style={{
          minHeight: "calc(100vh - 120px)", // Account for navbar + tab navigation + safe areas
          maxHeight: "calc(100vh - 120px)",
          touchAction: "manipulation", // Enable touch panning and pinch zoom for map interaction
        }}
      >
          <Map
            ref={mapRef}
            initialViewState={viewport}
            mapboxAccessToken={MAPBOX_TOKEN}
            style={{ width: "100%", height: "100%" }}
            mapStyle="mapbox://styles/mapbox/dark-v11"
            interactiveLayerIds={
              displayMode === "heatmap" 
                ? ["alert-heatmap-points"] 
                : displayMode === "dots" && viewMode === "priority" 
                  ? ["alert-points"] 
                  : []
            }
            interactive={isMapInteractive}
            dragPan={isMapInteractive}
            dragRotate={isMapInteractive}
            scrollZoom={isMapInteractive}
            keyboard={isMapInteractive}
            doubleClickZoom={isMapInteractive}
            onMove={handleViewportChange}
            onError={(error) => {
              console.error("❌ Map runtime error:", error);
            }}
          >
          {/* Heatmap Layer - Show when in heatmap mode */}
          {displayMode === "heatmap" && (
            <Source type="geojson" data={visibleAlertsGeoJSON}>
              <Layer
                id="alert-heatmap"
                type="heatmap"
                paint={{
                  // Increase the heatmap weight based on frequency and property value
                  "heatmap-weight": [
                    "interpolate",
                    ["linear"],
                    ["get", "weight"],
                    0, 0.1,
                    1, 0.3,
                    2, 0.6,
                    3, 0.8,
                    4, 1
                  ],
                  // Increase the heatmap color weight weight by zoom level
                  // heatmap-intensity is a multiplier on top of heatmap-weight
                  "heatmap-intensity": [
                    "interpolate",
                    ["exponential", 1.5],  // Gentle acceleration for smoother intensity changes
                    ["zoom"],
                    0, 0.6,
                    8, 1.2,
                    16, 2.5
                  ],
                  // Color ramp for heatmap.  Domain is 0 (low) to 1 (high).
                  // Begin color ramp at 0-stop with a 0-transparancy color
                  // to create a blur-like effect.
                  "heatmap-color": [
                    "interpolate",
                    ["linear"],
                    ["heatmap-density"],
                    0, "rgba(33,102,172,0)",
                    0.2, getHeatmapColors()[1],
                    0.4, getHeatmapColors()[2],
                    0.6, getHeatmapColors()[3],
                    0.8, getHeatmapColors()[4],
                    1, getHeatmapColors()[5]
                  ],
                  // Adjust the heatmap radius by zoom level - exponential for natural zoom scaling
                  "heatmap-radius": [
                    "interpolate",
                    ["exponential", 2],  // Base 2 = doubles with each major zoom change
                    ["zoom"],
                    0, 3,       // Very small when zoomed way out
                    8, 8,       // Small for city overview
                    12, 20,     // Medium for neighborhood view
                    16, 45      // Large for street-level detail
                  ],
                  // Keep heatmap visible across all zoom levels
                  "heatmap-opacity": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    0, 0.8,
                    22, 0.8
                  ]
                }}
              />
              {/* Optional: Add small circle layer for very high zoom levels */}
              <Layer
                id="alert-heatmap-points"
                type="circle"
                paint={{
                  "circle-radius": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    14, 0,
                    16, 5,      // Increased from 2 to 5
                    18, 8       // Increased from 3 to 8
                  ],
                  "circle-color": getHeatmapColors()[5],
                  "circle-stroke-color": "white",
                  "circle-stroke-width": 0.5,
                  "circle-opacity": [
                    "interpolate",
                    ["cubic-bezier", 0.25, 0.46, 0.45, 0.94],  // Smooth ease-out curve
                    ["zoom"],
                    14, 0,
                    16, 0.7,
                    18, 1
                  ]
                }}
              />
            </Source>
          )}

          {/* Priority Mode - Circle Layer */}
          {displayMode === "dots" && viewMode === "priority" && (
            <Source type="geojson" data={visibleAlertsGeoJSON}>
              <Layer
                id="alert-points"
                type="circle"
                paint={{
                  "circle-radius": [
                    "case",
                    ["==", ["get", "priority"], "critical"],
                    10,
                    ["==", ["get", "priority"], "high"],
                    8,
                    ["==", ["get", "priority"], "medium"],
                    6,
                    6,
                  ],
                  "circle-color": [
                    "case",
                    ["==", ["get", "priority"], "critical"],
                    "#dc2626",
                    ["==", ["get", "priority"], "high"],
                    "#ea580c",
                    ["==", ["get", "priority"], "medium"],
                    "#d97706",
                    "#65a30d",
                  ],
                  "circle-opacity": 0.8,
                  "circle-stroke-width": 1,
                  "circle-stroke-color": "#ffffff",
                }}
              />
            </Source>
          )}

          {/* Source Mode - HTML Markers */}
          {displayMode === "dots" && viewMode === "source" &&
            visibleAlerts.map((alert) => (
              <Marker
                key={alert.id}
                longitude={alert.coordinates.lng}
                latitude={alert.coordinates.lat}
                anchor="center"
                onClick={() => handleMarkerClick(alert)}
              >
                <div
                  className={`cursor-pointer transition-transform hover:scale-110 flex items-center justify-center rounded-full ${getBackgroundIconColor(
                    alert.source as "reddit" | "311" | "twitter",
                  )}`}
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
          {displayMode === "dots" && viewMode === "category" &&
            visibleAlerts.map((alert) => (
              <Marker
                key={alert.id}
                longitude={alert.coordinates.lng}
                latitude={alert.coordinates.lat}
                anchor="center"
                onClick={() => handleMarkerClick(alert)}
              >
                <div
                  className={`cursor-pointer transition-transform hover:scale-110 flex items-center justify-center rounded-full ${getCategoryBackgroundColor(
                    alert.category || "general",
                  )}`}
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
                    <span
                      className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-1 ${
                        selectedAlert.priority === "critical"
                          ? "bg-red-500 text-white"
                          : selectedAlert.priority === "high"
                          ? "bg-orange-500 text-white"
                          : selectedAlert.priority === "medium"
                          ? "bg-yellow-500 text-black"
                          : "bg-green-500 text-white"
                      }`}
                    >
                      {selectedAlert.priority.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-sm text-zinc-300 mb-4 leading-relaxed">{selectedAlert.description}</p>

                {/* Key-Value Pairs */}
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Location</span>
                    <span className="text-sm text-white text-right">
                      {[
                        selectedAlert.neighborhood !== "Unknown" ? selectedAlert.neighborhood : null,
                        selectedAlert.borough !== "Unknown" ? selectedAlert.borough : null,
                      ]
                        .filter(Boolean)
                        .join(", ") || "Location not specified"}
                    </span>
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
        onClose={() => setTraceModal({ isOpen: false, traceId: "", alertTitle: "" })}
        traceId={traceModal.traceId}
        alertTitle={traceModal.alertTitle}
      />

      {/* Performance Panel - Dev Mode Only */}
      {isDevMode && (
        <PerformancePanel />
      )}
    </div>
  );
};

export default MapView;
