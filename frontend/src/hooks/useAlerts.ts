// frontend/src/hooks/useAlerts.ts
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Alert } from '../types';

interface AlertsData {
  alerts: Alert[];
  timestamp: string;
}

interface UseAlertsOptions {
  useStream?: boolean; // Default true - set false to only use REST endpoint
  pollInterval?: number; // For REST-only mode, default 15 minutes
}

export const useAlerts = (options: UseAlertsOptions = {}) => {
  const { useStream = true, pollInterval = 1800000 } = options; // 30 minutes = 900000ms
  
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Memoized function to merge alerts to prevent unnecessary re-renders
  const mergeAlerts = useCallback((prevAlerts: Alert[], newAlerts: Alert[]) => {
    const existingIds = new Set(prevAlerts.map((alert: Alert) => alert.id));
    const uniqueNewAlerts = newAlerts.filter((alert: Alert) => !existingIds.has(alert.id));
    return [...uniqueNewAlerts, ...prevAlerts].slice(0, 100); // Keep last 100
  }, []);

  // Fetch initial alerts using REST endpoint
  const fetchRecentAlerts = useCallback(async () => {
    try {
      const response = await fetch('/api/alerts/recent');
      if (!response.ok) throw new Error('Failed to fetch alerts');
      
      const data = await response.json();
      setAlerts(data.alerts || []);
      setError(null);
      setIsLoading(false);
    } catch (err) {
      setError('Failed to load recent alerts');
      setIsLoading(false);
      console.error('Error fetching recent alerts:', err);
    }
  }, []);

  useEffect(() => {
    // Always load initial data first
    fetchRecentAlerts();

    if (!useStream) {
      // REST-only mode: set up polling
      const interval = setInterval(fetchRecentAlerts, pollInterval);
      return () => clearInterval(interval);
    }

    // Stream mode: set up SSE after initial load
    const eventSource = new EventSource('/api/alerts/stream');
    
    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };
    
    eventSource.onmessage = (event) => {
      try {
        const data: AlertsData = JSON.parse(event.data);
        if (data.alerts && Array.isArray(data.alerts)) {
          setAlerts(prevAlerts => mergeAlerts(prevAlerts, data.alerts));
        }
      } catch (err) {
        setError('Failed to parse alert data');
        console.error('Error parsing alert data:', err);
      }
    };
    
    eventSource.onerror = (event) => {
      setError('Connection to alert stream failed');
      setIsConnected(false);
      // EventSource will automatically try to reconnect
      console.warn('SSE connection error, will retry automatically');
      console.error('SSE connection error:', event);
    };

    return () => {
      eventSource.close();
    };
  }, [mergeAlerts, useStream, pollInterval, fetchRecentAlerts]);

  // Memoized stats to prevent recalculation on every render
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
      active: (byStatus.new || 0) + (byStatus.investigating || 0),
      resolved: byStatus.resolved || 0
    };
  }, [alerts]);

  return { 
    alerts, 
    error, 
    isConnected: useStream ? isConnected : true, // Always "connected" in REST mode
    isLoading,
    stats: alertStats,
    refetch: fetchRecentAlerts // Manual refresh function
  };
};