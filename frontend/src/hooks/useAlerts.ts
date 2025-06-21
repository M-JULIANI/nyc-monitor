// frontend/src/hooks/useAlerts.ts
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Alert } from '../types';

interface UseAlertsOptions {
  pollInterval?: number; // How often to refresh data
  limit?: number; // Max number of alerts to load
  hours?: number; // How many hours back to fetch
}

// Function to normalize alert objects
const normalizeAlert = (rawAlert: any): Alert => {
  const original = rawAlert.original_alert || {};
  const originalData = original.original_alert_data || {};
  
  // Extract coordinates from wherever they exist
  let coordinates = {
    lat: 40.7589, // NYC center fallback (Times Square)
    lng: -73.9851
  };
  
  if (original.latitude && original.longitude && 
      original.latitude !== null && original.longitude !== null) {
    coordinates = {
      lat: original.latitude,
      lng: original.longitude
    };
  } else if (originalData.coordinates?.lat && originalData.coordinates?.lng &&
             originalData.coordinates.lat !== null && originalData.coordinates.lng !== null) {
    coordinates = originalData.coordinates;
  } else if (rawAlert.coordinates?.lat && rawAlert.coordinates?.lng) {
    coordinates = rawAlert.coordinates;
  }

  // Use the most complete/accurate data available
  return {
    id: rawAlert.id || original.id || rawAlert.alert_id,
    title: rawAlert.title || original.title || rawAlert.topic,
    description: original.description || rawAlert.description || '',
    source: original.source || rawAlert.source === 'unknown' ? originalData.signals?.[0] || 'unknown' : rawAlert.source,
    priority: original.priority || rawAlert.priority || 'medium',
    status: original.status || rawAlert.status || 'active',
    
    timestamp: original.timestamp || original.created_at || rawAlert.created_at || rawAlert.timestamp || new Date().toISOString(),
    neighborhood: original.neighborhood || originalData.area || rawAlert.area || rawAlert.neighborhood || 'Unknown',
    borough: original.borough || original.borough_primary || rawAlert.borough || 'Unknown',
    
    // Additional date/time fields
    event_date: original.event_date || rawAlert.event_date,
    created_at: original.created_at || rawAlert.created_at,
    updated_at: rawAlert.updated_at,
    
    // Location data
    coordinates: coordinates as { lat: number; lng: number },
    area: originalData.area || original.neighborhood || rawAlert.area || rawAlert.neighborhood || 'Unknown',
    venue_address: originalData.venue_address || rawAlert.venue_address || '',
    specific_streets: originalData.specific_streets || rawAlert.specific_streets || [],
    cross_streets: originalData.cross_streets || rawAlert.cross_streets || [],
    
    // Impact data
    crowd_impact: originalData.crowd_impact || rawAlert.crowd_impact || 'unknown',
    transportation_impact: originalData.transportation_impact || rawAlert.transportation_impact || '',
    estimated_attendance: originalData.estimated_attendance || rawAlert.estimated_attendance || '',
    severity: originalData.severity || rawAlert.severity || 0,
    
    // Categorization fields (simplified to just main category)
    category: rawAlert.category || original.category || 'general',
    
    // Additional data
    keywords: originalData.keywords || rawAlert.keywords || [],
    signals: originalData.signals || rawAlert.signals || [],
    url: rawAlert.url || '',
  };
};

export const useAlerts = (options: UseAlertsOptions = {}) => {
  const { 
    pollInterval = 1800000, // 30 minutes
    limit = 2000, // High limit for map display
    hours = 72 // Default to 24 hours if not provided
  } = options;
  
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);

  // Fetch all alerts - simplified
  const fetchAlerts = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`/api/alerts/recent?limit=${limit}&hours=${hours}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Normalize the alerts
      const normalizedAlerts = (data.alerts || []).map(normalizeAlert);
      
      setAlerts(normalizedAlerts);
      setLastFetch(new Date());
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts');
      setIsLoading(false);
      console.error('Error fetching alerts:', err);
    }
  }, [limit, hours]);

  // Auto-refresh alerts
  useEffect(() => {
    // Initial load
    fetchAlerts();

    // Set up polling
    const interval = setInterval(fetchAlerts, pollInterval);
    return () => clearInterval(interval);
  }, [fetchAlerts, pollInterval]);

  // Memoized stats
  const alertStats = useMemo(() => {
    const total = alerts.length;
    const byPriority = alerts.reduce((acc, alert) => {
      acc[alert.priority] = (acc[alert.priority] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    const byStatus = alerts.reduce((acc, alert) => {
      acc[alert.status] = (acc[alert.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const bySource = alerts.reduce((acc, alert) => {
      acc[alert.source] = (acc[alert.source] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      total,
      byPriority,
      byStatus,
      bySource,
      critical: byPriority.critical || 0,
      high: byPriority.high || 0,
      medium: byPriority.medium || 0,
      low: byPriority.low || 0,
      active: (byStatus.new || 0) + (byStatus.investigating || 0) + (byStatus.active || 0),
      resolved: byStatus.resolved || 0
    };
  }, [alerts]);

  return { 
    alerts, 
    error, 
    isLoading,
    lastFetch,
    stats: alertStats,
    refetch: fetchAlerts
  };
};