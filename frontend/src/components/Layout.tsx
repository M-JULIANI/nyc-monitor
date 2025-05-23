import Navbar from './Navbar';
import React from 'react';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      background: '#222'
    }}>
      <Navbar />
      <div style={{
        flex: 1,
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: '60px', // height of navbar
        boxSizing: 'border-box'
      }}>
        {children}
      </div>
    </div>
  );
};

export default Layout; 