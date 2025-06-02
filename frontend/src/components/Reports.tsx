import React from 'react';

const Reports: React.FC = () => {
  // Sample report data
  const sampleReports = [
    {
      id: '1',
      title: 'Brooklyn Water Infrastructure Analysis',
      description: 'Comprehensive analysis of water main breaks in Brooklyn over the past month, identifying patterns and recommending preventive measures.',
      type: 'Infrastructure Report',
      status: 'completed',
      createdAt: '2024-01-15T09:30:00Z',
      author: 'AI Agent - Infrastructure',
      driveLink: 'https://docs.google.com/presentation/d/1ABC...',
      priority: 'high',
      borough: 'Brooklyn'
    },
    {
      id: '2',
      title: 'Manhattan Traffic Pattern Insights',
      description: 'Analysis of traffic incidents and patterns in Manhattan during peak hours, with recommendations for traffic flow optimization.',
      type: 'Traffic Analysis',
      status: 'in_progress',
      createdAt: '2024-01-15T08:15:00Z',
      author: 'AI Agent - Traffic',
      priority: 'medium',
      borough: 'Manhattan'
    },
    {
      id: '3',
      title: 'Emergency Response Time Optimization',
      description: 'Citywide analysis of emergency response times and recommendations for resource allocation to improve response efficiency.',
      type: 'Emergency Services',
      status: 'completed',
      createdAt: '2024-01-14T16:45:00Z',
      author: 'AI Agent - Emergency',
      driveLink: 'https://docs.google.com/presentation/d/2DEF...',
      priority: 'critical',
      borough: 'All Boroughs'
    }
  ];

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'in_progress': return '#f59e0b';
      case 'draft': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical': return '#dc2626';
      case 'high': return '#ea580c';
      case 'medium': return '#d97706';
      case 'low': return '#65a30d';
      default: return '#6b7280';
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      padding: '2rem',
      color: '#fff',
      background: '#111827',
      overflowY: 'auto'
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem'
        }}>
          <h2 style={{ 
            fontSize: '2rem', 
            fontWeight: '700',
            color: '#f9fafb',
            margin: 0
          }}>
            Reports & Insights
          </h2>
          <button style={{
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            padding: '0.75rem 1.5rem',
            borderRadius: '0.5rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '600'
          }}>
            + Generate New Report
          </button>
        </div>

        {/* Stats Overview */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <div style={{
            background: '#1f2937',
            padding: '1rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151',
            textAlign: 'center'
          }}>
            <p style={{ fontSize: '1.5rem', fontWeight: '700', color: '#10b981', margin: 0 }}>
              {sampleReports.filter(r => r.status === 'completed').length}
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: '0.25rem 0 0 0' }}>
              Completed Reports
            </p>
          </div>
          <div style={{
            background: '#1f2937',
            padding: '1rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151',
            textAlign: 'center'
          }}>
            <p style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f59e0b', margin: 0 }}>
              {sampleReports.filter(r => r.status === 'in_progress').length}
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: '0.25rem 0 0 0' }}>
              In Progress
            </p>
          </div>
          <div style={{
            background: '#1f2937',
            padding: '1rem',
            borderRadius: '0.5rem',
            border: '1px solid #374151',
            textAlign: 'center'
          }}>
            <p style={{ fontSize: '1.5rem', fontWeight: '700', color: '#3b82f6', margin: 0 }}>
              {sampleReports.length}
            </p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: '0.25rem 0 0 0' }}>
              Total Reports
            </p>
          </div>
        </div>

        {/* Reports Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
          gap: '1.5rem'
        }}>
          {sampleReports.map((report) => (
            <div
              key={report.id}
              style={{
                background: '#1f2937',
                padding: '1.5rem',
                borderRadius: '0.5rem',
                border: '1px solid #374151',
                transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 25px -5px rgba(0, 0, 0, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '1rem'
              }}>
                <div>
                  <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: '#f9fafb',
                    margin: '0 0 0.5rem 0'
                  }}>
                    {report.title}
                  </h3>
                  <p style={{
                    fontSize: '0.75rem',
                    color: '#9ca3af',
                    margin: 0
                  }}>
                    {report.type} • {report.borough}
                  </p>
                </div>
                <div style={{
                  display: 'flex',
                  gap: '0.5rem'
                }}>
                  <span style={{
                    background: getPriorityColor(report.priority),
                    color: '#fff',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    textTransform: 'uppercase'
                  }}>
                    {report.priority}
                  </span>
                  <span style={{
                    background: getStatusColor(report.status),
                    color: '#fff',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    textTransform: 'capitalize'
                  }}>
                    {report.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <p style={{
                color: '#d1d5db',
                fontSize: '0.875rem',
                lineHeight: '1.5',
                marginBottom: '1rem'
              }}>
                {report.description}
              </p>

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                paddingTop: '1rem',
                borderTop: '1px solid #374151'
              }}>
                <div>
                  <p style={{
                    fontSize: '0.75rem',
                    color: '#9ca3af',
                    margin: 0
                  }}>
                    {report.author}
                  </p>
                  <p style={{
                    fontSize: '0.75rem',
                    color: '#6b7280',
                    margin: '0.25rem 0 0 0'
                  }}>
                    {new Date(report.createdAt).toLocaleDateString()}
                  </p>
                </div>
                <div style={{
                  display: 'flex',
                  gap: '0.5rem'
                }}>
                  {report.driveLink && (
                    <button
                      style={{
                        background: '#059669',
                        color: '#fff',
                        border: 'none',
                        padding: '0.5rem 1rem',
                        borderRadius: '0.25rem',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: '600'
                      }}
                      onClick={() => window.open(report.driveLink, '_blank')}
                    >
                      📄 View Slides
                    </button>
                  )}
                  <button
                    style={{
                      background: '#3b82f6',
                      color: '#fff',
                      border: 'none',
                      padding: '0.5rem 1rem',
                      borderRadius: '0.25rem',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: '600'
                    }}
                    onClick={() => alert('View details functionality coming soon!')}
                  >
                    View Details
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Coming Soon Section */}
        <div style={{
          background: '#1f2937',
          padding: '2rem',
          borderRadius: '0.5rem',
          border: '1px solid #374151',
          textAlign: 'center',
          marginTop: '2rem'
        }}>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: '#f9fafb' }}>
            Enhanced Reporting Features Coming Soon
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1rem',
            marginTop: '1rem'
          }}>
            <div>
              <p style={{ fontSize: '1rem', fontWeight: '600', color: '#3b82f6', marginBottom: '0.5rem' }}>
                🤖 Automated Report Generation
              </p>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
                AI agents automatically generate reports based on alert patterns
              </p>
            </div>
            <div>
              <p style={{ fontSize: '1rem', fontWeight: '600', color: '#10b981', marginBottom: '0.5rem' }}>
                📊 Interactive Analytics
              </p>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
                Drill down into data with interactive charts and visualizations
              </p>
            </div>
            <div>
              <p style={{ fontSize: '1rem', fontWeight: '600', color: '#f59e0b', marginBottom: '0.5rem' }}>
                📋 Custom Templates
              </p>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
                Create custom report templates for different stakeholders
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reports; 