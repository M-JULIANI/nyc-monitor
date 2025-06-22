// Priority and Severity Types
export type AlertPriority = 'critical' | 'high' | 'medium' | 'low';
export type AlertSource = 'reddit' | '311' | 'twitter' | 'unknown';
export type AlertStatus = 'new' | 'investigating' | 'resolved' | 'active';

// Severity scale (1-10) that maps to priorities
export interface SeverityConfig {
  critical: { min: 9; max: 10; color: '#dc2626'; };
  high: { min: 7; max: 8; color: '#ea580c'; };
  medium: { min: 5; max: 6; color: '#d97706'; };
  low: { min: 1; max: 4; color: '#65a30d'; };
}

export const SEVERITY_CONFIG: SeverityConfig = {
  critical: { min: 9, max: 10, color: '#dc2626' },
  high: { min: 7, max: 8, color: '#ea580c' },
  medium: { min: 5, max: 6, color: '#d97706' },
  low: { min: 1, max: 4, color: '#65a30d' }
};

// Helper function to map severity to priority
export const severityToPriority = (severity: number): AlertPriority => {
  if (severity >= 9) return 'critical';
  if (severity >= 7) return 'high';
  if (severity >= 5) return 'medium';
  return 'low';
};

// Helper function to get priority color
export const getPriorityColor = (priority: AlertPriority): string => {
  return SEVERITY_CONFIG[priority].color;
};

export interface Alert {
  id: string;
  title: string;
  description: string;
  priority: AlertPriority;
  source: AlertSource;
  timestamp: string;
  status: AlertStatus;
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
  
  // Categorization fields (simplified to just main category)
  category?: string;
  
  // Additional metadata
  keywords?: string[];
  signals?: string[];
  url?: string;
  
  // Investigation & Report fields
  reportUrl?: string;     // URL to generated Google Slides report
  traceId?: string;       // ID to fetch agent trace from Firestore
  investigationId?: string; // ID of the investigation that was run
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
  priority?: AlertPriority;
  source?: AlertSource;
  status?: AlertStatus;
  timeRange?: '1h' | '24h' | '7d' | '30d';
  borough?: string;
}

export interface AlertStats {
  total: number;
  byPriority: Record<AlertPriority, number>;
  byStatus: Record<AlertStatus, number>;
  bySource: Record<AlertSource, number>;
  byBorough: Record<string, number>;
}

export interface Report {
  id: string;
  title: string;
  description: string;
  type: string;
  borough: string;
  status: 'completed' | 'in_progress' | 'draft';
  priority: AlertPriority;
  author: string;
  createdAt: string;
  driveLink?: string;
}