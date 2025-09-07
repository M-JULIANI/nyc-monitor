import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { debounce } from 'lodash';
import { Alert } from '../types';
import { ViewportState } from './MapStateContext';
import type { Map as MapboxMap } from 'mapbox-gl';

// Define viewport and date range types
export interface BoundingBox {
  lat1: number;
  lng1: number;
  lat2: number;
  lng2: number;
}

export interface DateRange {
  start: string; // YYYY-MM-DD format
  end: string;   // YYYY-MM-DD format
}


// Performance metrics as outlined in the enhanced strategy
export interface PerformanceMetrics {
  timestamp: string;
  bbox_area: number;
  alert_count: number;
  backend_performance?: {
    total_time_ms: number;
    cache_hit: boolean;
    cache_time_ms?: number;
    db_query_time_ms?: number;
    cache_write_time_ms?: number;
    source: 'redis_cache' | 'database_fresh';
  };
  frontend_metrics: {
    round_trip_time_ms: number;
    render_time_ms: number;
    total_frontend_time_ms: number;
  };
}

interface ViewportAlertsContextType {
  // Alert data
  alerts: Alert[];
  isLoading: boolean;
  error: string | null;
  
  // Performance tracking
  performanceMetrics: PerformanceMetrics[];
  
  // Methods
  fetchViewportAlerts: (bbox: BoundingBox, dateRange: DateRange) => Promise<void>;
  debouncedFetchViewportAlerts: (bbox: BoundingBox, dateRange: DateRange) => void;
  clearAlerts: () => void;
  
  // Utility methods
  calculateBboxArea: (bbox: BoundingBox) => number;
  viewportToBbox: (viewport: ViewportState, padding?: number) => BoundingBox;
  mapToBbox: (map: MapboxMap, padding?: number) => BoundingBox;
}

const ViewportAlertsContext = createContext<ViewportAlertsContextType | undefined>(undefined);

interface ViewportAlertsProviderProps {
  children: React.ReactNode;
}

export const ViewportAlertsProvider: React.FC<ViewportAlertsProviderProps> = ({ children }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics[]>([]);
  
  // Keep track of the last successful request to avoid duplicates
  const lastRequestRef = useRef<string>('');

  // Calculate bounding box area for performance tracking
  const calculateBboxArea = useCallback((bbox: BoundingBox): number => {
    const { lat1, lng1, lat2, lng2 } = bbox;
    const width = Math.abs(lng2 - lng1);
    const height = Math.abs(lat2 - lat1);
    return width * height;
  }, []);

  // Convert Mapbox map bounds to our BoundingBox format (PREFERRED METHOD)
  const mapToBbox = useCallback((map: MapboxMap, padding: number = 0.01): BoundingBox => {
    // Use Mapbox's native getBounds() method - this is the most accurate approach
    const bounds = map.getBounds();
    
    // Apply padding by expanding the bounds uniformly
    const latPadding = padding;
    const lngPadding = padding;
    
    return {
      lat1: bounds.getSouth() - latPadding,
      lng1: bounds.getWest() - lngPadding,
      lat2: bounds.getNorth() + latPadding,
      lng2: bounds.getEast() + lngPadding,
    };
  }, []);

  // Fallback: Convert viewport to bounding box with optional padding
  // Only use this when map reference is not available
  const viewportToBbox = useCallback((viewport: ViewportState, padding: number = 0.01): BoundingBox => {
    console.warn('⚠️ Using fallback viewport->bbox conversion. Consider using mapToBbox() with map reference for accuracy.');
    
    const { latitude, longitude, zoom } = viewport;
    
    // Rough degree calculation based on zoom level
    // This is a simplified approach - Mapbox provides more precise methods
    const baseSpan = 360 / Math.pow(2, zoom);
    const latSpan = baseSpan * 0.75; // Account for latitude compression
    const lngSpan = baseSpan;
    
    return {
      lat1: latitude - (latSpan / 2) - padding,
      lng1: longitude - (lngSpan / 2) - padding,
      lat2: latitude + (latSpan / 2) + padding,
      lng2: longitude + (lngSpan / 2) + padding,
    };
  }, []);

  // Fixed debounce delay to prevent excessive requests during rapid map interactions
  const DEBOUNCE_DELAY = 500; // 500ms delay for all viewport changes

  // Core fetch function that calls the viewport endpoint
  const fetchViewportAlerts = useCallback(async (bbox: BoundingBox, dateRange: DateRange): Promise<void> => {
    const { lat1, lng1, lat2, lng2 } = bbox;
    const { start, end } = dateRange;
    
    // Create a unique request signature to prevent duplicate requests
    const requestSignature = `${lat1},${lng1},${lat2},${lng2}:${start}:${end}`;
    
    // Skip if this is the same request as the last one
    if (lastRequestRef.current === requestSignature) {
      console.log('🔄 Skipping duplicate viewport request:', requestSignature);
      return;
    }
    
    console.log('🗺️ Fetching viewport alerts:', { bbox, dateRange });
    
    const startTime = performance.now();
    
    try {
      setIsLoading(true);
      setError(null);
      
      // Store this request signature
      lastRequestRef.current = requestSignature;
      
      const bboxParam = `${lat1},${lng1},${lat2},${lng2}`;
      const url = `/api/alerts/viewport?bbox=${bboxParam}&start_date=${start}&end_date=${end}&limit=10000`;
      
      console.log('📡 Making request to:', url);
      
      const response = await fetch(url, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`Viewport alerts request failed: ${response.status}`);
      }
      
      const data = await response.json();
      const endTime = performance.now();
      const roundTripTime = endTime - startTime;
      
      console.log('📥 Viewport alerts response:', {
        alertCount: data.alerts?.length || 0,
        performance: data.performance,
        roundTripTime: Math.round(roundTripTime)
      });
      
      // Measure map rendering performance
      const mapUpdateStart = performance.now();
      setAlerts(data.alerts || []);
      
      // Use requestAnimationFrame to measure actual render completion
      requestAnimationFrame(() => {
        const mapUpdateEnd = performance.now();
        const renderTime = mapUpdateEnd - mapUpdateStart;
        
        // Store comprehensive performance metrics as outlined in the strategy
        const metrics: PerformanceMetrics = {
          timestamp: new Date().toISOString(),
          bbox_area: calculateBboxArea(bbox),
          alert_count: data.alerts?.length || 0,
          backend_performance: data.performance,
          frontend_metrics: {
            round_trip_time_ms: Math.round(roundTripTime),
            render_time_ms: Math.round(renderTime),
            total_frontend_time_ms: Math.round(endTime - startTime + renderTime)
          }
        };
        
        // Keep last 20 performance measurements
        setPerformanceMetrics(prev => [...prev.slice(-19), metrics]);
        
        console.log('⚡ Performance metrics:', metrics);
      });
      
    } catch (err) {
      console.error('❌ Viewport fetch failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch viewport alerts');
      
      // Clear the request signature on error so retries can happen
      lastRequestRef.current = '';
    } finally {
      setIsLoading(false);
    }
  }, [calculateBboxArea]);

  // Stable debounced version with fixed delay to prevent request spam
  const debouncedFetchViewportAlerts = useCallback(
    debounce(async (bbox: BoundingBox, dateRange: DateRange) => {
      await fetchViewportAlerts(bbox, dateRange);
    }, DEBOUNCE_DELAY), // Fixed 500ms debounce window
    [fetchViewportAlerts]
  );

  // Clear alerts (useful for component unmounting or reset)
  const clearAlerts = useCallback(() => {
    setAlerts([]);
    setError(null);
    setIsLoading(false);
    lastRequestRef.current = '';
  }, []);

  const contextValue: ViewportAlertsContextType = {
    alerts,
    isLoading,
    error,
    performanceMetrics,
    fetchViewportAlerts,
    debouncedFetchViewportAlerts,
    clearAlerts,
    calculateBboxArea,
    viewportToBbox,
    mapToBbox,
  };

  return (
    <ViewportAlertsContext.Provider value={contextValue}>
      {children}
    </ViewportAlertsContext.Provider>
  );
};

export const useViewportAlerts = (): ViewportAlertsContextType => {
  const context = useContext(ViewportAlertsContext);
  if (context === undefined) {
    throw new Error('useViewportAlerts must be used within a ViewportAlertsProvider');
  }
  return context;
};

// Utility hook for converting time range hours to date range
export const useTimeRangeToDateRange = () => {
  return useCallback((timeRangeHours: number): DateRange => {
    const now = new Date();
    const startDate = new Date(now.getTime() - (timeRangeHours * 60 * 60 * 1000));
    
    const formatDate = (date: Date): string => {
      return date.toISOString().split('T')[0]; // YYYY-MM-DD format
    };
    
    return {
      start: formatDate(startDate),
      end: formatDate(now),
    };
  }, []);
};

// Note: Individual interfaces are already exported above where they're defined
