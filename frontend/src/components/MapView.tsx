import { useState, useRef, useEffect } from 'react';
import Map, { Layer, Source, Popup } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Alert } from '../types';
import { useAlerts } from '../contexts/AlertsContext';
import Spinner from './Spinner';

const MAPBOX_TOKEN = 'pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA';

const MapView: React.FC = () => {
  const mapRef = useRef<any>(null);
  const { alerts, error, isConnected } = useAlerts();;
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filter, setFilter] = useState({
    priority: 'all',
    source: 'all',
    status: 'all',
    timeRange: '24h'
  });

  // NYC bounding box for initial viewport (fallback when no alerts)
  const nycBounds = {
    longitude: -74.0,
    latitude: 40.7,
    zoom: 10
  };

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
  const filteredAlerts = alerts.filter(alert => {
    if (filter.priority !== 'all' && alert.priority !== filter.priority) return false;
    if (filter.source !== 'all' && alert.source !== filter.source) return false;
    if (filter.status !== 'all' && alert.status !== filter.status) return false;
    // TODO: Add time range filtering
    return true;
  });

  // Update map bounds when alerts change
  useEffect(() => {
    if (mapRef.current && filteredAlerts.length > 0) {
      const bounds = calculateAlertBounds(filteredAlerts);
      if (bounds) {
        try {
          mapRef.current.fitBounds(bounds, {
            padding: { top: 100, bottom: 100, left: 300, right: 100 }, // Extra padding for UI elements
            duration: 1000, // Smooth animation
            maxZoom: 16 // Don't zoom in too close
          });
        } catch (error) {
          console.warn('Error fitting bounds:', error);
        }
      }
    }
  }, [filteredAlerts]); // Re-run when filtered alerts change

  const getSourceIcon = (source: string): string => {
    switch (source) {
      case 'reddit': return '🟠';
      case '311': return '📞';
      case 'twitter': return '🐦';
      default: return '📍';
    }
  };

  // Create GeoJSON for alert points
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
    
    const features = event.features;
    if (features && features.length > 0) {
      const clickedAlertId = features[0].properties.id;
      const alert = alerts.find(a => a.id === clickedAlertId);
      setSelectedAlert(alert || null);
    } else {
      setSelectedAlert(null);
    }
  };

  return (
    <div className="relative w-full h-full">
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

        <div>
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
      </div>

      {/* Alert Count */}
      <div className={`absolute top-4 right-4 z-10 bg-zinc-800/95 px-4 py-2 rounded-lg text-white text-sm ${!isConnected ? 'opacity-50' : ''}`}>
        {filteredAlerts.length} alerts visible
        {isConnected && (
          <span className="ml-2 text-status-connected">●</span>
        )}
      </div>

      <div className={`w-full h-full ${!isConnected ? 'grayscale opacity-50' : ''}`}>
        <Map
          ref={mapRef}
          initialViewState={nycBounds}
          mapboxAccessToken={MAPBOX_TOKEN}
          style={{ width: '100%', height: '100%' }}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          interactiveLayerIds={isConnected ? ['alert-points'] : []}
          onClick={handleMapClick}
          interactive={isConnected}
          dragPan={isConnected}
          dragRotate={isConnected}
          scrollZoom={isConnected}
          keyboard={isConnected}
          doubleClickZoom={isConnected}
        >
          <Source type="geojson" data={alertsGeoJSON}>
            <Layer
              id="alert-points"
              type="circle"
              paint={{
                'circle-radius': [
                  'case',
                  ['==', ['get', 'priority'], 'critical'], 12,
                  ['==', ['get', 'priority'], 'high'], 10,
                  ['==', ['get', 'priority'], 'medium'], 8,
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
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff'
              }}
            />
          </Source>

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