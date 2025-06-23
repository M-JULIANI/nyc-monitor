import { Alert } from '../types';

export interface ReportServiceDependencies {
  generateReport: (alertId: string) => Promise<{ success: boolean; message: string; investigationId?: string }>;
  isConnected?: boolean;
  generatingReports?: Set<string>;
  setGeneratingReports?: (updater: (prev: Set<string>) => Set<string>) => void;
  onSuccess?: (result: { success: boolean; message: string; investigationId?: string }) => void;
  onError?: (error: any, message: string) => void;
}

export interface ReportGenerationOptions {
  showUserAlerts?: boolean; // Whether to show window.alert() for errors
  logToConsole?: boolean;   // Whether to log to console
  manageLoadingState?: boolean; // Whether to manage loading state with generatingReports
}

/**
 * Common service for handling report generation across different components
 */
export class ReportService {
  static async handleGenerateReport(
    alertOrId: Alert | string,
    dependencies: ReportServiceDependencies,
    options: ReportGenerationOptions = {}
  ): Promise<void> {
    const {
      generateReport,
      isConnected = true,
      generatingReports,
      setGeneratingReports,
      onSuccess,
      onError
    } = dependencies;

    const {
      showUserAlerts = false,
      logToConsole = true,
      manageLoadingState = false
    } = options;

    // Extract alert ID
    const alertId = typeof alertOrId === 'string' ? alertOrId : alertOrId.id;
    const alert = typeof alertOrId === 'object' ? alertOrId : null;

    // Check connection
    if (!isConnected) {
      if (logToConsole) {
        console.log('Not connected, cannot generate report');
      }
      return;
    }

    // Check if already generating (if managing loading state)
    if (manageLoadingState && generatingReports?.has(alertId)) {
      if (logToConsole) {
        console.log(`Report generation already in progress for alert ${alertId}`);
      }
      return;
    }

    // Start loading state
    if (manageLoadingState && setGeneratingReports) {
      setGeneratingReports(prev => new Set(prev).add(alertId));
    }

    try {
      const result = await generateReport(alertId);
      
      if (result.success) {
        if (logToConsole) {
          console.log('Report generation started:', result.investigationId);
        }
        
        // Call success callback if provided
        if (onSuccess) {
          onSuccess(result);
        }
      } else {
        const errorMsg = `Failed to generate report: ${result.message}`;
        
        if (logToConsole) {
          console.error(errorMsg);
        }
        
        if (showUserAlerts) {
          window.alert(errorMsg);
        }
        
        if (onError) {
          onError(new Error(result.message), errorMsg);
        }
      }
    } catch (err) {
      const errorMsg = 'Failed to generate report';
      
      if (logToConsole) {
        console.error('Error generating report:', err);
      }
      
      if (showUserAlerts) {
        window.alert(errorMsg);
      }
      
      if (onError) {
        onError(err, errorMsg);
      }
    } finally {
      // Clear loading state
      if (manageLoadingState && setGeneratingReports) {
        setGeneratingReports(prev => {
          const newSet = new Set(prev);
          newSet.delete(alertId);
          return newSet;
        });
      }
    }
  }

  /**
   * Convenience method for MapView-style usage (with user alerts)
   */
  static async handleGenerateReportForMap(
    alert: Alert,
    dependencies: Pick<ReportServiceDependencies, 'generateReport' | 'isConnected'>
  ): Promise<void> {
    return this.handleGenerateReport(
      alert,
      dependencies,
      {
        showUserAlerts: true,
        logToConsole: true,
        manageLoadingState: false
      }
    );
  }

  /**
   * Convenience method for Dashboard-style usage (with loading state management)
   */
  static async handleGenerateReportForDashboard(
    alertId: string,
    dependencies: Required<Pick<ReportServiceDependencies, 'generateReport' | 'generatingReports' | 'setGeneratingReports'>> & 
                  Pick<ReportServiceDependencies, 'isConnected'>
  ): Promise<void> {
    return this.handleGenerateReport(
      alertId,
      dependencies,
      {
        showUserAlerts: false,
        logToConsole: true,
        manageLoadingState: true
      }
    );
  }
} 