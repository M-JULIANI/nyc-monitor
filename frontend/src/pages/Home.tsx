import { useState } from 'react';
import TabNavigation from '../components/TabNavigation';
import MapView from '../components/MapView';
import Dashboard from '../components/Dashboard';
import Reports from '../components/Reports';
import { AlertsProvider } from '../contexts/AlertsContext';

const Home = () => {
  const [activeTab, setActiveTab] = useState('map');

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'map':
        return <MapView />;
      case 'dashboard':
        return <Dashboard />;
      case 'reports':
        return <Reports />;
      default:
        return <MapView />;
    }
  };

  return (
    <AlertsProvider>
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
    </AlertsProvider>
  );
};

export default Home; 