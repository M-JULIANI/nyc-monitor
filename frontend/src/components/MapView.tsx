import { useState, useRef, useEffect, useMemo } from 'react';
import Map, { Layer, Source, Popup, Marker } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Alert } from '../types';
import { useAlerts } from '../contexts/AlertsContext';
import { useMapState } from '../contexts/MapStateContext';
import Spinner from './Spinner';

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
  const { alerts, error, isLoading } = useAlerts();
  const isConnected = !isLoading;
  const { viewport, setViewport, filter, setFilter, viewMode, setViewMode } = useMapState();
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  
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
    console.log('Filtering with timeRangeHours:', filter.timeRangeHours);
    
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
      
      // Debug logging for first few alerts
      if (alerts.indexOf(alert) < 3) {
        console.log(`Alert ${alert.id}:`, {
          date: alert.timestamp,
          alertTime: alertTime.toISOString(),
          now: now.toISOString(),
          hoursAgo: hoursAgo.toFixed(2),
          timeRangeHours: filter.timeRangeHours,
          willShow: hoursAgo <= filter.timeRangeHours
        });
      }
      
      if (hoursAgo > filter.timeRangeHours) return false;
      
      return true;
    });
    
    console.log(`Filtered from ${alerts.length} to ${filtered.length} alerts`);
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

  const getBackgroundIconColor = (source: 'reddit' | '311' | 'twitter'): string => {
    switch (source) {
      case 'reddit': return 'bg-orange-400';
      case '311': return 'bg-yellow-400';
      case 'twitter': return 'bg-blue-400';
      default: return 'bg-gray-400';
    }
  };

  const getIconSize = (priority: string): number => {
    switch (priority) {
      case 'critical': return 24;
      case 'high': return 20;
      case 'medium': return 16;
      default: return 20;
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical': return '#dc2626';
      case 'high': return '#ea580c';
      case 'medium': return '#d97706';
      default: return '#65a30d';
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

  const handleMapClick = (event: any) => {
    // Disable interactions when not connected
    if (!isConnected) return;
    
    // In priority mode, handle clicks on circle features
    if (viewMode === 'priority') {
      const features = event.features;
      if (features && features.length > 0) {
        const clickedAlertId = features[0].properties.id;
        const alert = alerts.find(a => a.id === clickedAlertId);
        setSelectedAlert(alert || null);
      } else {
        setSelectedAlert(null);
      }
    }
    // In source mode, clicks are handled by individual markers
  };

  const handleMarkerClick = (alert: Alert) => {
    if (!isConnected) return;
    setSelectedAlert(alert);
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
                value="priority"
                checked={viewMode === 'priority'}
                onChange={(e) => setViewMode(e.target.value as 'priority' | 'source')}
                className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                disabled={!isConnected}
              />
              <span>By Priority</span>
              <span className="text-zinc-500">(colored circles)</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
              <input
                type="radio"
                name="viewMode"
                value="source"
                checked={viewMode === 'source'}
                onChange={(e) => setViewMode(e.target.value as 'priority' | 'source')}
                className="w-3 h-3 text-blue-600 bg-zinc-700 border-zinc-600 focus:ring-blue-500"
                disabled={!isConnected}
              />
              <span>By Source</span>
              <span className="text-zinc-500">(source icons)</span>
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
          onClick={handleMapClick}
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

          {/* Popup for selected alert */}
          {selectedAlert && (
            <Popup
              longitude={selectedAlert.coordinates.lng}
              latitude={selectedAlert.coordinates.lat}
              anchor="bottom"
              onClose={() => setSelectedAlert(null)}
              closeButton={true}
              closeOnClick={false}
              className="max-w-[320px]"
            >
              <div className="p-4 bg-zinc-800 border border-zinc-700 rounded-xl text-white shadow-xl">
                <h4 className={`text-base font-semibold mb-2 flex items-center gap-2 text-white`}>
                  <span>{getSourceIcon(selectedAlert.source)}</span>
                  <span>{selectedAlert.title}</span>
                </h4>
                <p className="text-sm text-zinc-300 mb-2">
                  {selectedAlert.description}
                </p>
                <div className="flex justify-between items-center text-xs text-zinc-300 mb-1">
                  <span>
                    📍 {selectedAlert.neighborhood}, {selectedAlert.borough}
                  </span>
                  <span className={`priority-badge priority-${selectedAlert.priority}`}>{selectedAlert.priority}</span>
                </div>
                <div className="mt-2 pt-2 border-t border-zinc-700 text-xs text-zinc-300">
                  Status: <strong className="text-white">{selectedAlert.status}</strong> | 
                  Source: <strong className="text-white">{selectedAlert.source}</strong> | 
                  {new Date(selectedAlert.timestamp).toLocaleString()}
                </div>
                <button
                  className="btn btn-primary w-full mt-3 text-xs"
                  onClick={() => {
                    alert('Generate Report feature coming soon!');
                  }}
                >
                  Generate Report
                </button>
              </div>
            </Popup>
          )}
        </Map>
      </div>
    </div>
  );
};

export default MapView; 