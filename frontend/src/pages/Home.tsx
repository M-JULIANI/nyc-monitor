import { useState } from 'react';
import TabNavigation from '../components/TabNavigation';
import MapView from '../components/MapView';
import Dashboard from '../components/Dashboard';
import Insights from '../components/Insights';
import { AlertsProvider } from '../contexts/AlertsContext';
import { AlertStatsProvider } from '../contexts/AlertStatsContext';
import { MapStateProvider } from '../contexts/MapStateContext';

// Internal component to access alerts for AlertStatsProvider
const HomeContent = () => {
  const [activeTab, setActiveTab] = useState('map');

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'map':
        return <MapView />;
      case 'dashboard':
        return <Dashboard />;
      case 'insights':
        return <Insights />;
      default:
        return <MapView />;
    }
  };

  return (
    <AlertStatsProvider>
      <div style={{
        width: '100vw',
        height: 'calc(100vh - 60px)', // Account for navbar height
        display: 'flex',
        flexDirection: 'column',
        background: '#111827'
      }}>
        <div style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          backgroundColor: '#111827'
        }}>
          <TabNavigation 
            activeTab={activeTab} 
            onTabChange={setActiveTab} 
          />
        </div>
        <div style={{
          flex: 1,
          overflow: 'hidden',
          position: 'relative'
        }}>
          {renderActiveTab()}
        </div>
      </div>
    </AlertStatsProvider>
  );
};

const Home = () => {
  return (
    <AlertsProvider>
      <MapStateProvider>
        <HomeContent />
      </MapStateProvider>
    </AlertsProvider>
  );
};

export default Home; 