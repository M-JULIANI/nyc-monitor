import { useState, useMemo, createContext, useContext, memo } from "react";
import TabNavigation from "../components/TabNavigation";
import MapView from "../components/MapView";
import Dashboard from "../components/Dashboard";
import Insights from "../components/Insights";
import { AlertsProvider, useAlerts } from "../contexts/AlertsContext";
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

// Memoized Insights component to prevent re-calculation
const MemoizedInsights = memo(Insights);

// Internal component to access alerts for AlertStatsProvider
const HomeContent = () => {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [insightsHasBeenRendered, setInsightsHasBeenRendered] = useState(false);
  const { isLoading, isStreaming, isConnecting, isComputingCharts, alerts } = useAlerts();

  // Determine if insights should be enabled
  const insightsEnabled = !isLoading && !isStreaming && !isConnecting && !isComputingCharts && alerts.length > 0;

  // Handle tab change with validation
  const handleTabChange = (newTab: string) => {
    // Prevent ALL navigation during chart computation
    if (isComputingCharts) {
      return;
    }
    
    // Prevent switching to insights if not ready
    if (newTab === "insights" && !insightsEnabled) {
      return;
    }
    
    setActiveTab(newTab);
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case "map":
        return <MapView />;
      case "dashboard":
        return <Dashboard />;
      case "insights":
        // Only render if enabled
        if (!insightsEnabled) {
          return <Dashboard />; // Fallback to dashboard
        }
        // Mark that insights has been rendered (for memoization)
        if (!insightsHasBeenRendered) {
          setInsightsHasBeenRendered(true);
        }
        return <MemoizedInsights />;
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
          <TabNavigation 
            activeTab={activeTab} 
            onTabChange={handleTabChange}
            isComputingCharts={isComputingCharts}
            {...(!insightsEnabled && { insightsDisabled: true })}
          />
        </div>
        <div
          style={{
            flex: 1,
            overflow: "hidden",
            position: "relative",
          }}
        >
          {renderActiveTab()}
          {/* Spinner overlay during chart computation */}
          {isComputingCharts && (
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(0, 0, 0, 0.7)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 50,
                backdropFilter: "blur(2px)",
              }}
            >
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-zinc-600 border-t-blue-500 mb-4"></div>
              <p className="text-white text-lg font-medium mb-2">Computing Charts...</p>
              <p className="text-zinc-400 text-sm">Please wait while we process the data</p>
            </div>
          )}
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
