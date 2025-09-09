
interface TabNavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  insightsDisabled?: boolean;
  isComputingCharts?: boolean;
}

const TabNavigation = ({ activeTab, onTabChange, insightsDisabled = false, isComputingCharts = false }: TabNavigationProps) => {
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: "" },
    { id: "map", label: "Map", icon: "" },
    { id: "insights", label: "Insights", icon: "" },
  ];

  return (
    <div className="flex border-b border-zinc-800 bg-zinc-900 px-2 pt-2">
      {tabs.map((tab) => {
        const isInsightsDisabled = tab.id === "insights" && insightsDisabled;
        const isInactiveTabFrozen = isComputingCharts && tab.id !== activeTab;
        const isDisabled = isInsightsDisabled || isInactiveTabFrozen;
        
        return (
          <button
            key={tab.id}
            onClick={() => !isDisabled && onTabChange(tab.id)}
            disabled={isDisabled}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors duration-200
              ${isDisabled 
                ? "text-zinc-600 cursor-not-allowed opacity-50" 
                : activeTab === tab.id 
                  ? "text-zinc-100 border-b-2 border-primary" 
                  : "text-zinc-400 hover:text-zinc-100"
              }
              bg-zinc-900 rounded-t-md
            `}
            type="button"
            title={
              isInsightsDisabled 
                ? "Loading data..." 
                : isInactiveTabFrozen 
                  ? "Computing charts..." 
                  : undefined
            }
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {isInsightsDisabled && (
              <span className="ml-1 text-xs">
                <div className="animate-spin rounded-full h-3 w-3 border border-zinc-600 border-t-transparent"></div>
              </span>
            )}
            {isInactiveTabFrozen && !isInsightsDisabled && (
              <span className="ml-1 text-xs">
                <div className="animate-spin rounded-full h-3 w-3 border border-zinc-600 border-t-transparent"></div>
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default TabNavigation;
export type { TabNavigationProps };
