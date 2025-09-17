// frontend/src/hooks/useAlerts.ts
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Alert } from "../types";

// Import performance tracking from AlertStatsContext
const recordPerformanceMetric = (metric: {
  endpoint: string;
  method: string;
  roundTripTime: number;
  cached: boolean;
  alertCount?: number;
  timestamp: number;
}) => {
  // Simple global tracking - will be picked up by PerformancePanel
  if (typeof window !== 'undefined' && (window as any).performanceMetrics) {
    (window as any).performanceMetrics.unshift(metric);
    (window as any).performanceMetrics = (window as any).performanceMetrics.slice(0, 99);
  }
};

interface UseAlertsOptions {
  limit?: number; // Max number of alerts to load
  hours?: number; // How many hours back to fetch
  useStreaming?: boolean; // Whether to use streaming endpoint
  chunkSize?: number; // Chunk size for streaming
}

// NYC bounding box - precise boundaries including all 5 boroughs
const NYC_BOUNDS = {
  minLat: 40.477399, // Southern tip of Staten Island
  maxLat: 40.917577, // Northern Bronx
  minLng: -74.259090, // Westernmost point (Staten Island)
  maxLng: -73.700272, // Easternmost point (Queens)
};

// Check if coordinates are within NYC bounds
const isWithinNYC = (lat: number, lng: number): boolean => {
  return (
    lat >= NYC_BOUNDS.minLat &&
    lat <= NYC_BOUNDS.maxLat &&
    lng >= NYC_BOUNDS.minLng &&
    lng <= NYC_BOUNDS.maxLng
  );
};

// Check if coordinates are valid (not zero, not null, not NaN)
const isValidCoordinate = (lat: number, lng: number): boolean => {
  return (
    typeof lat === 'number' &&
    typeof lng === 'number' &&
    !isNaN(lat) &&
    !isNaN(lng) &&
    lat !== 0 &&
    lng !== 0 &&
    Math.abs(lat) <= 90 &&
    Math.abs(lng) <= 180
  );
};

// Minimal normalization for optimized backend payload
const normalizeAlert = (rawAlert: any): Alert | null => {
  const now = new Date().toISOString();
  
  // Extract coordinates and validate them
  const coords = rawAlert.coordinates || {};
  const lat = typeof coords.lat === 'number' ? coords.lat : parseFloat(coords.lat);
  const lng = typeof coords.lng === 'number' ? coords.lng : parseFloat(coords.lng);
  
  // Skip alerts with invalid coordinates or coordinates outside NYC
  if (!isValidCoordinate(lat, lng) || !isWithinNYC(lat, lng)) {
    console.debug(`🚫 Filtering out alert ${rawAlert.id}: invalid coordinates (${lat}, ${lng}) or outside NYC bounds`);
    return null;
  }
  
  // Backend now sends minimal, clean data - just pass through with fallbacks
  return {
    id: rawAlert.id || '',
    title: rawAlert.title || 'Untitled Alert',
    description: rawAlert.description || '',
    source: rawAlert.source || 'unknown',
    priority: rawAlert.priority || 'medium',
    status: rawAlert.status || 'active',
    timestamp: rawAlert.timestamp || now,
    coordinates: { lat, lng }, // Use validated coordinates
    neighborhood: rawAlert.neighborhood || 'Unknown',
    borough: rawAlert.borough || 'Unknown',
    category: rawAlert.category || 'general',
    // Required date fields
    event_date: rawAlert.event_date || rawAlert.timestamp || now,
    created_at: rawAlert.created_at || now,
    updated_at: rawAlert.updated_at || now,
    // Add optional fields with defaults
    reportUrl: rawAlert.reportUrl,
    traceId: rawAlert.traceId,
    investigationId: rawAlert.investigationId,
  };
};

export const useAlerts = (options: UseAlertsOptions = {}) => {
  const {
    limit = 50000, // High limit for map display
    hours = 4320, // Default to 6 months
    useStreaming, // Default to non-streaming
    chunkSize = 200, // Default chunk size (kept smaller to prevent SSE payload truncation)
  } = options;

  // Main alerts dataset - full collection for map visualization and analytics (up to 50k alerts)
  const [alerts, setAlerts] = useState<Alert[]>([]);
  
  // Curated reports dataset - only alerts with completed investigation reports (limited to ~20 items)
  // Used specifically for the Dashboard component to showcase finished investigations
  const [alertsWithReports, setAlertsWithReports] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingReports, setIsLoadingReports] = useState(true);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);
  const [lastReportsFetch, setLastReportsFetch] = useState<Date | null>(null);
  
  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isComputingCharts, setIsComputingCharts] = useState(false);
  const [streamingProgress, setStreamingProgress] = useState({
    currentChunk: 0,
    totalChunks: 0,
    totalAlerts: 0,
    estimatedTotal: 0,
    progressPercent: 0,
    source: '',
    isComplete: false
  });
  const [streamController, setStreamController] = useState<AbortController | null>(null);
  const [streamingFailures, setStreamingFailures] = useState<number>(0);
  const streamingInProgress = useRef<boolean>(false);

  // Keep track of alerts that are currently being investigated
  const [investigatingAlerts, setInvestigatingAlerts] = useState<Set<string>>(new Set());
  const [completedInvestigations, setCompletedInvestigations] = useState<
    Map<string, { reportUrl?: string; traceId?: string; investigationId?: string }>
  >(new Map());

  /**
   * Fetches alerts that have completed investigation reports.
   * This is a separate, smaller dataset optimized for the Dashboard component.
   * 
   * @param reportLimit Maximum number of reports to fetch (default: 20)
   */
  const fetchAlertsWithReports = useCallback(async (reportLimit: number = 20) => {
    try {
      setIsLoadingReports(true);

      const response = await fetch(`/api/alerts/reports?limit=${reportLimit}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch alerts with reports: ${response.status}`);
      }

      const data = await response.json();

      // Don't normalize - the reports endpoint already returns clean minimal data
      const alerts = data.alerts || [];

      setAlertsWithReports(alerts);
      setLastReportsFetch(new Date());
      setIsLoadingReports(false);
    } catch (err) {
      console.error("Error fetching alerts with reports:", err);
      setIsLoadingReports(false);
      // Don't set main error state for reports-specific fetch failures
    }
  }, []);

  /**
   * Streams the main alerts dataset using Server-Sent Events.
   * This populates the primary `alerts` array with the full dataset for map/analytics.
   */
  const streamAlerts = useCallback(async () => {
    if (isStreaming || streamingInProgress.current) {
      console.warn('Stream already in progress, skipping...');
      return;
    }

    // Additional safety check - abort any existing controller
    if (streamController) {
      console.log('Aborting existing stream controller...');
      streamController.abort();
      setStreamController(null);
    }

    try {
      // Prevent starting a new stream if one just completed successfully
      if (alerts.length > 0 && !isLoading && !error) {
        console.log('⏭️ Skipping stream - data already loaded successfully');
        return;
      }

      streamingInProgress.current = true;
      setIsLoading(true);
      setIsConnecting(true);
      setIsStreaming(false); // Not streaming yet, just connecting
      setError(null);
      setAlerts([]); // Clear existing alerts for fresh stream
      setStreamingProgress({
        currentChunk: 0,
        totalChunks: 0,
        totalAlerts: 0,
        estimatedTotal: 0,
        progressPercent: 0,
        source: 'Connecting...',
        isComplete: false
      });

      // Create abort controller for cancellation
      const controller = new AbortController();
      setStreamController(controller);

      const startTime = performance.now();
      // Ensure chunk size doesn't exceed safe SSE limits (max ~200 alerts per chunk to be safe)
      const safeChunkSize = Math.min(chunkSize, 200);
      const eventSource = new EventSource(`/api/alerts/recent/stream?hours=${hours}&chunk_size=${safeChunkSize}`);

      eventSource.onmessage = (event) => {
        if (controller.signal.aborted) {
          eventSource.close();
          return;
        }

        try {
          // Add debugging for malformed JSON
          if (!event.data || event.data.trim() === '') {
            console.warn('⚠️ Received empty EventSource data, skipping...');
            return;
          }
          
          // Clean the SSE data - remove 'data: ' prefix if present
          let eventData = event.data.trim();
          if (eventData.startsWith('data: ')) {
            eventData = eventData.substring(6).trim();
          }
          
          // Check for truncated JSON (common with large SSE payloads)
          if (!eventData.endsWith('}') && !eventData.endsWith(']')) {
            console.warn('⚠️ Received truncated JSON data, skipping chunk:', eventData.slice(0, 100) + '...');
            return;
          }
          
          // Additional validation - ensure it looks like JSON
          if (!eventData.startsWith('{') && !eventData.startsWith('[')) {
            console.warn('⚠️ Invalid JSON format detected, skipping:', eventData.slice(0, 100) + '...');
            return;
          }
          
          const data = JSON.parse(eventData);

          switch (data.type) {
            case 'start':
              console.log('🚀 Starting alert stream:', data);
              setIsConnecting(false);
              setIsStreaming(true);
              setStreamingProgress(prev => ({
                ...prev,
                source: 'Starting...'
              }));
              break;

            case 'count':
              setStreamingProgress(prev => ({
                ...prev,
                estimatedTotal: data.estimated_total,
                progressPercent: 0,
                source: data.estimated_total > 0 ? `Estimated ${data.estimated_total} alerts` : 'Counting...'
              }));
              break;

            case 'chunk':
              // const beforeFiltering = data.alerts.length;
               const normalizedChunkAlerts = data.alerts.map(normalizeAlert).filter(Boolean) as Alert[];
              // const afterFiltering = normalizedChunkAlerts.length;
             // const filteredCount = beforeFiltering - afterFiltering;
              
              // if (filteredCount > 0) {
              //   console.log(`🚫 Filtered out ${filteredCount}/${beforeFiltering} alerts from ${data.source} chunk (outside NYC bounds or invalid coordinates)`);
              // }
              
              setAlerts(prev => [...prev, ...normalizedChunkAlerts]);
              setStreamingProgress(prev => {
                const newTotalAlerts = data.total_so_far;
                const progressPercent = prev.estimatedTotal > 0 
                  ? Math.min(Math.round((newTotalAlerts / prev.estimatedTotal) * 100), 100)
                  : Math.min(Math.round((newTotalAlerts / 10) * 100), 100); // Show progress even without estimated total
                
                return {
                  ...prev,
                  currentChunk: data.chunk,
                  totalChunks: Math.max(prev.totalChunks, data.chunk),
                  totalAlerts: newTotalAlerts,
                  progressPercent,
                  source: `${data.source} - ${newTotalAlerts}${prev.estimatedTotal > 0 ? `/${prev.estimatedTotal}` : ''} alerts`
                };
              });
              break;

            case 'complete':
              const endTime = performance.now();
              
              setStreamingProgress(prev => ({
                ...prev,
                isComplete: true,
                totalChunks: data.total_chunks,
                totalAlerts: data.total_alerts,
                progressPercent: 100,
                source: `Complete - ${data.total_alerts} alerts loaded`
              }));

              // Record performance metric
              recordPerformanceMetric({
                endpoint: `/api/alerts/recent/stream?hours=${hours}&chunk_size=${safeChunkSize}`,
                method: 'GET',
                roundTripTime: endTime - startTime,
                cached: false,
                alertCount: data.total_alerts,
                timestamp: Date.now()
              });

              // Mark streaming as complete - map/dashboard can be interactive now
              setIsStreaming(false);
              setIsConnecting(false);
              setIsLoading(false); // Allow map/dashboard to be interactive immediately
              setIsComputingCharts(true); // Start chart computation phase for Insights only
              setLastFetch(new Date());
              eventSource.close();
              setStreamController(null);
              streamingInProgress.current = false;
              
              // Reset failure counter on successful completion
              setStreamingFailures(0);

              console.log(`✅ Stream complete: ${data.total_alerts} alerts in ${data.total_chunks} chunks - starting chart computation`);
              break;

            case 'error':
              console.error('❌ Stream error:', data);
              setError(`Streaming error (${data.source}): ${data.message}`);
              setIsConnecting(false);
              setIsStreaming(false);
              break;
          }
        } catch (err) {
          console.error('Failed to parse stream data:', err);
          console.error('Raw event data length:', event.data?.length || 0);
          console.error('Raw event data preview:', event.data?.slice(0, 200) + '...');
          console.error('Raw event data ending:', '...' + event.data?.slice(-100));
          
          // Log the cleaned data for debugging
          let cleanedData = event.data?.trim() || '';
          if (cleanedData.startsWith('data: ')) {
            cleanedData = cleanedData.substring(6).trim();
          }
          console.error('Cleaned data preview:', cleanedData.slice(0, 200) + '...');
          console.error('Cleaned data ending:', '...' + cleanedData.slice(-100));
          
          // Check if this looks like a truncation issue
          if (event.data && event.data.length > 1000 && !cleanedData.endsWith('}')) {
            console.warn('🔥 This appears to be a truncated SSE payload. Consider reducing chunk_size.');
          }
          
          // Don't treat JSON parse errors as fatal - continue streaming
        }
      };

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        setStreamingFailures(prev => prev + 1);
        
        // If streaming fails repeatedly, fall back to regular fetch
        if (streamingFailures >= 2) {
          console.warn('🔄 Multiple streaming failures detected, falling back to regular fetch...');
          setError('Streaming failed, switching to regular fetch');
          eventSource.close();
          setStreamController(null);
          setIsStreaming(false);
          setIsConnecting(false);
          streamingInProgress.current = false;
          // Trigger regular fetch as fallback
          fetchAlerts();
          return;
        }
        
        setError('Connection lost during streaming');
        setIsLoading(false);
        setIsStreaming(false);
        setIsConnecting(false);
        eventSource.close();
        setStreamController(null);
        streamingInProgress.current = false;
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start streaming");
      setIsLoading(false);
      setIsStreaming(false);
      setIsConnecting(false);
      setStreamController(null);
      streamingInProgress.current = false;
      console.error("Error starting stream:", err);
    }
  }, [hours, chunkSize]);

  // Cancel streaming
  const cancelStreaming = useCallback(() => {
    if (streamController) {
      streamController.abort();
      setStreamController(null);
      setIsStreaming(false);
      setIsConnecting(false);
      setIsLoading(false);
      streamingInProgress.current = false;
      console.log('🛑 Stream cancelled by user');
    }
  }, [streamController]);

  /**
   * Fetches the main alerts dataset via REST API.
   * This populates the primary `alerts` array with the full dataset for map/analytics.
   */
  const fetchAlerts = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const startTime = performance.now();
      //fallback to 5000 alerts
      const response = await fetch(`/api/alerts/recent?limit=${5000}&hours=${hours}`, {
        credentials: 'include',
      });
      const endTime = performance.now();

      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.status}`);
      }

      const data = await response.json();

      // Record performance metric
      recordPerformanceMetric({
        endpoint: `/api/alerts/recent?limit=${limit}&hours=${hours}`,
        method: 'GET',
        roundTripTime: endTime - startTime,
        cached: data.performance?.cached || false,
        alertCount: data.count || data.alerts?.length || 0,
        timestamp: Date.now()
      });

      // Normalize the alerts and filter out nulls (invalid coordinates)
     // const beforeFiltering = (data.alerts || []).length;
      const normalizedAlerts = (data.alerts || []).map(normalizeAlert).filter(Boolean) as Alert[];
     // const filteredCount = beforeFiltering - normalizedAlerts.length;
      
      // if (filteredCount > 0) {
      //   console.log(`🚫 Filtered out ${filteredCount}/${beforeFiltering} alerts during regular fetch (outside NYC bounds or invalid coordinates)`);
      // }

      // Preserve investigation status and data for alerts that are being investigated
      const alertsWithInvestigationData = normalizedAlerts.map((alert: Alert) => {
        // If this alert is being investigated locally, preserve its investigating status
        if (investigatingAlerts.has(alert.id)) {
          return { ...alert, status: "investigating" as const };
        }

        // If this alert has completed investigation data in local state, merge it but preserve backend status
        const completedData = completedInvestigations.get(alert.id);
        if (completedData) {
          return {
            ...alert,
            // Don't override status - let backend status take precedence
            reportUrl: completedData.reportUrl || alert.reportUrl,
            traceId: completedData.traceId || alert.traceId,
            investigationId: completedData.investigationId || alert.investigationId,
          };
        }

        return alert;
      });

      setAlerts(alertsWithInvestigationData);
      setLastFetch(new Date());
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
      setIsLoading(false);
      console.error("Error fetching alerts:", err);
    }
  }, [limit, hours, investigatingAlerts, completedInvestigations]);

  // Generate report for an alert using existing investigation endpoint
  const generateReport = useCallback(
    async (alertId: string): Promise<{ success: boolean; message: string; investigationId?: string }> => {
      try {
        // Check if investigation is already in progress
        if (investigatingAlerts.has(alertId)) {
          //console.log(`Investigation already in progress for alert ${alertId}`);
          return {
            success: false,
            message: "Investigation already in progress",
          };
        }

        // Find the alert to get its data
        const alert = alerts.find((a) => a.id === alertId);
        if (!alert) {
          throw new Error("Alert not found");
        }

        // Mark alert as being investigated
        setInvestigatingAlerts((prev) => new Set(prev).add(alertId));

        // Update alert status to investigating
        setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status: "investigating" as const } : a)));

        // Use existing investigation endpoint
        const investigationRequest = {
          alert_id: alert.id,
          severity: alert.severity || 5,
          priority: alert.priority || "medium",
          event_type: alert.category || "general",
          location: `${alert.neighborhood}, ${alert.borough}`.replace("Unknown, ", "").replace(", Unknown", ""),
          summary: alert.description,
          timestamp: alert.timestamp,
          sources: [alert.source],
        };

        //console.log(`Starting investigation for alert ${alertId}:`, investigationRequest);

        const response = await fetch("/api/investigate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: 'include',
          body: JSON.stringify(investigationRequest),
        });

        if (!response.ok) {
          throw new Error(`Investigation failed: ${response.status}`);
        }

        const result = await response.json();
        //console.log(`Investigation completed for alert ${alertId}:`, result);

        // Remove from investigating set
        setInvestigatingAlerts((prev) => {
          const newSet = new Set(prev);
          newSet.delete(alertId);
          return newSet;
        });

        // Store completed investigation data
        const investigationData = {
          reportUrl: result.report_url,
          traceId: result.trace_id || result.investigation_id,
          investigationId: result.investigation_id,
        };

        setCompletedInvestigations((prev) => new Map(prev).set(alertId, investigationData));

        // Update alert with investigation info - ONLY set to resolved if we have a report URL
        const newStatus = result.report_url ? "resolved" : "active";
        setAlerts((prev) =>
          prev.map((a) =>
            a.id === alertId
              ? {
                  ...a,
                  status: newStatus,
                  investigationId: result.investigation_id,
                  reportUrl: result.report_url,
                  traceId: result.trace_id || result.investigation_id,
                }
              : a,
          ),
        );

        // console.log(`✅ Updated alert ${alertId} to ${newStatus} status with reportUrl: ${result.report_url}`);

        return {
          success: true,
          message: "Investigation completed",
          investigationId: result.investigation_id,
        };
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to generate report";
        console.error(`Investigation failed for alert ${alertId}:`, err);

        // Remove from investigating set
        setInvestigatingAlerts((prev) => {
          const newSet = new Set(prev);
          newSet.delete(alertId);
          return newSet;
        });

        // Update alert status to failed
        setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status: "active" as const } : a)));

        return {
          success: false,
          message: errorMessage,
        };
      }
    },
    [alerts, investigatingAlerts],
  );

  // Fetch agent trace for an alert using existing trace endpoint
  const fetchAgentTrace = useCallback(
    async (investigationId: string): Promise<{ success: boolean; trace?: string; message: string }> => {
      try {
        const response = await fetch(`/api/investigate/${investigationId}/trace/export`, {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch trace: ${response.status}`);
        }

        const data = await response.json();

        // Convert trace data to markdown format
        const traceMarkdown = formatTraceAsMarkdown(data.trace_data);

        return {
          success: true,
          trace: traceMarkdown,
          message: "Trace fetched successfully",
        };
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to fetch trace";
        return {
          success: false,
          message: errorMessage,
        };
      }
    },
    [],
  );

  // Get a single hydrated alert by ID with full details
  const getSingleAlert = useCallback(
    async (alertId: string): Promise<{ success: boolean; message: string; alert?: Alert }> => {
      try {
        const startTime = performance.now();
        const response = await fetch(`/api/alerts/get/${alertId}`, {
          credentials: 'include',
        });
        const endTime = performance.now();

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Alert not found");
          }
          throw new Error(`Failed to fetch alert: ${response.status}`);
        }

        const data = await response.json();

        // Record performance metric
        recordPerformanceMetric({
          endpoint: `/api/alerts/get/${alertId}`,
          method: 'GET',
          roundTripTime: endTime - startTime,
          cached: data.performance?.cached || false,
          timestamp: Date.now()
        });

        if (!data.found || !data.alert) {
          throw new Error("Alert not found in response");
        }

        // Return the full hydrated alert data directly (backend already sends complete data)
        const hydratedAlert = {
          ...data.alert,
          id: alertId, // Ensure ID is set
        } as Alert;

        console.log(`✅ Retrieved hydrated alert ${alertId} with full details`);

        return {
          success: true,
          message: "Alert retrieved successfully",
          alert: hydratedAlert,
        };
      } catch (err) {
        const error = err as Error;
        console.error(`❌ Failed to get alert ${alertId}:`, error);

        return {
          success: false,
          message: error.message,
        };
      }
    },
    []
  );

  // Refetch a single alert by ID and update it in the local state
  const refetchAlert = useCallback(
    async (alertId: string): Promise<{ success: boolean; message: string; alert?: Alert }> => {
      try {
        //console.log(`🔄 Refetching alert ${alertId}...`);

        const response = await fetch(`/api/alerts/get/${alertId}?_t=${Date.now()}`, {
          headers: {
            "Cache-Control": "no-cache",
          },
          credentials: 'include',
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Alert not found");
          }
          throw new Error(`Failed to fetch alert: ${response.status}`);
        }

        const data = await response.json();

        if (!data.found || !data.alert) {
          throw new Error("Alert not found in response");
        }

        // Normalize the single alert
        const normalizedAlert = normalizeAlert(data.alert);
        
        if (!normalizedAlert) {
          throw new Error("Alert has invalid coordinates or is outside NYC bounds");
        }

        // Only update if the data actually changed (avoid unnecessary re-renders)
        setAlerts((prev) => {
          const existingAlert = prev.find((a) => a.id === alertId);

          // Compare key fields that matter for the UI
          const hasChanges =
            !existingAlert ||
            existingAlert.status !== normalizedAlert.status ||
            existingAlert.reportUrl !== normalizedAlert.reportUrl ||
            existingAlert.traceId !== normalizedAlert.traceId ||
            existingAlert.investigationId !== normalizedAlert.investigationId;

          if (!hasChanges) {
            //   console.log(`📋 No changes detected for alert ${alertId}, skipping update`);
            return prev; // Return same reference to prevent re-renders
          }

          //console.log(`📋 Changes detected for alert ${alertId}, updating collection`);
          return prev.map((a) => (a.id === alertId ? normalizedAlert : a));
        });

        //  console.log(`✅ Successfully refetched and updated alert ${alertId}`);

        return {
          success: true,
          message: "Alert refetched successfully",
          alert: normalizedAlert,
        };
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to refetch alert";
        console.error(`❌ Failed to refetch alert ${alertId}:`, err);
        return {
          success: false,
          message: errorMessage,
        };
      }
    },
    [],
  );

  // Helper function to format trace data as markdown
  const formatTraceAsMarkdown = (traceData: any): string => {
    if (!traceData) return "No trace data available";

    try {
      // Format the trace data as readable markdown
      let markdown = `# Investigation Trace\n\n`;

      if (traceData.investigation_id) {
        markdown += `**Investigation ID:** ${traceData.investigation_id}\n\n`;
      }

      if (traceData.approach) {
        markdown += `**Approach:** ${traceData.approach}\n\n`;
      }

      // Format the trace data structure
      markdown += `## Trace Data\n\n`;
      markdown += "```json\n";
      markdown += JSON.stringify(traceData, null, 2);
      markdown += "\n```\n";

      return markdown;
    } catch (err) {
      return `Error formatting trace data: ${err}`;
    }
  };

  // Load alerts once on mount - NO polling
  useEffect(() => {
    let mounted = true;
    
    // Initial load - use streaming if enabled
    const initialLoad = async () => {
      if (!mounted) return;
      
      if (useStreaming) {
        streamAlerts();
      } else {
        fetchAlerts();
      }
    };
    
    initialLoad();
    fetchAlertsWithReports();

    return () => {
      mounted = false;
    };
  }, []); // Only run once on mount

  // Separate effect for cleanup on unmount
  useEffect(() => {
    return () => {
      // Cancel any ongoing stream on unmount
      if (streamController) {
        streamController.abort();
      }
    };
  }, [streamController]);

  // Memoized stats
  const alertStats = useMemo(() => {
    const total = alerts.length;
    const byPriority = alerts.reduce((acc, alert) => {
      acc[alert.priority || "medium"] = (acc[alert.priority || "medium"] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const byStatus = alerts.reduce((acc, alert) => {
      acc[alert.status || "active"] = (acc[alert.status || "active"] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const bySource = alerts.reduce((acc, alert) => {
      acc[alert.source || "unknown"] = (acc[alert.source || "unknown"] || 0) + 1;
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
      resolved: byStatus.resolved || 0,
    };
  }, [alerts]);

  // Memoized chart data for Insights component - computed once and cached
  // Only compute chart data when streaming is complete or not using streaming
  const chartData = useMemo(() => {
    // Don't compute expensive chart data while streaming is in progress or if streaming just completed
    if (isStreaming || (streamingProgress.isComplete && isComputingCharts)) {
      return { categoryData: [], timeData: [], priorityData: [], dateInfo: [], debugInfo: null };
    }
    
    if (!alerts.length) return { categoryData: [], timeData: [], priorityData: [], dateInfo: [], debugInfo: null };

    // Day names array
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    // Category colors for consistent theming
    const categoryColors = {
      infrastructure: "#3b82f6", // blue
      emergency: "#ef4444", // red
      transportation: "#8b5cf6", // purple
      events: "#ec4899", // pink
      safety: "#f97316", // orange
      environment: "#10b981", // green
      housing: "#eab308", // yellow
      general: "#6b7280", // gray
    };

    // Debug: Log alert timestamps to understand date range
    const timestamps = alerts.map((alert) => new Date(alert.timestamp));
    const minDate = new Date(Math.min(...timestamps.map((d) => d.getTime())));
    const maxDate = new Date(Math.max(...timestamps.map((d) => d.getTime())));

    // Category breakdown
    const categoryCount = alerts.reduce((acc, alert) => {
      const category = alert.category || "general";
      acc[category] = (acc[category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const categoryData = Object.entries(categoryCount).map(([category, count]) => ({
      name: category.charAt(0).toUpperCase() + category.slice(1),
      value: count,
      color: categoryColors[category as keyof typeof categoryColors] || "#6b7280",
    }));

    // Get unique dates from alerts and sort them chronologically
    const uniqueDates = [
      ...new Set(
        alerts.map((alert) => {
          const date = new Date(alert.timestamp);
          return date.toDateString(); // This gives us "Mon Jan 01 2024" format
        }),
      ),
    ].sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

    // Create date info for X-axis
    const dateInfo = uniqueDates.map((dateStr, index) => {
      const date = new Date(dateStr);
      const alertsOnThisDate = alerts.filter((alert) => new Date(alert.timestamp).toDateString() === dateStr).length;

      return {
        index,
        dateStr,
        shortLabel: `${date.getMonth() + 1}/${date.getDate()}`, // MM/DD format
        dayName: dayNames[date.getDay()],
        alertCount: alertsOnThisDate,
      };
    });

    // Time-based scatter plot data with intelligent clustering prevention
    const timeData = alerts.map((alert, alertIndex) => {
      const date = new Date(alert.timestamp);
      const dateStr = date.toDateString();
      const dateIndex = uniqueDates.indexOf(dateStr);
      const hourOfDay = date.getHours();

      return {
        originalX: dateIndex,
        originalY: hourOfDay,
        category: alert.category || "general",
        title: alert.title,
        priority: alert.priority,
        color: categoryColors[alert.category as keyof typeof categoryColors] || "#6b7280",
        alert: alert,
        alertIndex, // Store original index for stable jitter
      };
    });

    // Apply intelligent spreading to prevent clustering
    const maxDateIndex = uniqueDates.length - 1;
    const spreadTimeData = timeData.map((point) => {
      // Scale the position to use more chart width (map 0-2 to 0-10 for better spacing)
      const scaleFactor = maxDateIndex > 0 ? 10 / maxDateIndex : 1;
      const scaledOriginalX = point.originalX * scaleFactor;

      // Find all points with same or very similar coordinates
      const similarPoints = timeData.filter(
        (p) => Math.abs(p.originalX - point.originalX) < 0.1 && Math.abs(p.originalY - point.originalY) < 0.5, // Smaller tolerance for hour grouping
      );

      if (similarPoints.length <= 1) {
        // If no clustering, just add small horizontal jitter only
        return {
          ...point,
          x: scaledOriginalX + (Math.random() - 0.5) * 0.5,
          y: point.originalY, // Keep exact hour - no vertical jitter
        };
      }

      // For clustered points, spread them out horizontally only
      const pointIndex = similarPoints.findIndex((p) => p.alertIndex === point.alertIndex);
      const totalSimilar = similarPoints.length;

      // Create horizontal spread pattern for clustered points
      const horizontalSpread = (pointIndex - totalSimilar / 2) * 0.15; // Systematic horizontal spacing

      // Add some horizontal randomness to avoid perfect lines
      const randomX = (Math.random() - 0.5) * 0.2;

      return {
        ...point,
        x: scaledOriginalX + horizontalSpread + randomX,
        y: point.originalY, // Keep exact hour - preserve time accuracy
      };
    });

    // Priority breakdown
    const priorityCount = alerts.reduce((acc, alert) => {
      acc[alert.priority] = (acc[alert.priority] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const priorityData = Object.entries(priorityCount).map(([priority, count]) => ({
      name: priority.charAt(0).toUpperCase() + priority.slice(1),
      value: count,
      color:
        priority === "critical"
          ? "#ef4444"
          : priority === "high"
          ? "#f97316"
          : priority === "medium"
          ? "#eab308"
          : "#10b981",
    }));

    const debugInfo = {
      totalAlerts: alerts.length,
      dateRange: { minDate: minDate.toDateString(), maxDate: maxDate.toDateString() },
      uniqueDates: uniqueDates.length,
      pointsGenerated: spreadTimeData.length,
    };

    return { categoryData, timeData: spreadTimeData, priorityData, dateInfo, debugInfo };
  }, [alerts, isStreaming, streamingProgress.isComplete, isComputingCharts]);

  // Effect to trigger chart computation after streaming completes
  useEffect(() => {
    if (streamingProgress.isComplete && isComputingCharts && alerts.length > 0) {
      // Use setTimeout to allow the chart computation to happen in the next tick
      const computeCharts = setTimeout(() => {
        setIsComputingCharts(false); // Only affects Insights tab availability
      }, 100); // Small delay to ensure chart computation happens

      return () => clearTimeout(computeCharts);
    }
  }, [streamingProgress.isComplete, isComputingCharts, alerts.length]);

  return {
    alerts,
    alertsWithReports,
    error,
    isLoading,
    isLoadingReports,
    lastFetch,
    lastReportsFetch,
    stats: alertStats,
    chartData, // Pre-computed chart data for Insights
    refetch: useStreaming ? streamAlerts : fetchAlerts,
    refetchAlert,
    getSingleAlert,
    generateReport,
    fetchAgentTrace,
    fetchAlertsWithReports,
    // Streaming-specific state and methods
    isStreaming,
    isConnecting,
    isComputingCharts,
    streamingProgress,
    streamAlerts,
    cancelStreaming,
    // Dashboard optimization - separate reports fetch with configurable limit
    fetchReportsForDashboard: () => fetchAlertsWithReports(15), // Faster for dashboard
  };
};
