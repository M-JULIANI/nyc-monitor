import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div style={{
      width: '100%',
      height: '100%',
      padding: '2rem',
      color: '#fff',
      background: '#111827'
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <h2 style={{ 
          fontSize: '2rem', 
          fontWeight: '700', 
          marginBottom: '2rem',
          color: '#f9fafb'
        }}>
          NYC Alert Dashboard
        </h2>
        
        {/* Stats Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          <div style={{
            background: '#1f2937',
            padding: '1.5rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151'
          }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#f9fafb' }}>
              Active Alerts
            </h3>
            <p style={{ fontSize: '2.5rem', fontWeight: '700', color: '#ef4444' }}>
              23
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
              +4 from last hour
            </p>
          </div>
          
          <div style={{
            background: '#1f2937',
            padding: '1.5rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151'
          }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#f9fafb' }}>
              Critical Priority
            </h3>
            <p style={{ fontSize: '2.5rem', fontWeight: '700', color: '#dc2626' }}>
              3
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
              Requires immediate attention
            </p>
          </div>
          
          <div style={{
            background: '#1f2937',
            padding: '1.5rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151'
          }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#f9fafb' }}>
              Reports Generated
            </h3>
            <p style={{ fontSize: '2.5rem', fontWeight: '700', color: '#10b981' }}>
              7
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
              Today
            </p>
          </div>
          
          <div style={{
            background: '#1f2937',
            padding: '1.5rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151'
          }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#f9fafb' }}>
              Data Sources
            </h3>
            <p style={{ fontSize: '2.5rem', fontWeight: '700', color: '#3b82f6' }}>
              3
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
              Reddit, 311, Twitter
            </p>
          </div>
        </div>

        {/* Content area for future dashboard widgets */}
        <div style={{
          background: '#1f2937',
          padding: '2rem',
          borderRadius: '0.5rem',
          border: '1px solid #374151',
          textAlign: 'center'
        }}>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: '#f9fafb' }}>
            Dashboard Coming Soon
          </h3>
          <p style={{ color: '#9ca3af', marginBottom: '1rem' }}>
            This dashboard will include:
          </p>
          <ul style={{ 
            listStyle: 'none', 
            padding: 0, 
            color: '#d1d5db',
            textAlign: 'left',
            maxWidth: '600px',
            margin: '0 auto'
          }}>
            <li style={{ padding: '0.5rem 0' }}>📊 Real-time alert analytics</li>
            <li style={{ padding: '0.5rem 0' }}>📈 Trend analysis and patterns</li>
            <li style={{ padding: '0.5rem 0' }}>🗺️ Geographic distribution insights</li>
            <li style={{ padding: '0.5rem 0' }}>⏱️ Response time metrics</li>
            <li style={{ padding: '0.5rem 0' }}>🔍 Predictive hotspot analysis</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 