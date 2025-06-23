import { useState } from 'react';
import TabNavigation from '../components/TabNavigation';
import MapView from '../components/MapView';
import Dashboard from '../components/Dashboard';
import Insights from '../components/Insights';
import Reports from '../components/Reports';
import { AlertsProvider } from '../contexts/AlertsContext';
import { AlertStatsProvider } from '../contexts/AlertStatsContext';
import { MapStateProvider } from '../contexts/MapStateContext';
import { useAlerts } from '../contexts/AlertsContext';

// Internal component to access alerts for AlertStatsProvider
const HomeContent = () => {
  const [activeTab, setActiveTab] = useState('map');
  const { alerts } = useAlerts();

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'map':
        return <MapView />;
      case 'dashboard':
        return <Dashboard />;
      case 'insights':
        return <Insights />;
      case 'reports':
        return <Reports />;
      default:
        return <MapView />;
    }
  };

  return (
    <AlertStatsProvider alerts={alerts}>
      <div style={{
        width: '100vw',
        height: 'calc(100vh - 60px)', // Account for navbar height
        display: 'flex',
        flexDirection: 'column',
        background: '#111827'
      }}>
        <TabNavigation 
          activeTab={activeTab} 
          onTabChange={setActiveTab} 
        />
        <div style={{
          flex: 1,
          overflow: 'hidden'
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