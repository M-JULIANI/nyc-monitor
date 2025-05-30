# Monitor Agent Subsystem

## Overview

The Monitor Agent is the "always-on intelligence" layer of the Atlas system that continuously scans multiple NYC data sources to identify patterns, anomalies, emergencies, and major public events requiring investigation or city planning attention. It operates as a lightweight triage system that feeds high-priority signals to the full multi-agent analysis pipeline.

This system captures both emergency situations AND significant public events that impact NYC operations, including crowd gatherings, parades, festivals, concerts, and seasonal celebrations that require city planning, safety coordination, and resource allocation.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cron Job      │───▶│   Lightweight    │───▶│   Firestore     │
│   (15 min)      │    │   Vertex AI      │    │   Alert Queue   │
│                 │    │   Triage Agent   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  Raw API Data    │    │  Cloud Function │
                    │  (Reddit, 311,   │    │  (Firestore     │
                    │   Traffic, etc)  │    │   Trigger)      │
                    └──────────────────┘    └─────────────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  Full Multi-    │
                                            │  Agent System   │
                                            │  (On Demand)    │
                                            └─────────────────┘
```

## Core Capabilities

### 🔍 **Continuous Monitoring**
- **Frequency**: Every 15 minutes via Cloud Scheduler
- **Scope**: Multi-source data aggregation across NYC
- **Intelligence**: Pattern recognition for emergencies AND public events
- **Output**: Prioritized alert queue for human/AI investigation

### 📊 **Live Intelligence Dashboard**
Real-time view of city-wide patterns:
- 🔴 **Critical Alerts** (Severity 8-10): Emergencies requiring immediate response
- 🟡 **Major Events** (Severity 5-7): Public gatherings, parades, festivals requiring planning
- 🟢 **Background Trends** (Severity 1-4): Routine activities and minor events
- 📊 **Daily Insights**: Emergency areas, planned events, crowd patterns, resource needs

### 🎯 **Smart Triage Logic**
The system automatically escalates based on:
- **Severity scoring** (1-10 scale) for both emergencies and events
- **Event type classification** (emergency, parade, festival, concert, etc.)
- **Crowd impact assessment** (expected attendance and city resource needs)
- **Cross-source correlation** (multiple signals from same area/event)
- **Temporal patterns** (planned vs. spontaneous events)
- **Geographic clustering** (neighborhood-level event analysis)

## Data Sources

### 🗨️ **Social Media Intelligence (Reddit)**

**NYC Community Subreddits:**
- `r/nyc`, `r/newyorkcity`, `r/manhattan`, `r/brooklyn`, `r/queens`
- `r/bronx`, `r/statenisland`, `r/asknyc`
- `r/nycapartments`, `r/nycjobs`

**Emergency & Safety Subreddits:**
- `r/emergencyservices`, `r/police`, `r/firefighting`
- `r/ems`, `r/911calls`, `r/cityplanning`

**Infrastructure & Operations:**
- `r/infrastructure`, `r/transit`, `r/traffic`
- `r/publichealth`, `r/environment`

**Keywords & Patterns Monitored:**
```yaml
Emergency Keywords:
  - "911", "emergency", "ambulance", "fire", "police"
  - "explosion", "shooting", "accident", "collapse"
  - "evacuation", "lockdown", "emergency alert"

Infrastructure Issues:
  - "power outage", "blackout", "water main", "gas leak"
  - "subway delay", "train stuck", "signal problem"
  - "road closure", "construction", "bridge closed"

Health & Safety:
  - "food poisoning", "contamination", "outbreak"
  - "air quality", "pollution", "smog alert"
  - "heat wave", "cold warning", "weather emergency"

Major Public Events & Crowd Gatherings:
  - "parade", "festival", "pride", "concert", "marathon"
  - "protest", "rally", "demonstration", "march"
  - "celebration", "block party", "street fair"
  - "outdoor event", "large crowd", "street closure"
  - "event permit", "public gathering", "street festival"

Seasonal & Annual NYC Events:
  - "halloween parade", "thanksgiving parade", "new year"
  - "fourth of july", "summer streets", "outdoor cinema"
  - "bryant park event", "central park event", "times square event"
  - "brooklyn bridge park", "pier event"

Sports & Entertainment Events:
  - "yankees game", "mets game", "knicks game", "rangers game"
  - "madison square garden", "yankee stadium", "citi field"
  - "barclays center", "big concert", "broadway opening"
  - "fashion week"

City Operations:
  - "city hall", "mayor", "DOT", "DSNY", "FDNY", "NYPD"
  - "permit", "inspection", "violation", "citation"
  - "budget", "policy", "announcement"

Community Concerns:
  - "noise complaint", "quality of life", "safety concern"
  - "homeless", "housing", "rent", "eviction"
  - "neighborhood meeting", "community board"
```

### 📞 **311 Service Requests** (Planned)
- Service request patterns and spikes
- Geographic clustering of complaints
- Response time anomalies
- Seasonal trend analysis

### 🚨 **Emergency Services Data** (Planned)
- 911 call volume patterns
- Response time metrics
- Incident type clustering
- Multi-agency coordination events

### 🚦 **Traffic & Transportation**
- MTA service alerts and delays
- Traffic incident reports
- Construction notifications
- Pedestrian safety incidents

### 🌬️ **Environmental Monitoring**
- Air quality index changes
- Weather emergency alerts
- Environmental health warnings
- Climate-related incidents

## Technical Implementation

### 1. **Background Collection** (15-minute intervals)

```python
def background_monitor():
    """Lightweight data collection for triage analysis"""
    
    # Collect trending signals from each source
    signals = {
        'reddit': {
            'trending_posts': get_reddit_trending_nyc(),
            'emergency_keywords': scan_emergency_keywords(),
            'geographic_mentions': extract_neighborhood_mentions(),
            'sentiment_spikes': detect_sentiment_anomalies()
        },
        'traffic': {
            'incidents': get_traffic_incidents(),
            'delays': get_transit_delays(),
            'closures': get_road_closures()
        },
        'environment': {
            'air_quality': get_aqi_alerts(),
            'weather': get_weather_warnings()
        },
        'city_operations': {
            'permits': get_recent_permits(),
            'violations': get_violation_spikes()
        }
    }
    
    # Trigger lightweight AI triage
    analysis = triage_agent.analyze(signals)
    
    # Store alerts by severity
    store_alerts(analysis)
```

### 2. **AI Triage Agent** (Vertex AI)

```python
class TriageAgent:
    def analyze_signals(self, raw_signals):
        """
        Lightweight AI analysis for pattern detection
        
        Prompt Engineering:
        - "Analyze NYC data signals for anomalies and correlations"
        - "Assign severity scores (1-10) based on public impact"
        - "Identify geographic clusters and temporal patterns"
        - "Flag urgent situations requiring immediate investigation"
        """
        
        triage_prompt = f"""
        Analyze these NYC data signals collected in the last 15 minutes:
        
        {json.dumps(raw_signals, indent=2)}
        
        Your tasks:
        1. Identify any anomalies or concerning patterns
        2. Look for correlations between different data sources
        3. Assign severity scores (1-10) where:
           - 9-10: Emergency/Crisis requiring immediate attention
           - 7-8: Significant incident needing investigation
           - 5-6: Notable pattern worth monitoring
           - 1-4: Background noise/normal activity
        
        4. For each alert, specify:
           - Geographic area affected
           - Data sources involved
           - Potential impact/urgency
           - Recommended action
        
        Output as structured JSON.
        """
        
        response = vertex_ai.generate_content(
            prompt=triage_prompt,
            model="gemini-pro"
        )
        
        return parse_triage_response(response)
```

### 3. **Alert Storage & Escalation**

```javascript
// Firestore Alert Structure
{
  "alerts": {
    "brooklyn_traffic_20250530_1420": {
      "id": "brooklyn_traffic_20250530_1420",
      "severity": 8,
      "area": "Brooklyn Heights",
      "signals": ["reddit", "traffic", "transit"],
      "description": "Multiple Reddit posts about traffic jam correlating with MTA delays",
      "raw_data": {...},
      "status": "pending_investigation", // pending_investigation | investigating | resolved
      "created": "2025-05-30T14:20:00Z",
      "expires": "2025-05-31T14:20:00Z",
      "escalated": false,
      "investigation_results": null
    }
  }
}
```

### 4. **Escalation Logic**

```python
@firestore_trigger('alerts/{alertId}')
def handle_new_alert(alert_data):
    """Automatic escalation based on severity"""
    
    severity = alert_data['severity']
    
    if severity >= 9:
        # Critical: Immediate full investigation
        trigger_emergency_investigation(alert_data)
        notify_emergency_contacts(alert_data)
        
    elif severity >= 7:
        # High: Automated deep investigation
        queue_full_investigation(alert_data)
        
    elif severity >= 5:
        # Medium: Queue for user-triggered investigation
        add_to_investigation_queue(alert_data)
        
    else:
        # Low: Log for pattern analysis
        log_background_trend(alert_data)
```

## Live Intelligence Examples

### 🔴 **Critical Emergency Alert**
```
SEVERITY: 9 | AREA: Lower Manhattan | TIME: 2min ago
EVENT TYPE: Emergency | CROWD IMPACT: High
SIGNALS: Reddit (15 posts), Traffic (major incident), 911 (call spike)
PATTERN: "explosion" + "downtown" + traffic closure + emergency response
ACTION: ✅ Full investigation triggered automatically
```

### 🟡 **Major Event Alert**  
```
SEVERITY: 7 | AREA: Central Park | TIME: 2hr ago
EVENT TYPE: Festival | CROWD IMPACT: High | ESTIMATED: 50,000+ attendees
SIGNALS: Reddit (event posts), Traffic (street closures), Permits (scheduled)
PATTERN: "Summer Stage concert" + "road closures" + "large crowd gathering"
ACTION: 🎭 Event monitoring activated - resource coordination needed
```

### 🟡 **Public Gathering Alert**
```
SEVERITY: 6 | AREA: Brooklyn Bridge | TIME: 45min ago
EVENT TYPE: Protest | CROWD IMPACT: Medium | ESTIMATED: 5,000+ attendees
SIGNALS: Reddit (rally posts), Social media (demonstration), Traffic (delays)
PATTERN: "peaceful protest" + "bridge access" + "NYPD coordination"
ACTION: 📋 Crowd management protocols activated
```

### 🟢 **Background Event Trend**
```
SEVERITY: 3 | AREA: East Village | TIME: 2hr ago  
EVENT TYPE: Street Fair | CROWD IMPACT: Low | ESTIMATED: 1,000 attendees
SIGNALS: Reddit (local event), Permits (street fair permit)
PATTERN: Regular weekend street fair - normal neighborhood activity
ACTION: 📊 Logged for community event tracking
```

## Benefits

### **For City Officials**
- **Early Warning System**: Detect issues before they escalate
- **Data-Driven Insights**: Evidence-based decision making
- **Resource Optimization**: Focus investigation efforts on high-impact areas
- **Pattern Recognition**: Identify recurring problems and systemic issues

### **For Citizens**
- **Transparency**: Real-time view of city monitoring efforts
- **Responsiveness**: Faster identification and response to community issues
- **Accountability**: Public record of how issues are identified and addressed

### **For Atlas System**
- **Efficiency**: Lightweight monitoring reduces computational costs
- **Scalability**: Can monitor unlimited data sources
- **Intelligence**: Continuously learns from patterns and outcomes
- **Integration**: Seamlessly feeds the full multi-agent analysis pipeline

## Monitoring Metrics

### **System Health**
- Collection success rate per data source
- Triage agent response time and accuracy
- False positive/negative rates
- Alert resolution times

### **Intelligence Quality**
- Correlation accuracy between predicted and actual incidents
- User satisfaction with alert relevance
- Investigation outcome tracking
- Pattern recognition improvement over time

## Future Enhancements

### **Additional Data Sources**
- 📱 Social media sentiment analysis (Twitter/X, NextDoor)
- 🏥 Hospital emergency department volumes
- 🚆 Real-time transit crowding data
- 📈 Economic indicators (unemployment filings, business permits)
- 🌡️ IoT sensor networks (noise, air quality, traffic)

### **Advanced Analytics**
- 🧠 Machine learning pattern recognition
- 🔮 Predictive modeling for incident forecasting
- 🗺️ Geospatial clustering algorithms
- 📊 Time series anomaly detection

### **Integration Capabilities**
- 📧 Automated notifications to relevant city departments
- 📱 Mobile app for field investigators
- 🌐 Public API for transparency and civic engagement
- 🔗 Integration with existing city emergency response systems

---

The Monitor Agent represents the "always learning" aspect of Atlas - continuously scanning the digital pulse of NYC to identify patterns, anomalies, and opportunities for proactive city management. 