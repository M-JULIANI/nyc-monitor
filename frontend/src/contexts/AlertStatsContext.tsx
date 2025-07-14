import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AlertStats {
  monitor_alerts: number;
  nyc_311_signals: number;
  total: number;
}

interface AlertStatsResponse {
  stats: AlertStats;
  timeframe: string;
  generated_at: string;
}

interface Category {
  name: string;
  types: Array<{
    key: string;
    name: string;
    description: string;
    default_severity: number;
  }>;
}

interface AlertCategoriesResponse {
  categories: Record<string, Category>;
  main_categories: string[];
  total_categories: number;
  total_alert_types: number;
  timestamp: string;
  version: string;
}

interface AlertStatsContextType {
  alertStats: AlertStatsResponse | null;
  alertCategories: AlertCategoriesResponse | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
  timeRange: number;
}

const AlertStatsContext = createContext<AlertStatsContextType | undefined>(undefined);

interface AlertStatsProviderProps {
  children: ReactNode;
}

export const AlertStatsProvider: React.FC<AlertStatsProviderProps> = ({ children }) => {
  const [alertStats, setAlertStats] = useState<AlertStatsResponse | null>(null);
  const [alertCategories, setAlertCategories] = useState<AlertCategoriesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timeRange = 168; // Fixed to 7 days to match data availability

  const fetchStats = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = localStorage.getItem('idToken');
      if (!token) {
        throw new Error('Authentication required');
      }

      const [statsResponse, categoriesResponse] = await Promise.all([
        fetch(`/api/alerts/stats?hours=${timeRange}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }),
        fetch('/api/alerts/categories', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })
      ]);

      if (!statsResponse.ok) {
        throw new Error(`Stats API error: ${statsResponse.status}`);
      }

      if (!categoriesResponse.ok) {
        throw new Error(`Categories API error: ${categoriesResponse.status}`);
      }

      const [statsData, categoriesData] = await Promise.all([
        statsResponse.json(),
        categoriesResponse.json()
      ]);

      setAlertStats(statsData);
      setAlertCategories(categoriesData);

    } catch (err) {
      console.error('Error fetching alert stats:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch alert stats');
    } finally {
      setIsLoading(false);
    }
  };

  const refetch = () => {
    fetchStats();
  };

  // Fetch data on mount
  useEffect(() => {
    fetchStats();
  }, []);

  const value: AlertStatsContextType = {
    alertStats,
    alertCategories,
    isLoading,
    error,
    refetch,
    timeRange
  };

  return (
    <AlertStatsContext.Provider value={value}>
      {children}
    </AlertStatsContext.Provider>
  );
};

export const useAlertStats = (): AlertStatsContextType => {
  const context = useContext(AlertStatsContext);
  if (context === undefined) {
    throw new Error('useAlertStats must be used within an AlertStatsProvider');
  }
  return context;
}; 