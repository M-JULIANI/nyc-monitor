import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, Play, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface InvestigationResult {
  investigation_id: string;
  status: string;
  findings: string;
  artifacts: string[];
  confidence_score: number;
}

const InvestigationTester: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [investigationId, setInvestigationId] = useState<string | null>(null);

  const testPayload = {
    alert_id: `test_alert_ui_${Date.now()}`,
    severity: 8,
    event_type: "infrastructure_failure",
    location: "Manhattan Bridge",
    summary: "Critical infrastructure issue detected via UI testing",
    timestamp: new Date().toISOString(),
    sources: ["ui_test", "manual_testing"]
  };

  const startInvestigation = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // Get auth token (assuming it's stored in localStorage or context)
      const token = localStorage.getItem('authToken');
      
      const response = await fetch('/api/investigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(testPayload),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
      setInvestigationId(data.investigation_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const viewTraceData = async () => {
    if (!investigationId) return;

    try {
      const token = localStorage.getItem('authToken');
      
      // Open trace timeline in new tab
      const traceUrl = `/api/investigate/${investigationId}/trace/timeline`;
      const response = await fetch(traceUrl, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const traceData = await response.json();
        console.log('Trace Data:', traceData);
        
        // You could open a modal or new page to display this
        alert(`Trace data logged to console. Timeline has ${traceData.total_events} events.`);
      }
    } catch (err) {
      console.error('Failed to fetch trace data:', err);
    }
  };

  const viewAgentFlow = async () => {
    if (!investigationId) return;

    try {
      const token = localStorage.getItem('authToken');
      
      const response = await fetch(`/api/investigate/${investigationId}/agent-flow`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const agentFlowData = await response.json();
        console.log('Agent Flow Data:', agentFlowData);
        
        // Open agent flow visualization
        alert(`Agent flow data logged to console. ${agentFlowData.agent_message_flow.summary.total_messages} messages between agents.`);
      }
    } catch (err) {
      console.error('Failed to fetch agent flow data:', err);
    }
  };

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          Investigation System Tester
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-medium mb-2">Test Payload:</h3>
          <pre className="text-sm bg-white p-3 rounded border overflow-x-auto">
            {JSON.stringify(testPayload, null, 2)}
          </pre>
        </div>

        <div className="flex gap-2">
          <Button 
            onClick={startInvestigation} 
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {isLoading ? 'Running Investigation...' : 'Start Investigation'}
          </Button>

          {investigationId && (
            <>
              <Button variant="outline" onClick={viewTraceData}>
                View Trace Data
              </Button>
              <Button variant="outline" onClick={viewAgentFlow}>
                View Agent Flow
              </Button>
            </>
          )}
        </div>

        {error && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && (
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Investigation completed!</strong> ID: {result.investigation_id}
            </AlertDescription>
          </Alert>
        )}

        {result && (
          <div className="space-y-4">
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-medium mb-2">Investigation Results:</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Status:</strong> {result.status}
                </div>
                <div>
                  <strong>Confidence:</strong> {(result.confidence_score * 100).toFixed(0)}%
                </div>
                <div className="col-span-2">
                  <strong>Artifacts:</strong> {result.artifacts.join(', ')}
                </div>
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-medium mb-2">Investigation Findings:</h3>
              <pre className="text-sm whitespace-pre-wrap">{result.findings}</pre>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default InvestigationTester; 