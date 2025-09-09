import React, { createContext, useContext, ReactNode } from 'react';
import { useAlerts as useAlertsHook } from '../hooks/useAlerts';
import { Alert } from '../types';

interface AlertsContextType {
  alerts: Alert[];
  alertsWithReports: Alert[];
  error: string | null;
  isLoading: boolean;
  isLoadingReports: boolean;
  stats: {
    total: number;
    byPriority: Record<string, number>;
    byStatus: Record<string, number>;
    bySource: Record<string, number>;
    critical: number;
    high: number;
    medium: number;
    low: number;
    active: number;
    resolved: number;
  };
  chartData: {
    categoryData: Array<{ name: string; value: number; color: string }>;
    timeData: Array<any>;
    priorityData: Array<{ name: string; value: number; color: string }>;
    dateInfo: Array<any>;
    debugInfo: any;
  };
  refetch: () => void;
  fetchAlertsWithReports: () => void;
  refetchAlert: (alertId: string) => Promise<{ success: boolean; message: string; alert?: Alert }>;
  getSingleAlert: (alertId: string) => Promise<{ success: boolean; message: string; alert?: Alert }>;
  generateReport: (alertId: string) => Promise<{ success: boolean; message: string; investigationId?: string }>;
  fetchAgentTrace: (traceId: string) => Promise<{ success: boolean; trace?: string; message: string }>;
  // Streaming properties
  isStreaming: boolean;
  isConnecting: boolean;
  isComputingCharts: boolean;
  streamingProgress: {
    currentChunk: number;
    totalChunks: number;
    totalAlerts: number;
    estimatedTotal: number;
    progressPercent: number;
    source: string;
    isComplete: boolean;
  };
  streamAlerts: () => void;
  cancelStreaming: () => void;
  // Dashboard optimization
  fetchReportsForDashboard: () => void;
}

const AlertsContext = createContext<AlertsContextType | undefined>(undefined);

interface AlertsProviderProps {
  children: ReactNode;
  useStreaming?: boolean;
  chunkSize?: number;
  hours?: number;
}

export const AlertsProvider: React.FC<AlertsProviderProps> = ({ 
  children, 
  useStreaming = true, // Disable streaming by default to prevent connection issues
  chunkSize = 1000,
  hours = 4320 // 6 months
}) => {
  const alertsData = useAlertsHook({ 
    useStreaming, 
    chunkSize, 
    hours 
  });
  
  return (
    <AlertsContext.Provider value={alertsData}>
      {children}
    </AlertsContext.Provider>
  );
};

export const useAlerts = (): AlertsContextType => {
  const context = useContext(AlertsContext);
  if (context === undefined) {
    throw new Error('useAlerts must be used within an AlertsProvider');
  }
  return context;
}; 