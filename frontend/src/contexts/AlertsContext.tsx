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
  refetch: () => void;
  fetchAlertsWithReports: () => void;
  refetchAlert: (alertId: string) => Promise<{ success: boolean; message: string; alert?: Alert }>;
  generateReport: (alertId: string) => Promise<{ success: boolean; message: string; investigationId?: string }>;
  fetchAgentTrace: (traceId: string) => Promise<{ success: boolean; trace?: string; message: string }>;
}

const AlertsContext = createContext<AlertsContextType | undefined>(undefined);

interface AlertsProviderProps {
  children: ReactNode;
}

export const AlertsProvider: React.FC<AlertsProviderProps> = ({ children }) => {
  const alertsData = useAlertsHook();
  
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