// frontend/src/hooks/useAlerts.ts
import { useState, useEffect, useCallback, useMemo } from "react";
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
  pollInterval?: number; // How often to refresh data
  limit?: number; // Max number of alerts to load
  hours?: number; // How many hours back to fetch
}

// Minimal normalization for optimized backend payload
const normalizeAlert = (rawAlert: any): Alert => {
  const now = new Date().toISOString();
  // Backend now sends minimal, clean data - just pass through with fallbacks
  return {
    id: rawAlert.id || '',
    title: rawAlert.title || 'Untitled Alert',
    description: rawAlert.description || '',
    source: rawAlert.source || 'unknown',
    priority: rawAlert.priority || 'medium',
    status: rawAlert.status || 'active',
    timestamp: rawAlert.timestamp || now,
    coordinates: rawAlert.coordinates || { lat: 40.7589, lng: -73.9851 },
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
    pollInterval = 1800000, // 30 minutes
    limit = 50000, // High limit for map display
    hours = 4320, // Default to 6 months
  } = options;

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertsWithReports, setAlertsWithReports] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingReports, setIsLoadingReports] = useState(true);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);
  const [lastReportsFetch, setLastReportsFetch] = useState<Date | null>(null);

  // Keep track of alerts that are currently being investigated to prevent polling interference
  const [investigatingAlerts, setInvestigatingAlerts] = useState<Set<string>>(new Set());
  const [completedInvestigations, setCompletedInvestigations] = useState<
    Map<string, { reportUrl?: string; traceId?: string; investigationId?: string }>
  >(new Map());

  // Fetch alerts with reports
  const fetchAlertsWithReports = useCallback(async () => {
    try {
      setIsLoadingReports(true);

      const response = await fetch(`/api/alerts/reports?limit=40`, {
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

  // Fetch all alerts - simplified
  const fetchAlerts = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const startTime = performance.now();
      const response = await fetch(`/api/alerts/recent?limit=${limit}&hours=${hours}`, {
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

      // Normalize the alerts
      const normalizedAlerts = (data.alerts || []).map(normalizeAlert);

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

  // Auto-refresh alerts
  useEffect(() => {
    // Initial load
    fetchAlerts();
    fetchAlertsWithReports();

    // Set up staggered polling intervals
    const alertsInterval = setInterval(fetchAlerts, pollInterval); // 30 minutes
    const reportsInterval = setInterval(fetchAlertsWithReports, 720000); // 12 minutes (12 * 60 * 1000)

    return () => {
      clearInterval(alertsInterval);
      clearInterval(reportsInterval);
    };
  }, [fetchAlerts, fetchAlertsWithReports, pollInterval]);

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

  return {
    alerts,
    alertsWithReports,
    error,
    isLoading,
    isLoadingReports,
    lastFetch,
    lastReportsFetch,
    stats: alertStats,
    refetch: fetchAlerts,
    refetchAlert,
    getSingleAlert,
    generateReport,
    fetchAgentTrace,
    fetchAlertsWithReports,
  };
};
