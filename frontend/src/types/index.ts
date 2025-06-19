export interface Alert {
  id: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  source: 'reddit' | '311' | 'twitter' | 'unknown';
  timestamp: string;
  status: 'new' | 'investigating' | 'resolved' | 'active';
  neighborhood: string;
  borough: string;
  
  // Additional date/time fields
  event_date: string;
  created_at: string;
  updated_at: string;
  
  // Location data
  coordinates: {
    lat: number;
    lng: number;
  };
  area?: string;
  venue_address?: string;
  specific_streets?: string[];
  cross_streets?: string[];
  
  // Impact data
  crowd_impact?: string;
  transportation_impact?: string;
  estimated_attendance?: string;
  severity?: number;
  
  // Additional metadata
  keywords?: string[];
  signals?: string[];
  url?: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'judge' | 'viewer';
  picture?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface ApiConfig {
  baseUrl: string;
  headers?: Record<string, string>;
}

export interface ApiResponse<T> {
  data: T;
  error?: string;
  status: number;
}

export interface LoginResponse {
  user: User;
  token: string;
}

export interface AlertFilters {
  priority?: Alert['priority'];
  source?: Alert['source'];
  status?: Alert['status'];
  timeRange?: '1h' | '24h' | '7d' | '30d';
  borough?: string;
}

export interface AlertStats {
  total: number;
  byPriority: Record<Alert['priority'], number>;
  byStatus: Record<Alert['status'], number>;
  bySource: Record<Alert['source'], number>;
  byBorough: Record<string, number>;
}

export interface Report {
  id: string;
  title: string;
  description: string;
  type: string;
  borough: string;
  status: 'completed' | 'in_progress' | 'draft';
  priority: Alert['priority'];
  author: string;
  createdAt: string;
  driveLink?: string;
}