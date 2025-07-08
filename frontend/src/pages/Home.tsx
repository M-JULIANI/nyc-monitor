import { useState, useMemo, createContext, useContext } from "react";
import TabNavigation from "../components/TabNavigation";
import MapView from "../components/MapView";
import Dashboard from "../components/Dashboard";
import Insights from "../components/Insights";
import { AlertsProvider } from "../contexts/AlertsContext";
import { AlertStatsProvider } from "../contexts/AlertStatsContext";
import { MapStateProvider } from "../contexts/MapStateContext";

// Mobile Detection Context
interface MobileContextType {
  isMobile: boolean;
}

const MobileContext = createContext<MobileContextType | undefined>(undefined);

export const useMobile = () => {
  const context = useContext(MobileContext);
  if (context === undefined) {
    throw new Error("useMobile must be used within a MobileProvider");
  }
  return context;
};

interface MobileProviderProps {
  children: React.ReactNode;
  isMobile: boolean;
}

const MobileProvider: React.FC<MobileProviderProps> = ({ children, isMobile }) => {
  return <MobileContext.Provider value={{ isMobile }}>{children}</MobileContext.Provider>;
};

// Internal component to access alerts for AlertStatsProvider
const HomeContent = () => {
  const [activeTab, setActiveTab] = useState("dashboard");

  const renderActiveTab = () => {
    switch (activeTab) {
      case "map":
        return <MapView />;
      case "dashboard":
        return <Dashboard />;
      case "insights":
        return <Insights />;
      default:
        return <MapView />;
    }
  };

  return (
    <AlertStatsProvider>
      <div
        style={{
          width: "100vw",
          height: "calc(100vh - 60px)", // Account for navbar height
          display: "flex",
          flexDirection: "column",
          background: "#111827",
        }}
      >
        <div
          style={{
            position: "sticky",
            top: 0,
            zIndex: 40,
            backgroundColor: "#111827",
          }}
        >
          <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
        <div
          style={{
            flex: 1,
            overflow: "hidden",
            position: "relative",
          }}
        >
          {renderActiveTab()}
        </div>
      </div>
    </AlertStatsProvider>
  );
};

const Home = () => {
  // Detect mobile at the top level for better reliability
  const isMobile = useMemo(() => {
    return (
      window.innerWidth <= 768 ||
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    );
  }, []);

  return (
    <MobileProvider isMobile={isMobile}>
      <AlertsProvider>
        <MapStateProvider>
          <HomeContent />
        </MapStateProvider>
      </AlertsProvider>
    </MobileProvider>
  );
};

export default Home;
