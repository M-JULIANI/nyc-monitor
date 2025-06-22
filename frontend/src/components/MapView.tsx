import { useState, useRef, useEffect, useMemo } from 'react';
import Map, { Layer, Source, Popup, Marker } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Alert } from '../types';
import { useAlerts } from '../contexts/AlertsContext';
import { useMapState } from '../contexts/MapStateContext';
import Spinner from './Spinner';
import AgentTraceModal from './AgentTraceModal';

const MAPBOX_TOKEN = 'pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA';

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
`;

const MapView: React.FC = () => {
  const mapRef = useRef<any>(null);
  //const markerClickedRef = useRef(false);
  const { alerts, error, isLoading, generateReport, refetchAlert } = useAlerts();
  const isConnected = !isLoading;
  const { viewport, setViewport, filter, setFilter, viewMode, setViewMode } = useMapState();
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [selectedAlertLoading, setSelectedAlertLoading] = useState(false);
  const [traceModal, setTraceModal] = useState<{ isOpen: boolean; traceId: string; alertTitle: string }>({
    isOpen: false,
    traceId: '',
    alertTitle: ''
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

    alerts.forEach(alert => {
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
      [maxLng + padding, maxLat + padding]  // Northeast corner
    ];

    return paddedBounds;
  };

  // Filter alerts based on current filter settings
  const filteredAlerts = useMemo(() => {
    //console.log('Filtering with timeRangeHours:', filter.timeRangeHours);
    
    const filtered = alerts.filter(alert => {
      // Priority filter
      if (filter.priority !== 'all' && alert.priority !== filter.priority) return false;
      
      // Source filter
      if (filter.source !== 'all' && alert.source !== filter.source) return false;
      
      // Status filter
      if (filter.status !== 'all' && alert.status !== filter.status) return false;
      
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
            padding: { top: 100, bottom: 150, left: 300, right: 100 }, // Extra bottom padding for slider
            duration: 1000, // Smooth animation
            maxZoom: 16 // Don't zoom in too close
          });
          
          // Update viewport state after fitBounds completes
          setTimeout(() => {
            if (mapRef.current) {
              const newViewState = mapRef.current.getMap().getCenter();
              const newZoom = mapRef.current.getMap().getZoom();
              setViewport({
                longitude: newViewState.lng,
                latitude: newViewState.lat,
                zoom: newZoom
              });
            }
          }, 1100); // Wait slightly longer than the animation duration
          
          // Disable auto-fit after first automatic fit
          setShouldAutoFit(false);
        } catch (error) {
          console.warn('Error fitting bounds:', error);
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
      zoom: evt.viewState.zoom
    });
  };

  const getSourceIcon = (source: string): string => {
    switch (source) {
      case 'reddit': return '👽'; // Reddit alien mascot
      case '311': return '📞';
      case 'twitter': return '🐦';
      default: return '📍';
    }
  };

  const getCategoryIcon = (category: string): string => {
    switch (category) {
      case 'infrastructure': return '🔧'; // Wrench for infrastructure
      case 'emergency': return '🚨'; // Emergency siren
      case 'transportation': return '🚗'; // Car for transportation
      case 'events': return '🎪'; // Circus tent for events
      case 'safety': return '🛡️'; // Shield for safety
      case 'environment': return '🌿'; // Leaf for environment
      case 'housing': return '🏠'; // House for housing
      case 'general': return '📋'; // Clipboard for general
      default: return '📍'; // Default pin
    }
  };

  const getBackgroundIconColor = (source: 'reddit' | '311' | 'twitter'): string => {
    switch (source) {
      case 'reddit': return 'bg-orange-400';
      case '311': return 'bg-yellow-400';
      case 'twitter': return 'bg-blue-400';
      default: return 'bg-gray-400';
    }
  };

  const getCategoryBackgroundColor = (category: string): string => {
    switch (category) {
      case 'infrastructure': return 'bg-blue-500'; // Blue for infrastructure
      case 'emergency': return 'bg-red-500'; // Red for emergency
      case 'transportation': return 'bg-purple-500'; // Purple for transportation
      case 'events': return 'bg-pink-500'; // Pink for events
      case 'safety': return 'bg-orange-500'; // Orange for safety
      case 'environment': return 'bg-green-500'; // Green for environment
      case 'housing': return 'bg-yellow-500'; // Yellow for housing
      case 'general': return 'bg-gray-500'; // Gray for general
      default: return 'bg-gray-400';
    }
  };

  const getIconSize = (priority: string): number => {
    switch (priority) {
      case 'critical': return 18;
      case 'high': return 12;
      case 'medium': return 8;
      case 'low': return 4;
      default: return 8;
    }
  };


  // Create GeoJSON for alert points (only used in priority mode)
  const alertsGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: filteredAlerts.map(alert => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [alert.coordinates.lng, alert.coordinates.lat]
      },
      properties: {
        id: alert.id,
        title: alert.title,
        priority: alert.priority,
        source: alert.source,
        color: `priority-${alert.priority}`
      }
    }))
  };

  const handleMarkerClick = (alert: Alert) => {
    console.log('🖱️ MARKER CLICKED! Alert ID:', alert.id);
    console.log('🖱️ isConnected:', isConnected);
   // console.log('🖱️ Alert object:', alert);
    
    if (!isConnected) {
      console.log('🖱️ Not connected, returning early');
      return;
    }
    
    console.log('🖱️ Calling handleAlertSelection...');
    handleAlertSelection(alert);
  };

  const handleAlertSelection = (alert: Alert) => {
    console.log('🎯 HANDLE ALERT SELECTION CALLED! Alert ID:', alert.id);
    
    // Step 1: Set the alert immediately for instant popup
    console.log('🎯 Setting selectedAlert to:', alert);
    setSelectedAlert(alert);

    // Step 1.5: Fly to center the marker on the map
    if (mapRef.current) {
      console.log('🗺️ Flying to marker coordinates:', alert.coordinates);
      mapRef.current.flyTo({
        center: [alert.coordinates.lng, alert.coordinates.lat],
        duration: 800, // Smooth 800ms animation
        essential: true // This animation is essential and will not be interrupted
      });
      
      // Update viewport state after flyTo completes
      setTimeout(() => {
        if (mapRef.current) {
          const newViewState = mapRef.current.getMap().getCenter();
          const newZoom = mapRef.current.getMap().getZoom();
          setViewport({
            longitude: newViewState.lng,
            latitude: newViewState.lat,
            zoom: newZoom
          });
        }
      }, 850); // Wait slightly longer than the animation duration
    }

    if(alert.source === "311") {
      console.log('🎯 311 alert, returning early');
      return;
    }
    
    // Step 2: Set loading state 
    console.log('🎯 Setting loading state to true');
    setSelectedAlertLoading(true);
    
    // Step 3: Start refetch in background (non-blocking)
    console.log('🎯 Starting background refetch...');
    setTimeout(() => {
      console.log('🔄 Refetching alert data for:', alert.id);
      
      refetchAlert(alert.id)
        .then(result => {
          console.log('📥 Refetch completed for:', alert.id, result);
          if (result.success && result.alert) {
            console.log('✅ Updating with fresh data');
            setSelectedAlert(result.alert);
          } else {
            console.warn('⚠️ Refetch failed, keeping cached data');
          }
        })
        .catch(err => {
          console.warn('⚠️ Refetch error, keeping cached data:', err);
        })
        .finally(() => {
          console.log('🏁 Clearing loading state');
          setSelectedAlertLoading(false);
        });
    }, 50); // Small delay to ensure UI updates first
  };

  const handleGenerateReport = async (alert: Alert) => {
    if (!isConnected) return;
    
    try {
      const result = await generateReport(alert.id);
      if (result.success) {
        console.log('Report generation started:', result.investigationId);
        // The UI will update automatically via polling
      } else {
        window.alert(`Failed to generate report: ${result.message}`);
      }
    } catch (err) {
      console.error('Error generating report:', err);
      window.alert('Failed to generate report');
    }
  };

  const handleViewTrace = (alert: Alert) => {
    if (alert.traceId) {
      setTraceModal({
        isOpen: true,
        traceId: alert.traceId,
        alertTitle: alert.title
      });
    }
  };

  const getReportButtonContent = (alert: Alert) => {
    if (alert.status === 'investigating') {
      return (
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
          <span>Investigating...</span>
        </div>
      );
    }
    
    // Only show "View Report" if BOTH status is resolved AND reportUrl exists
    if (alert.status === 'resolved' && alert.reportUrl) {
      return 'View Report';
    }
    
    // Default to "Generate Report" for all other cases
    return 'Generate Report';
  };

  const handleReportButtonClick = async (alert: Alert) => {
    // Enhanced status checking with double-click prevention
    console.log(`Report button clicked for alert ${alert.id}:`, {
      status: alert.status,
      reportUrl: alert.reportUrl,
      investigationId: alert.investigationId,
      traceId: alert.traceId
    });

    if (alert.status === 'investigating') {
      // Do nothing - investigation in progress, button should be disabled
      console.log(`Investigation in progress for alert ${alert.id}, button click ignored`);
      return;
    }
    
    // STRICT CHECK: Only open report if BOTH conditions are true
    if (alert.status === 'resolved' && alert.reportUrl) {
      // Open report in new tab
      console.log(`Opening existing report for alert ${alert.id}: ${alert.reportUrl}`);
      window.open(alert.reportUrl, '_blank');
      return; // Early return to prevent fallback
    }
    
    // Generate new report for all other cases
    console.log(`Generating new report for alert ${alert.id} - Status: ${alert.status}, ReportUrl: ${alert.reportUrl}`);
    await handleGenerateReport(alert);
  };

  const isInvestigationDisabled = (alert: Alert) => {
    // Button should be disabled when investigating or when not connected
    return !isConnected || alert.status === 'investigating';
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

      {/* Disconnected State Overlay */}
      {!isConnected && (
        <>
          <div className="absolute inset-0 bg-black/50 z-20"></div>
          <Spinner />
        </>
      )}

      {/* Filter Controls */}
      <div className={`absolute top-4 left-4 z-10 bg-zinc-800 p-4 rounded-lg text-white min-w-[200px] ${!isConnected ? 'opacity-50 pointer-events-none' : ''}`}>
        <h3 className="text-sm font-semibold mb-4 text-white">
          Filters
        </h3>
        
        <div className="mb-2">
          <label className="block text-xs mb-1 text-zinc-300">
            Priority
          </label>
          <select 
            value={filter.priority}
            onChange={(e) => setFilter(prev => ({ ...prev, priority: e.target.value }))}
            className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-sm"
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
          <label className="block text-xs mb-1 text-zinc-300">
            Source
          </label>
          <select 
            value={filter.source}
            onChange={(e) => setFilter(prev => ({ ...prev, source: e.target.value }))}
            className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-sm"
            disabled={!isConnected}
          >
            <option value="all">All Sources</option>
            <option value="reddit">Reddit</option>
            <option value="311">311</option>
            <option value="twitter">Twitter</option>
          </select>
        </div>

        <div className="mb-4">
          <label className="block text-xs mb-1 text-zinc-300">
            Status
          </label>
          <select 
            value={filter.status}
            onChange={(e) => setFilter(prev => ({ ...prev, status: e.target.value }))}
            className="w-full p-1 bg-zinc-700 text-white border border-zinc-600 rounded text-sm"
            disabled={!isConnected}
          >
            <option value="all">All Status</option>
            <option value="new">New</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>

        {/* View Mode Toggles */}
        <div className="border-t border-zinc-700 pt-3">
          <h4 className="text-xs font-semibold mb-2 text-zinc-300">
            View Mode
          </h4>
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
              <input
                type="radio"
                name="viewMode"
                value="category"
                checked={viewMode === 'category'}
                onChange={(e) => setViewMode(e.target.value as 'priority' | 'source' | 'category')}
                className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                disabled={!isConnected}
              />
              <span>By Category</span>
              <span className="text-zinc-500">(category icons)</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
              <input
                type="radio"
                name="viewMode"
                value="source"
                checked={viewMode === 'source'}
                onChange={(e) => setViewMode(e.target.value as 'priority' | 'source' | 'category')}
                className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                disabled={!isConnected}
              />
              <span>By Source</span>
              <span className="text-zinc-500">(source icons)</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
              <input
                type="radio"
                name="viewMode"
                value="priority"
                checked={viewMode === 'priority'}
                onChange={(e) => setViewMode(e.target.value as 'priority' | 'source' | 'category')}
                className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                disabled={!isConnected}
              />
              <span>By Priority</span>
              <span className="text-zinc-500">(colored circles)</span>
            </label>
          </div>
        </div>
      </div>

      {/* Alert Count */}
      <div className={`absolute top-4 right-4 z-10 bg-zinc-800/95 px-4 py-2 rounded-lg text-white text-sm ${!isConnected ? 'opacity-50' : ''}`}>
        {filteredAlerts.length} alerts visible
        {isConnected && (
          <span className="ml-2 text-status-connected">●</span>
        )}
      </div>

      {/* Time Range Slider */}
      <div className={`absolute bottom-6 left-1/2 transform -translate-x-1/2 z-10 bg-zinc-800/95 px-6 py-4 rounded-lg text-white min-w-[400px] ${!isConnected ? 'opacity-50 pointer-events-none' : ''}`}>
        <div className="text-center mb-3">
          <h4 className="text-xs font-semibold text-zinc-300 mb-1">Time Filter</h4>
        </div>
        
        <div className="relative">
          {/* Hour markers - flipped so recent times are on right */}
          <div className="flex justify-between text-xs text-zinc-400 mb-2 px-1">
            <span>-7d</span>
            <span>-5d</span>
            <span>-3d</span>
            <span>-1d</span>
            <span>-12h</span>
            <span>-1h</span>
          </div>
          
          {/* Slider - inverted so right side = fewer hours (more recent) */}
          <input
            type="range"
            min="1"
            max="168"
            step="1"
            value={169 - filter.timeRangeHours}
            onChange={(e) => setFilter(prev => ({ ...prev, timeRangeHours: 169 - parseInt(e.target.value) }))}
            className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer slider"
            disabled={!isConnected}
          />
          
          {/* Current value indicator */}
          <div className="text-center">
            <h3 className="text-xs font-semibold mt-4 text-white">
              Last {filter.timeRangeHours} hour{filter.timeRangeHours !== 1 ? 's' : ''}
              {filter.timeRangeHours >= 24 && (
                <span className="text-zinc-400 ml-1">
                  ({Math.round(filter.timeRangeHours / 24 * 10) / 10} day{filter.timeRangeHours >= 48 ? 's' : ''})
                </span>
              )}
            </h3>
          </div>
        </div>
      </div>



      <div className={`w-full h-full ${!isConnected ? 'grayscale opacity-50' : ''}`}>
        <Map
          ref={mapRef}
          initialViewState={viewport}
          mapboxAccessToken={MAPBOX_TOKEN}
          style={{ width: '100%', height: '100%' }}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          interactiveLayerIds={viewMode === 'priority' ? ['alert-points'] : []}
          interactive={isConnected}
          dragPan={isConnected}
          dragRotate={isConnected}
          scrollZoom={isConnected}
          keyboard={isConnected}
          doubleClickZoom={isConnected}
          onMove={handleViewportChange}
        >
          {/* Priority Mode - Circle Layer */}
          {viewMode === 'priority' && (
            <Source type="geojson" data={alertsGeoJSON}>
              <Layer
                id="alert-points"
                type="circle"
                paint={{
                  'circle-radius': [
                    'case',
                    ['==', ['get', 'priority'], 'critical'], 10,
                    ['==', ['get', 'priority'], 'high'], 8,
                    ['==', ['get', 'priority'], 'medium'], 6,
                    6
                  ],
                  'circle-color': [
                    'case',
                    ['==', ['get', 'priority'], 'critical'], '#dc2626',
                    ['==', ['get', 'priority'], 'high'], '#ea580c',
                    ['==', ['get', 'priority'], 'medium'], '#d97706',
                    '#65a30d'
                  ],
                  'circle-opacity': 0.8,
                  'circle-stroke-width': 1,
                  'circle-stroke-color': '#ffffff'
                }}
              />
            </Source>
          )}

          {/* Source Mode - HTML Markers */}
          {viewMode === 'source' && filteredAlerts.map(alert => (
            <Marker
              key={alert.id}
              longitude={alert.coordinates.lng}
              latitude={alert.coordinates.lat}
              anchor="center"
              onClick={() => handleMarkerClick(alert)}
            >
              <div
                className={`cursor-pointer transition-transform hover:scale-110 flex items-center justify-center rounded-full ${getBackgroundIconColor(alert.source as 'reddit' | '311' | 'twitter')}`}
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
          {viewMode === 'category' && filteredAlerts.map(alert => (
            <Marker
              key={alert.id}
              longitude={alert.coordinates.lng}
              latitude={alert.coordinates.lat}
              anchor="center"
              onClick={() => handleMarkerClick(alert)}
            >
              <div
                className={`cursor-pointer transition-transform hover:scale-110 flex items-center justify-center rounded-full ${getCategoryBackgroundColor(alert.category || 'general')}`}
                style={{
                  fontSize: `${getIconSize(alert.priority)}px`,
                  width: `${getIconSize(alert.priority) + 8}px`,
                  height: `${getIconSize(alert.priority) + 8}px`,
                }}
              >
                {getCategoryIcon(alert.category || 'general')}
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
                console.log('❌ Closing popup');
                setSelectedAlert(null);
                setSelectedAlertLoading(false);
              }}
              closeButton={true}
              closeOnClick={false}
              className="max-w-[360px]"
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
                    <h4 className="text-base font-semibold text-white leading-tight">
                      {selectedAlert.title}
                    </h4>
                    <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-1 ${
                      selectedAlert.priority === 'critical' ? 'bg-red-500 text-white' :
                      selectedAlert.priority === 'high' ? 'bg-orange-500 text-white' :
                      selectedAlert.priority === 'medium' ? 'bg-yellow-500 text-black' :
                      'bg-green-500 text-white'
                    }`}>
                      {selectedAlert.priority.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-sm text-zinc-300 mb-4 leading-relaxed">
                  {selectedAlert.description}
                </p>

                {/* Key-Value Pairs */}
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Location</span>
                    <span className="text-sm text-white text-right">
                      {[
                        selectedAlert.neighborhood !== 'Unknown' ? selectedAlert.neighborhood : null,
                        selectedAlert.borough !== 'Unknown' ? selectedAlert.borough : null
                      ].filter(Boolean).join(', ') || 'Location not specified'}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Category</span>
                    <span className="text-sm text-white capitalize flex items-center gap-1">
                      <span>{getCategoryIcon(selectedAlert.category || 'general')}</span>
                      {selectedAlert.category || 'General'}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Status</span>
                    <span className="text-sm text-white capitalize">
                      {selectedAlert.status}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Source</span>
                    <span className="text-sm text-white capitalize">
                      {selectedAlert.source}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Time</span>
                    <span className="text-sm text-white">
                      {new Date(selectedAlert.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Action Buttons */}
                {selectedAlert.source !== "311" && (
                  <div className="space-y-2">
                  {/* Generate/View Report Button - always show unless disabled */}
                  <button
                    className={`btn w-full text-sm ${
                      isInvestigationDisabled(selectedAlert)
                        ? 'bg-yellow-600 cursor-not-allowed text-white' 
                        : selectedAlert.status === 'resolved' && selectedAlert.reportUrl
                        ? 'btn-success'
                        : 'btn-primary'
                    }`}
                    onClick={() => handleReportButtonClick(selectedAlert)}
                    disabled={isInvestigationDisabled(selectedAlert)}
                  >
                    {getReportButtonContent(selectedAlert)}
                  </button>

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
        onClose={() => setTraceModal({ isOpen: false, traceId: '', alertTitle: '' })}
        traceId={traceModal.traceId}
        alertTitle={traceModal.alertTitle}
      />
    </div>
  );
};

export default MapView; 