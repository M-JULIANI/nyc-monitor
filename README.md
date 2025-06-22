parch# Atlas - Multi-Agent Investigation System

Refer to [setup](./docs/setup.md) for getting started

## 🚀 Deployed Services
- **Frontend**: https://nyc-monitor.app
- **Backend**: https://atlas-backend-blz2r3yjgq-uc.a.run.app

## 🧪 Testing the Investigation System

### **UI-Based Testing (Recommended)**
1. **Navigate to Testing Page**: Go to `/testing` in the deployed frontend
2. **Authentication**: Login with Google OAuth (no bypassing needed)
3. **Run Investigation**: Click "Start Investigation" button with pre-configured test payload
4. **View Results**: Access distributed tracing data and agent message flows

### **Why Deployment is Required**
- **Vertex AI ADK**: Multi-agent system requires cloud execution
- **Real Agent Interactions**: Local testing shows only fallback behavior
- **Distributed Tracing**: Full trace functionality needs cloud resources

### **Test Payload**
The UI testing uses this infrastructure alert:
```json
{
  "alert_id": "test_alert_ui_[timestamp]",
  "severity": 8,
  "event_type": "infrastructure_failure", 
  "location": "Manhattan Bridge",
  "summary": "Critical infrastructure issue detected via UI testing",
  "timestamp": "[current_time]",
  "sources": ["ui_test", "manual_testing"]
}
```