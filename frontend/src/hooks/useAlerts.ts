// frontend/src/hooks/useAlerts.ts
import { useState, useEffect } from 'react';
import { Alert } from '../types';

export const useAlerts = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource('/api/alerts/stream');
    
    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setAlerts(prevAlerts => {
        // Merge new alerts with existing ones
        const newAlerts = data.alerts;
        const existingIds = new Set(prevAlerts.map(a => a.id));
        const uniqueNewAlerts = newAlerts.filter(a => !existingIds.has(a.id));
        return [...uniqueNewAlerts, ...prevAlerts].slice(0, 100); // Keep last 100
      });
    };
    
    eventSource.onerror = (error: Event) => {
      setError(error as unknown as Error);
      setIsConnected(false);
      // EventSource will automatically try to reconnect
    };
    
    return () => {
      eventSource.close();
    };
  }, []);

  return { alerts, error, isConnected };
};