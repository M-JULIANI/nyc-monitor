import { createContext, useContext, useState, ReactNode } from 'react';

interface ViewportState {
    longitude: number;
    latitude: number;
    zoom: number;
  } 

interface MapStateContextType {
  viewport: ViewportState;
  setViewport: (viewport: ViewportState) => void;
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

  return (
    <MapStateContext.Provider value={{ viewport, setViewport }}>
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