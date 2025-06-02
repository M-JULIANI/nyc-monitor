import React from 'react';

interface TabNavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TabNavigation: React.FC<TabNavigationProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'map', label: 'Map View', icon: '🗺️' },
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'reports', label: 'Reports', icon: '📋' }
  ];

  return (
    <div style={{
      display: 'flex',
      borderBottom: '2px solid #374151',
      background: '#1f2937',
      paddingLeft: '1rem',
      paddingTop: '0.5rem'
    }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.75rem 1.5rem',
            background: activeTab === tab.id ? '#374151' : 'transparent',
            color: activeTab === tab.id ? '#fff' : '#9ca3af',
            border: 'none',
            borderRadius: '0.5rem 0.5rem 0 0',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: activeTab === tab.id ? '600' : '400',
            transition: 'all 0.2s ease-in-out',
            marginRight: '0.25rem'
          }}
          onMouseEnter={(e) => {
            if (activeTab !== tab.id) {
              e.currentTarget.style.background = '#374151';
              e.currentTarget.style.color = '#d1d5db';
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== tab.id) {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#9ca3af';
            }
          }}
        >
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};

export default TabNavigation; 