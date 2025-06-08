import React from 'react';
import InvestigationTester from '../components/InvestigationTester';

const Testing: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">System Testing</h1>
        <p className="text-gray-600">
          Test the multi-agent investigation system with real authentication and full e2e flow.
        </p>
      </div>
      
      <InvestigationTester />
      
      <div className="mt-8 p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h2 className="text-lg font-semibold text-yellow-800 mb-2">⚠️ Deployment Required</h2>
        <p className="text-yellow-700 text-sm">
          For full multi-agent functionality, the backend needs to be deployed to connect with Vertex AI ADK. 
          Local testing will use fallback mechanisms but won't show real agent interactions.
        </p>
      </div>
    </div>
  );
};

export default Testing; 