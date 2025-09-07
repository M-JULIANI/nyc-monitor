import { createContext, useContext, useState, ReactNode } from 'react';

export interface ViewportState {
    longitude: number;
    latitude: number;
    zoom: number;
} 

export interface FilterState {
  priority: string;
  source: string;
  status: string;
  timeRangeHours: number; // Hours back from now (1-4380 for up to 6 months)
}

export type ViewMode = 'priority' | 'source' | 'category';
export type DisplayMode = 'dots' | 'heatmap';

interface MapStateContextType {
  viewport: ViewportState;
  setViewport: (viewport: ViewportState) => void;
  filter: FilterState;
  setFilter: (filter: FilterState | ((prev: FilterState) => FilterState)) => void;
  viewMode: ViewMode;
  setViewMode: (viewMode: ViewMode) => void;
  displayMode: DisplayMode;
  setDisplayMode: (displayMode: DisplayMode) => void;
}

const MapStateContext = createContext<MapStateContextType | undefined>(undefined);

interface MapStateProviderProps {
  children: ReactNode;
}

export const MapStateProvider: React.FC<MapStateProviderProps> = ({ children }) => {
  // NYC bounding box for initial viewport
  const [viewport, setViewport] = useState<ViewportState>({
    longitude: -74.0,
    latitude: 40.7,
    zoom: 10
  });

  // Filter state
  const [filter, setFilter] = useState<FilterState>({
    priority: 'all',
    source: 'all',
    status: 'all',
    timeRangeHours: 168 // Default to last 7 days (reasonable starting point)
  });

  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('category');
  
  // Display mode state (dots vs heatmap)
  const [displayMode, setDisplayMode] = useState<DisplayMode>('heatmap');

  return (
    <MapStateContext.Provider value={{ 
      viewport, 
      setViewport, 
      filter, 
      setFilter, 
      viewMode, 
      setViewMode,
      displayMode,
      setDisplayMode
    }}>
      {children}
    </MapStateContext.Provider>
  );
};

export const useMapState = () => {
  const context = useContext(MapStateContext);
  if (context === undefined) {
    throw new Error('useMapState must be used within a MapStateProvider');
  }
  return context;
}; 