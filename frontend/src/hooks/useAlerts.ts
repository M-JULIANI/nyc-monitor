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
  const normalizedAlert = {
    id: rawAlert.id || original.id || rawAlert.alert_id,
    title: rawAlert.title || original.title || rawAlert.topic,
    description: original.description || rawAlert.description || '',
    source: original.source || rawAlert.source === 'unknown' ? originalData.signals?.[0] || 'unknown' : rawAlert.source,
    priority: original.priority || rawAlert.priority || 'medium',
    status: rawAlert.status || original.status || 'active', // PRIORITIZE rawAlert.status
    
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
    
    // Investigation & Report fields - PRIORITIZE rawAlert fields
    reportUrl: rawAlert.report_url || original.report_url,
    traceId: rawAlert.trace_id || original.trace_id,
    investigationId: rawAlert.investigation_id || original.investigation_id,
  };

  return normalizedAlert;
};

export const useAlerts = (options: UseAlertsOptions = {}) => {
  const { 
    pollInterval = 1800000, // 30 minutes
    limit = 2000, // High limit for map display
    hours = 72 // Default to 24 hours if not provided
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
  const [completedInvestigations, setCompletedInvestigations] = useState<Map<string, { reportUrl?: string; traceId?: string; investigationId?: string }>>(new Map());

  // Fetch alerts with reports
  const fetchAlertsWithReports = useCallback(async () => {
    try {
      setIsLoadingReports(true);
      
      const token = localStorage.getItem('idToken');
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch(`/api/alerts/reports?limit=100`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
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
      console.error('Error fetching alerts with reports:', err);
      setIsLoadingReports(false);
      // Don't set main error state for reports-specific fetch failures
    }
  }, []);

  // Fetch all alerts - simplified
  const fetchAlerts = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const token = localStorage.getItem('idToken');
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch(`/api/alerts/recent?limit=${limit}&hours=${hours}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Normalize the alerts
      const normalizedAlerts = (data.alerts || []).map(normalizeAlert);
      
      // Preserve investigation status and data for alerts that are being investigated
      const alertsWithInvestigationData = normalizedAlerts.map((alert: Alert) => {
        // If this alert is being investigated locally, preserve its investigating status
        if (investigatingAlerts.has(alert.id)) {
          return { ...alert, status: 'investigating' as const };
        }
        
        // If this alert has completed investigation data in local state, merge it but preserve backend status
        const completedData = completedInvestigations.get(alert.id);
        if (completedData) {
          return { 
            ...alert, 
            // Don't override status - let backend status take precedence
            reportUrl: completedData.reportUrl || alert.reportUrl,
            traceId: completedData.traceId || alert.traceId,
            investigationId: completedData.investigationId || alert.investigationId
          };
        }
        
        return alert;
      });
      
      setAlerts(alertsWithInvestigationData);
      setLastFetch(new Date());
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts');
      setIsLoading(false);
      console.error('Error fetching alerts:', err);
    }
  }, [limit, hours, investigatingAlerts, completedInvestigations]);

  // Generate report for an alert using existing investigation endpoint
  const generateReport = useCallback(async (alertId: string): Promise<{ success: boolean; message: string; investigationId?: string }> => {
    try {
      const token = localStorage.getItem('idToken');
      if (!token) {
        throw new Error('Authentication required');
      }

      // Check if investigation is already in progress
      if (investigatingAlerts.has(alertId)) {
        console.log(`Investigation already in progress for alert ${alertId}`);
        return {
          success: false,
          message: 'Investigation already in progress'
        };
      }

      // Find the alert to get its data
      const alert = alerts.find(a => a.id === alertId);
      if (!alert) {
        throw new Error('Alert not found');
      }

      // Mark alert as being investigated
      setInvestigatingAlerts(prev => new Set(prev).add(alertId));

      // Update alert status to investigating
      setAlerts(prev => prev.map(a => 
        a.id === alertId 
          ? { ...a, status: 'investigating' as const }
          : a
      ));

      // Use existing investigation endpoint
      const investigationRequest = {
        alert_id: alert.id,
        severity: alert.severity || 5,
        event_type: alert.category || 'general',
        location: `${alert.neighborhood}, ${alert.borough}`.replace('Unknown, ', '').replace(', Unknown', ''),
        summary: alert.description,
        timestamp: alert.timestamp,
        sources: [alert.source]
      };

      console.log(`Starting investigation for alert ${alertId}:`, investigationRequest);

      const response = await fetch('/api/investigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(investigationRequest),
      });

      if (!response.ok) {
        throw new Error(`Investigation failed: ${response.status}`);
      }

      const result = await response.json();
      console.log(`Investigation completed for alert ${alertId}:`, result);
      
      // Remove from investigating set
      setInvestigatingAlerts(prev => {
        const newSet = new Set(prev);
        newSet.delete(alertId);
        return newSet;
      });

      // Store completed investigation data
      const investigationData = {
        reportUrl: result.report_url,
        traceId: result.trace_id || result.investigation_id,
        investigationId: result.investigation_id
      };
      
      setCompletedInvestigations(prev => new Map(prev).set(alertId, investigationData));

      // Update alert with investigation info - set status to resolved
      setAlerts(prev => prev.map(a => 
        a.id === alertId 
          ? { 
              ...a, 
              status: 'resolved' as const,  // Set to resolved when investigation completes
              investigationId: result.investigation_id,
              reportUrl: result.report_url,
              traceId: result.trace_id || result.investigation_id
            }
          : a
      ));

      console.log(`✅ Updated alert ${alertId} to resolved status with reportUrl: ${result.report_url}`);

      return {
        success: true,
        message: 'Investigation completed',
        investigationId: result.investigation_id
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate report';
      console.error(`Investigation failed for alert ${alertId}:`, err);
      
      // Remove from investigating set
      setInvestigatingAlerts(prev => {
        const newSet = new Set(prev);
        newSet.delete(alertId);
        return newSet;
      });

      // Update alert status to failed
      setAlerts(prev => prev.map(a => 
        a.id === alertId 
          ? { ...a, status: 'active' as const }
          : a
      ));

      return {
        success: false,
        message: errorMessage
      };
    }
  }, [alerts, investigatingAlerts]);

  // Fetch agent trace for an alert using existing trace endpoint
  const fetchAgentTrace = useCallback(async (investigationId: string): Promise<{ success: boolean; trace?: string; message: string }> => {
    try {
      const token = localStorage.getItem('idToken');
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await fetch(`/api/investigate/${investigationId}/trace/export`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
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
        message: 'Trace fetched successfully'
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch trace';
      return {
        success: false,
        message: errorMessage
      };
    }
  }, []);

  // Refetch a single alert by ID and update it in the local state
  const refetchAlert = useCallback(async (alertId: string): Promise<{ success: boolean; message: string; alert?: Alert }> => {
    try {
      const token = localStorage.getItem('idToken');
      if (!token) {
        throw new Error('Authentication required');
      }

      console.log(`🔄 Refetching alert ${alertId}...`);

      const response = await fetch(`/api/alerts/get/${alertId}?_t=${Date.now()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Cache-Control': 'no-cache',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Alert not found');
        }
        throw new Error(`Failed to fetch alert: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.found || !data.alert) {
        throw new Error('Alert not found in response');
      }

      // Normalize the single alert
      const normalizedAlert = normalizeAlert(data.alert);
      
      // Only update if the data actually changed (avoid unnecessary re-renders)
      setAlerts(prev => {
        const existingAlert = prev.find(a => a.id === alertId);
        
        // Compare key fields that matter for the UI
        const hasChanges = !existingAlert || 
          existingAlert.status !== normalizedAlert.status ||
          existingAlert.reportUrl !== normalizedAlert.reportUrl ||
          existingAlert.traceId !== normalizedAlert.traceId ||
          existingAlert.investigationId !== normalizedAlert.investigationId;
        
        if (!hasChanges) {
          console.log(`📋 No changes detected for alert ${alertId}, skipping update`);
          return prev; // Return same reference to prevent re-renders
        }
        
        console.log(`📋 Changes detected for alert ${alertId}, updating collection`);
        return prev.map(a => a.id === alertId ? normalizedAlert : a);
      });

      console.log(`✅ Successfully refetched and updated alert ${alertId}`);

      return {
        success: true,
        message: 'Alert refetched successfully',
        alert: normalizedAlert
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refetch alert';
      console.error(`❌ Failed to refetch alert ${alertId}:`, err);
      return {
        success: false,
        message: errorMessage
      };
    }
  }, []);

  // Helper function to format trace data as markdown
  const formatTraceAsMarkdown = (traceData: any): string => {
    if (!traceData) return 'No trace data available';
    
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
      markdown += '```json\n';
      markdown += JSON.stringify(traceData, null, 2);
      markdown += '\n```\n';
      
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
    alertsWithReports,
    error, 
    isLoading,
    isLoadingReports,
    lastFetch,
    lastReportsFetch,
    stats: alertStats,
    refetch: fetchAlerts,
    refetchAlert,
    generateReport,
    fetchAgentTrace,
    fetchAlertsWithReports
  };
};