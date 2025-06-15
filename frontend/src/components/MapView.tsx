import { useState, useRef } from 'react';
import Map, { Layer, Source, Popup } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Alert } from '@/types';

const MAPBOX_TOKEN = 'pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA';


// Sample data for demonstration
const sampleAlerts: Alert[] = [
  {
    id: '1',
    title: 'Water Main Break',
    description: 'Major water main break causing street flooding on Broadway',
    latitude: 40.7589,
    longitude: -73.9851,
    priority: 'high',
    source: '311',
    timestamp: '2024-01-15T10:30:00Z',
    status: 'investigating',
    neighborhood: 'Times Square',
    borough: 'Manhattan'
  },
  {
    id: '2',
    title: 'Traffic Accident',
    description: 'Multi-car accident blocking traffic on FDR Drive',
    latitude: 40.7505,
    longitude: -73.9934,
    priority: 'medium',
    source: 'twitter',
    timestamp: '2024-01-15T11:15:00Z',
    status: 'new',
    neighborhood: 'Lower East Side',
    borough: 'Manhattan'
  },
  {
    id: '3',
    title: 'Power Outage',
    description: 'Widespread power outage affecting multiple blocks',
    latitude: 40.6892,
    longitude: -74.0445,
    priority: 'critical',
    source: 'reddit',
    timestamp: '2024-01-15T09:45:00Z',
    status: 'investigating',
    neighborhood: 'Brooklyn Heights',
    borough: 'Brooklyn'
  },
  {
    id: '4',
    title: 'Construction Issue',
    description: 'Unauthorized construction causing noise complaints',
    latitude: 40.7831,
    longitude: -73.9712,
    priority: 'low',
    source: '311',
    timestamp: '2024-01-15T08:20:00Z',
    status: 'resolved',
    neighborhood: 'Upper West Side',
    borough: 'Manhattan'
  }
];

const MapView: React.FC = () => {
  const mapRef = useRef<any>(null);
  const [alerts] = useState<Alert[]>(sampleAlerts);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filter, setFilter] = useState({
    priority: 'all',
    source: 'all',
    status: 'all',
    timeRange: '24h'
  });

  // NYC bounding box for initial viewport
  const nycBounds = {
    longitude: -74.0,
    latitude: 40.7,
    zoom: 10
  };

  // const getPriorityColor = (priority: string): string => {
  //   switch (priority) {
  //     case 'critical': return '#dc2626'; // red
  //     case 'high': return '#ea580c'; // orange
  //     case 'medium': return '#d97706'; // amber
  //     case 'low': return '#65a30d'; // green
  //     default: return '#6b7280'; // gray
  //   }
  // };

  const getSourceIcon = (source: string): string => {
    switch (source) {
      case 'reddit': return '🟠';
      case '311': return '📞';
      case 'twitter': return '🐦';
      default: return '📍';
    }
  };

  // Filter alerts based on current filter settings
  const filteredAlerts = alerts.filter(alert => {
    if (filter.priority !== 'all' && alert.priority !== filter.priority) return false;
    if (filter.source !== 'all' && alert.source !== filter.source) return false;
    if (filter.status !== 'all' && alert.status !== filter.status) return false;
    // TODO: Add time range filtering
    return true;
  });

  // Create GeoJSON for alert points
  const alertsGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: filteredAlerts.map(alert => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [alert.longitude, alert.latitude]
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
      {/* Filter Controls */}
      <div className="absolute top-4 left-4 z-10 bg-zinc-800 p-4 rounded-lg text-white min-w-[200px]">
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
          >
            <option value="all">All Status</option>
            <option value="new">New</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Alert Count */}
      <div className="absolute top-4 right-4 z-10 bg-zinc-800/95 px-4 py-2 rounded-lg text-white text-sm">
        {filteredAlerts.length} alerts visible
      </div>

      <Map
        ref={mapRef}
        initialViewState={nycBounds}
        mapboxAccessToken={MAPBOX_TOKEN}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        interactiveLayerIds={['alert-points']}
        onClick={handleMapClick}
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
            longitude={selectedAlert.longitude}
            latitude={selectedAlert.latitude}
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
  );
};

export default MapView; 