import { useEffect, useCallback, useRef } from 'react';
import { debounce } from 'lodash';
import { useViewportAlerts, useTimeRangeToDateRange } from '../contexts/ViewportAlertsContext';
import { useMapState } from '../contexts/MapStateContext';
import type { Map as MapboxMap } from 'mapbox-gl';

/**
 * Custom hook that integrates viewport-based alert fetching with map state
 * Implements the enhanced alert serving strategy with automatic viewport tracking
 * 
 * @param mapRef - Optional Mapbox map reference for accurate bounds calculation
 */
export const useMapViewportAlerts = (mapRef?: React.RefObject<any>) => {
  const { viewport, filter } = useMapState();
  const { 
    alerts, 
    isLoading, 
    error, 
    performanceMetrics, 
    debouncedFetchViewportAlerts,
    viewportToBbox,
    mapToBbox
  } = useViewportAlerts();
  const timeRangeToDateRange = useTimeRangeToDateRange();

  // Convert current filter time range to date range
  const dateRange = timeRangeToDateRange(filter.timeRangeHours);

  // Trigger viewport-based fetch when viewport or time filter changes
  const handleViewportUpdate = useCallback(() => {
    // Prefer Mapbox native bounds if map reference is available
    let bbox;
    if (mapRef?.current) {
      const map: MapboxMap = mapRef.current.getMap();
      bbox = mapToBbox(map, 0.01); // Small padding to ensure coverage
      console.log('🗺️ Using Mapbox native bounds:', bbox);
    } else {
      bbox = viewportToBbox(viewport, 0.01); // Fallback to viewport calculation
      console.log('🗺️ Using fallback viewport bounds:', bbox);
    }
    
    console.log('🗺️ Viewport changed, will debounce fetch:', {
      viewport: { lat: viewport.latitude.toFixed(4), lng: viewport.longitude.toFixed(4), zoom: viewport.zoom.toFixed(1) },
      bbox: { lat1: bbox.lat1.toFixed(4), lng1: bbox.lng1.toFixed(4), lat2: bbox.lat2.toFixed(4), lng2: bbox.lng2.toFixed(4) },
      timeRangeHours: filter.timeRangeHours,
      usingMapRef: !!mapRef?.current
    });
    
    // Use stable debounced fetch to prevent excessive API calls during map interactions
    debouncedFetchViewportAlerts(bbox, dateRange);
  }, [viewport, dateRange, filter.timeRangeHours, mapRef, mapToBbox, viewportToBbox, debouncedFetchViewportAlerts]);

  // Effect to trigger fetch when dependencies change
  useEffect(() => {
    handleViewportUpdate();
  }, [handleViewportUpdate]);

  // Return the data and utilities needed by MapView
  return {
    // Alert data from viewport endpoint
    viewportAlerts: alerts,
    isLoadingViewport: isLoading,
    viewportError: error,
    
    // Performance tracking
    performanceMetrics,
    
    // Utility functions
    triggerViewportUpdate: handleViewportUpdate,
    
    // Debug info
    currentDateRange: dateRange,
    currentViewport: viewport,
  };
};
