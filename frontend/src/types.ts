// Sample NYC alert data structure
export interface Alert {
    id: string;
    title: string;
    description: string;
    latitude: number;
    longitude: number;
    priority: 'low' | 'medium' | 'high' | 'critical';
    source: 'reddit' | '311' | 'twitter';
    timestamp: string;
    status: 'new' | 'investigating' | 'resolved';
    neighborhood?: string;
    borough?: string;
  }