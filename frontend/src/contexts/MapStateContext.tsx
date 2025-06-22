import { createContext, useContext, useState, ReactNode } from 'react';

interface ViewportState {
    longitude: number;
    latitude: number;
    zoom: number;
} 

interface FilterState {
  priority: string;
  source: string;
  status: string;
  timeRangeHours: number; // Hours back from now (1-168 for 7 days)
}

type ViewMode = 'priority' | 'source' | 'category';

interface MapStateContextType {
  viewport: ViewportState;
  setViewport: (viewport: ViewportState) => void;
  filter: FilterState;
  setFilter: (filter: FilterState | ((prev: FilterState) => FilterState)) => void;
  viewMode: ViewMode;
  setViewMode: (viewMode: ViewMode) => void;
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
    timeRangeHours: 72 // Default to last 72 hours to show 311 data
  });

  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('category');

  return (
    <MapStateContext.Provider value={{ 
      viewport, 
      setViewport, 
      filter, 
      setFilter, 
      viewMode, 
      setViewMode 
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