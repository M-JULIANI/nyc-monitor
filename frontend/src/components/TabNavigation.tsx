import React from 'react';

interface TabNavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TabNavigation: React.FC<TabNavigationProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'map', label: 'Map', icon: '🗺️' },
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'insights', label: 'Insights', icon: '📈' },
    { id: 'reports', label: 'Reports', icon: '📄' }
  ];

  return (
    <div className="flex border-b border-zinc-800 bg-zinc-900 px-2 pt-2">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors duration-200
            ${
              activeTab === tab.id
                ? 'text-zinc-100 border-b-2 border-primary'
                : 'text-zinc-400 hover:text-zinc-100'
            }
            bg-zinc-900 rounded-t-md
          `}
          type="button"
        >
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};

export default TabNavigation; 