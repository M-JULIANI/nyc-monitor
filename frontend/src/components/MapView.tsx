import { useState, useRef } from 'react';
import Map, { Layer, Source, Popup } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';


const MAPBOX_TOKEN = 'pk.eyJ1IjoibWp1bGlhbmkiLCJhIjoiY21iZWZzbGpzMWZ1ejJycHgwem9mdTkxdCJ9.pRU2rzdu-wP9A63--30ldA';
// Sample NYC alert data structure
interface Alert {
  id: string;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  source: 'reddit' | '311' | 'twitter';
  timestamp: string;
  status: 'new' | 'investigating' | 'resolved';
  neighborhood?: string;
  borough?: string;
}

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

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical': return '#dc2626'; // red
      case 'high': return '#ea580c'; // orange
      case 'medium': return '#d97706'; // amber
      case 'low': return '#65a30d'; // green
      default: return '#6b7280'; // gray
    }
  };

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
  const alertsGeoJSON = {
    type: 'FeatureCollection',
    features: filteredAlerts.map(alert => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [alert.longitude, alert.latitude]
      },
      properties: {
        id: alert.id,
        title: alert.title,
        priority: alert.priority,
        source: alert.source,
        color: getPriorityColor(alert.priority)
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
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Filter Controls */}
      <div style={{
        position: 'absolute',
        top: '1rem',
        left: '1rem',
        zIndex: 10,
        background: 'rgba(31, 41, 55, 0.95)',
        padding: '1rem',
        borderRadius: '0.5rem',
        color: '#fff',
        minWidth: '200px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', fontWeight: '600' }}>
          Filters
        </h3>
        
        <div style={{ marginBottom: '0.5rem' }}>
          <label style={{ display: 'block', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
            Priority:
          </label>
          <select 
            value={filter.priority}
            onChange={(e) => setFilter(prev => ({ ...prev, priority: e.target.value }))}
            style={{
              width: '100%',
              padding: '0.25rem',
              background: '#374151',
              color: '#fff',
              border: '1px solid #4b5563',
              borderRadius: '0.25rem'
            }}
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div style={{ marginBottom: '0.5rem' }}>
          <label style={{ display: 'block', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
            Source:
          </label>
          <select 
            value={filter.source}
            onChange={(e) => setFilter(prev => ({ ...prev, source: e.target.value }))}
            style={{
              width: '100%',
              padding: '0.25rem',
              background: '#374151',
              color: '#fff',
              border: '1px solid #4b5563',
              borderRadius: '0.25rem'
            }}
          >
            <option value="all">All Sources</option>
            <option value="reddit">Reddit</option>
            <option value="311">311</option>
            <option value="twitter">Twitter</option>
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
            Status:
          </label>
          <select 
            value={filter.status}
            onChange={(e) => setFilter(prev => ({ ...prev, status: e.target.value }))}
            style={{
              width: '100%',
              padding: '0.25rem',
              background: '#374151',
              color: '#fff',
              border: '1px solid #4b5563',
              borderRadius: '0.25rem'
            }}
          >
            <option value="all">All Status</option>
            <option value="new">New</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Alert Count */}
      <div style={{
        position: 'absolute',
        top: '1rem',
        right: '1rem',
        zIndex: 10,
        background: 'rgba(31, 41, 55, 0.95)',
        padding: '0.5rem 1rem',
        borderRadius: '0.5rem',
        color: '#fff',
        fontSize: '0.875rem'
      }}>
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
          {/* Alert points */}
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
              'circle-color': ['get', 'color'],
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
            style={{ maxWidth: '300px' }}
          >
            <div style={{ padding: '0.5rem' }}>
              <h4 style={{ 
                margin: '0 0 0.5rem 0', 
                color: getPriorityColor(selectedAlert.priority),
                fontSize: '1rem',
                fontWeight: '600'
              }}>
                {getSourceIcon(selectedAlert.source)} {selectedAlert.title}
              </h4>
              <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', color: '#374151' }}>
                {selectedAlert.description}
              </p>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                fontSize: '0.75rem',
                color: '#6b7280'
              }}>
                <span>
                  📍 {selectedAlert.neighborhood}, {selectedAlert.borough}
                </span>
                <span 
                  style={{ 
                    background: getPriorityColor(selectedAlert.priority),
                    color: '#fff',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    textTransform: 'uppercase',
                    fontWeight: '600'
                  }}
                >
                  {selectedAlert.priority}
                </span>
              </div>
              <div style={{ 
                marginTop: '0.5rem',
                paddingTop: '0.5rem',
                borderTop: '1px solid #e5e7eb',
                fontSize: '0.75rem',
                color: '#6b7280'
              }}>
                Status: <strong>{selectedAlert.status}</strong> | 
                Source: <strong>{selectedAlert.source}</strong> | 
                {new Date(selectedAlert.timestamp).toLocaleString()}
              </div>
              <button
                style={{
                  marginTop: '0.5rem',
                  padding: '0.5rem 1rem',
                  background: '#3b82f6',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  width: '100%'
                }}
                onClick={() => {
                  // TODO: Implement report generation
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