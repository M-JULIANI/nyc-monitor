import React from 'react';
import ReportCard from './ReportCard';

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
    <div className="w-full h-full p-4 md:p-8 bg-background text-text-primary overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <h2 className="text-2xl md:text-3xl font-bold text-text-primary m-0">
            Reports & Insights
          </h2>
          <button className="btn btn-primary whitespace-nowrap">
            + Generate New Report
          </button>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="card text-center">
            <p className="text-2xl font-bold text-accent m-0">
              {sampleReports.filter(r => r.status === 'completed').length}
            </p>
            <p className="text-sm text-text-muted mt-1">
              Completed Reports
            </p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-high m-0">
              {sampleReports.filter(r => r.status === 'in_progress').length}
            </p>
            <p className="text-sm text-text-muted mt-1">
              In Progress
            </p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-primary m-0">
              {sampleReports.length}
            </p>
            <p className="text-sm text-text-muted mt-1">
              Total Reports
            </p>
          </div>
        </div>

        {/* Reports Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {sampleReports.map((report) => (
            <ReportCard
              key={report.id}
              title={report.title}
              description={report.description}
              type={report.type}
              borough={report.borough}
              status={report.status}
              priority={report.priority}
              author={report.author}
              createdAt={report.createdAt}
              driveLink={report.driveLink}
              onViewDetails={() => alert('View details functionality coming soon!')}
            />
          ))}
        </div>

        {/* Coming Soon Section */}
        <div className="card text-center mt-8">
          <h3 className="text-xl md:text-2xl font-semibold mb-4 text-text-primary">
            Enhanced Reporting Features Coming Soon
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
            <div>
              <p className="text-lg font-semibold text-primary mb-2">
                🤖 Automated Report Generation
              </p>
              <p className="text-sm text-text-muted">
                AI agents automatically generate reports based on alert patterns
              </p>
            </div>
            <div>
              <p className="text-lg font-semibold text-accent mb-2">
                📊 Interactive Analytics
              </p>
              <p className="text-sm text-text-muted">
                Drill down into data with interactive charts and visualizations
              </p>
            </div>
            <div>
              <p className="text-lg font-semibold text-high mb-2">
                📋 Custom Templates
              </p>
              <p className="text-sm text-text-muted">
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