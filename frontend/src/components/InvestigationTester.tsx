import React, { useState } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Box,
  Grid,
  Paper
} from '@mui/material';
import {
  PlayArrow,
  CheckCircle,
  Error as ErrorIcon,
  Warning
} from '@mui/icons-material';

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
        const errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        throw new globalThis.Error(errorMessage);
      }

      const data = await response.json();
      setResult(data);
      setInvestigationId(data.investigation_id);
    } catch (err) {
      const errorMessage = err instanceof globalThis.Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
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
    <Card sx={{ width: '100%', maxWidth: 1000, margin: 'auto' }}>
      <CardHeader 
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <Warning color="primary" />
            <Typography variant="h5">Investigation System Tester</Typography>
          </Box>
        }
      />
      <CardContent>
        <Box display="flex" flexDirection="column" gap={3}>
          {/* Test Payload Display */}
          <Paper elevation={1} sx={{ p: 2, bgcolor: 'grey.50' }}>
            <Typography variant="h6" gutterBottom>Test Payload:</Typography>
            <Paper 
              elevation={0} 
              sx={{ 
                p: 2, 
                bgcolor: 'white', 
                border: 1, 
                borderColor: 'grey.300',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                overflowX: 'auto'
              }}
            >
              <pre>{JSON.stringify(testPayload, null, 2)}</pre>
            </Paper>
          </Paper>

          {/* Action Buttons */}
          <Box display="flex" gap={2}>
            <Button
              variant="contained"
              onClick={startInvestigation}
              disabled={isLoading}
              startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrow />}
            >
              {isLoading ? 'Running Investigation...' : 'Start Investigation'}
            </Button>

            {investigationId && (
              <>
                <Button variant="outlined" onClick={viewTraceData}>
                  View Trace Data
                </Button>
                <Button variant="outlined" onClick={viewAgentFlow}>
                  View Agent Flow
                </Button>
              </>
            )}
          </Box>

          {/* Error Alert */}
          {error && (
            <Alert severity="error" icon={<ErrorIcon />}>
              {error}
            </Alert>
          )}

          {/* Success Alert */}
          {result && (
            <Alert severity="success" icon={<CheckCircle />}>
              <strong>Investigation completed!</strong> ID: {result.investigation_id}
            </Alert>
          )}

          {/* Results Display */}
          {result && (
            <Box display="flex" flexDirection="column" gap={2}>
              <Paper elevation={1} sx={{ p: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
                <Typography variant="h6" gutterBottom>Investigation Results:</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      <strong>Status:</strong> {result.status}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      <strong>Confidence:</strong> {(result.confidence_score * 100).toFixed(0)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2">
                      <strong>Artifacts:</strong> {result.artifacts.join(', ')}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>

              <Paper elevation={1} sx={{ p: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
                <Typography variant="h6" gutterBottom>Investigation Findings:</Typography>
                <Typography 
                  variant="body2" 
                  component="pre" 
                  sx={{ 
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem'
                  }}
                >
                  {result.findings}
                </Typography>
              </Paper>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default InvestigationTester; 