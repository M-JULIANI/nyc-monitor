# Architecture Overview

This diagram illustrates the complete Atlas NYC Monitor system, from continuous data collection through intelligent triage to on-demand investigation and report generation.

```mermaid
flowchart TD
    subgraph Users
        U[City Officials/Users]
    end

    subgraph Frontend["🖥️ Frontend Views"]
        Map[🗺️ Map View<br/>Alert Heatmap & Pins]
        Dashboard[📊 Dashboard<br/>Alert Stream & Triage]
        Reports[📋 Reports Gallery<br/>Generated Insights]
    end

    subgraph Background["⏰ Background Intelligence (Every 15min)"]
        Cron[🕐 Cloud Scheduler<br/>15-minute intervals]
        Collector[📡 Live Data Collector<br/>Reddit, HackerNews, Twitter, 311, Traffic]
        Triage[🧠 Triage Agent<br/>Vertex AI - Quick Analysis]
    end

    subgraph Storage["💾 Alert & Data Storage"]
        Firestore[(🔥 Firestore<br/>Alert Metadata & Status)]
        Vector[(🎯 Vertex AI Vector DB<br/>Document Content & Embeddings)]
        BigQuery[(📊 BigQuery<br/>Static Datasets & Analytics)]
        CloudStorage[(☁️ Cloud Storage<br/>Files, Images, Templates)]
    end

    subgraph Investigation["🔍 On-Demand Investigation System"]
        Orchestrator[🎯 Orchestrator Agent<br/>Alert Review & Coordination]
        ResearchAgent[🔍 Research Agent<br/>Multi-Source Data Collection<br/>Web Search + Social Media + Live APIs]
        DataAgent[📊 Data Agent<br/>Internal Knowledge Expert<br/>Vector DB + BigQuery + Tool Calling]
        AnalysisAgent[🧠 Analysis Agent<br/>Pattern Recognition & Synthesis<br/>Cross-Domain Insights]
        ReportAgent[📝 Report Agent<br/>Validation + Report Generation<br/>Fact-Check + Google Slides]
    end

    subgraph Outputs["📤 Generated Outputs"]
        GSlides[📊 Google Slides Documents<br/>Generated via API]
        Insights[💡 Actionable Insights<br/>Indexed in Vector DB]
    end

    %% Background Flow
    Cron --> Collector
    Collector --> Triage
    Triage --> Firestore
    Collector --> Vector

    %% User Interface
    U --> Map
    U --> Dashboard  
    U --> Reports

    %% Frontend Data Sources
    Map -.-> Firestore
    Dashboard -.-> Firestore
    Reports -.-> CloudStorage

    %% Investigation Trigger
    Dashboard --> Orchestrator
    Firestore --> Orchestrator

    %% Investigation Flow - Orchestrator assigns tasks
    Orchestrator --> ResearchAgent
    Orchestrator --> DataAgent
    Orchestrator --> AnalysisAgent
    Orchestrator --> ReportAgent
    
    %% Agents query data experts
    ResearchAgent --> Vector
    DataAgent --> Vector
    AnalysisAgent --> Vector
    ReportAgent --> Vector
    
    %% Data expert access
    ResearchAgent --> BigQuery
    DataAgent --> BigQuery
    
    %% External data collection
    ResearchAgent --> CloudStorage
    DataAgent --> CloudStorage
    
    %% Analysis and synthesis
    AnalysisAgent --> ReportAgent
    
    ReportAgent --> GSlides
    ReportAgent --> CloudStorage
    ReportAgent --> Firestore
    
    %% Knowledge building
    ReportAgent --> Vector
    GSlides -.-> Reports

    %% Styling
    classDef background fill:#e1f5fe
    classDef investigation fill:#f3e5f5
    classDef storage fill:#e8f5e8
    classDef frontend fill:#fff3e0
    classDef output fill:#fce4ec
    classDef rag fill:#e8eaf6

    class Cron,Collector,Triage background
    class Orchestrator,ResearchAgent,DataAgent,AnalysisAgent,ReportAgent investigation
    class Vector,BigQuery,CloudStorage storage
    class Map,Dashboard,Reports frontend
    class GSlides,Insights output
```

## System Components

### 🔄 **Continuous Background Intelligence**
- **Cloud Scheduler**: Triggers data collection every 15 minutes
- **Live Data Collector**: Scans Reddit, HackerNews, Twitter, 311, HackerNews, traffic APIs for NYC signals
- **Triage Agent**: Lightweight Vertex AI analysis assigns severity scores (1-10)
- **Alert Storage**: Prioritized alerts stored in Firestore with status tracking

### 🎯 **Smart Investigation System**
- **Orchestrator Agent**: Reviews recent alerts, decides which warrant deep investigation, coordinates agent assignments
- **Research Agent**: Multi-source data collection from web search, social media, and live APIs
- **Data Agent**: Internal knowledge expert in Vector DB and BigQuery, capable of tool calling
- **Analysis Agent**: Pattern recognition and synthesis across data domains
- **Report Agent**: Validation and report generation, fact-checking and Google Slides report creation

### 💾 **Intelligent Data Layer**
- **Firestore**: Real-time alert queue with status tracking (New → Investigating → Resolved)
- **Vertex AI Vector DB**: All collected data indexed for semantic search
- **BigQuery**: Static datasets (census, permits, historical trends)
- **Cloud Storage**: Generated reports, images, and media assets

## Data Storage Strategy

### 🔥 **Firestore - Real-time Operations & Alert Metadata**
**Use Case**: Fast queries, real-time updates, agent coordination
```json
{
  "alerts/alert_id": {
    "severity": 7,
    "status": "investigating",
    "event_type": "traffic_incident", 
    "location": {"lat": 40.7, "lng": -73.9, "address": "Brooklyn Bridge"},
    "created_at": "2025-06-03T15:30:00Z",
    "sources": ["reddit", "twitter", "hackernews"],
    "investigation_metadata": {
      "assigned_agents": ["ResearchAgent", "DataAgent"],
      "document_count": 15,
      "confidence_score": 0.85
    }
  }
}
```

### 🎯 **Vertex AI Vector DB - Semantic Search Content**
**Use Case**: Find similar documents, cross-reference patterns, semantic queries
```json
{
  "documents/doc_id": {
    "content": "Full text content for embedding and search...",
    "source": "reddit_r_brooklyn", 
    "alert_id": "2025-06-03_brooklyn_traffic_001",
    "embedding": [0.1, 0.2, 0.3, ...], // Auto-generated
    "metadata": {
      "timestamp": "2025-06-03T15:25:00Z",
      "sentiment": "frustrated",
      "location_mentions": ["Brooklyn Bridge", "FDR Drive"],
      "keywords": ["traffic", "accident", "delay"]
    }
  }
}
```

### 📊 **BigQuery - Structured Analytics & Historical Data**
**Use Case**: Complex queries, joins, time-series analysis, statistical aggregations
```sql
-- Example tables
census_demographics (tract_id, population, median_income, demographics)
construction_permits (permit_id, address, start_date, type, status)
historical_incidents (date, location, type, severity, resolution_time)
traffic_patterns (hour, day_of_week, location, avg_volume, incidents)
```

### ☁️ **Cloud Storage - Files, Templates, Generated Content**
**Use Case**: Large files, images, document templates, generated reports
```
/bucket/
├── templates/
│   ├── incident_report_template.json (Google Slides template ID)
│   ├── pattern_analysis_template.json
│   └── emergency_response_template.json
├── generated_reports/
│   ├── 2025-06-03_brooklyn_traffic_analysis/
│   │   ├── metadata.json (slide doc ID, creation time, etc.)
│   │   └── images/ (charts, maps, photos)
├── raw_images/
│   ├── satellite_imagery/
│   ├── social_media_photos/
│   └── traffic_cameras/
└── data_exports/ (backups, bulk exports)
```

## Google Slides Report Generation

### 📝 **Template-Based Report Creation**
```python
# Report Creator Agent Process
def generate_investigation_report(alert_id, investigation_data):
    """Use Google Slides API with predefined templates"""
    
    # 1. Select appropriate template
    template_id = select_template(alert_data.event_type)
    
    # 2. Create new presentation from template
    slides_service = build('slides', 'v1')
    new_presentation = slides_service.presentations().create({
        'title': f"NYC Alert Analysis - {alert_data.location} - {alert_data.date}"
    }).execute()
    
    # 3. Populate with investigation findings
    populate_slides({
        'title_slide': {
            'alert_summary': investigation_data.summary,
            'severity_score': alert_data.severity,
            'location_map': generate_location_map(alert_data.location)
        },
        'data_sources_slide': {
            'reddit_posts': investigation_data.reddit_findings,
            'news_articles': investigation_data.web_search_results,
            'official_data': investigation_data.static_data_insights
        },
        'analysis_slide': {
            'pattern_analysis': investigation_data.synthesized_patterns,
            'confidence_scores': investigation_data.validation_results,
            'risk_assessment': investigation_data.risk_analysis
        },
        'recommendations_slide': {
            'immediate_actions': investigation_data.urgent_recommendations,
            'long_term_planning': investigation_data.strategic_insights,
            'resource_allocation': investigation_data.resource_needs
        }
    })
    
    # 4. Store metadata and make accessible
    report_metadata = {
        'slides_document_id': new_presentation['presentationId'],
        'alert_id': alert_id,
        'created_at': datetime.utcnow(),
        'template_used': template_id,
        'public_url': f"https://docs.google.com/presentation/d/{new_presentation['presentationId']}"
    }
    
    # Store in Cloud Storage and update Firestore
    store_report_metadata(report_metadata)
    update_alert_status(alert_id, 'report_generated', report_metadata)
```

### 🎨 **Template Structure Examples**
```json
{
  "incident_report_template": {
    "template_id": "1BxAR...Google_Slides_Template_ID",
    "slides": [
      {"title": "Alert Summary", "placeholders": ["{{alert_title}}", "{{severity}}", "{{location_map}}"]},
      {"title": "Data Sources", "placeholders": ["{{reddit_summary}}", "{{news_sources}}", "{{official_data}}"]},
      {"title": "Analysis", "placeholders": ["{{pattern_insights}}", "{{confidence_chart}}", "{{timeline}}"]},
      {"title": "Recommendations", "placeholders": ["{{immediate_actions}}", "{{long_term_plans}}"]}
    ]
  }
}
```

This approach gives you:
- **Firestore**: Fast alert operations and real-time coordination
- **Vector DB**: Powerful semantic search across collected content  
- **BigQuery**: Complex analytics on structured datasets
- **Google Slides API**: Professional, templated reports generated programmatically
- **Cloud Storage**: File management and template storage

## Data Flow Examples

### 🚨 **Emergency Alert Path**
```
Reddit Post: "Fire on 5th Ave" → Triage Agent (Severity: 9) 
→ Firestore Alert → Dashboard Notification → User Triggers Investigation 
→ Orchestrator → ResearchAgent (social media dive) + DataAgent (area demographics) 
→ AnalysisAgent (risk assessment) → ReportAgent (validated emergency report)
```

### 🎭 **Event Monitoring Path**
```
Twitter: "Pride Parade prep" → Triage Agent (Severity: 6) 
→ Orchestrator Auto-Investigation → ResearchAgent (news + social monitoring) 
→ DataAgent (historical crowd data + permits) → AnalysisAgent (traffic predictions) 
→ ReportAgent (resource planning report)
```

### 📊 **Pattern Discovery Path**
```
Multiple 311 Complaints → Triage Agent Groups by Area 
→ DataAgent (construction permits + demographic analysis) 
→ ResearchAgent (resident social media sentiment) 
→ AnalysisAgent (cross-domain correlation) → ReportAgent (policy recommendation)
```

## **Benefits of 5-Agent Architecture**

### ✅ **Balanced Specialization**
- **Clear Roles**: Each agent has distinct, meaningful responsibilities
- **Reduced Overhead**: Fewer coordination handoffs while maintaining specialization
- **Tool-Rich Agents**: Each agent has comprehensive tool access for their domain

### 🎯 **Competition-Friendly**
- **Multi-Agent Coordination**: Still demonstrates sophisticated agent interactions
- **Autonomous Operation**: Each agent can work independently with their toolset
- **Meaningful Specialization**: Not over-engineered, but clearly differentiated roles

### 🔄 **Data Flow Efficiency**
- **Research Agent**: All external data collection in one place
- **Data Agent**: All internal knowledge queries centralized
- **Analysis Agent**: Dedicated pattern recognition and synthesis
- **Report Agent**: Combined validation and output generation
- **Orchestrator**: Simplified coordination with fewer agents to manage

## Alert Status Lifecycle

```
📥 New Alert (Triage Agent) 
    ↓
🎯 Review Queue (Orchestrator Decision)
    ↓
🔍 Investigating (Multi-Agent Analysis)
    ↓
📋 Report Generated (Google Slides)
    ↓
✅ Resolved | ⏭️ No Investigation Needed
```

## Trigger Strategy

### **Continuous (15-min intervals)**
- Light monitoring and pattern detection
- Alert generation and priority scoring  
- Background knowledge building

### **On-Demand (User-triggered)**
- Deep investigation of specific alerts
- Comprehensive multi-agent analysis
- Professional report generation (5-10 minutes)

This hybrid approach provides continuous intelligence while keeping compute costs manageable for demo and production use.

### 🖥️ **Three-View Frontend**
1. **Map View**: Geographic alert heatmap with real-time pins and priority color-coding
2. **Dashboard**: Alert stream with triage controls and investigation triggers  
3. **Reports Gallery**: Links to generated insights and Google Slides reports

### 🤔 **Agent Coordination Strategy**

**Current Model: Orchestrator as Coordinator**
The Orchestrator currently handles:
- Alert triage and investigation decisions
- Initial agent assignments
- Basic workflow coordination

**Potential Enhancement: Dedicated Moderator Agent**
A specialized moderator could provide:
- **Task Assignment Intelligence**: "Given traffic incident X, assign ResearchAgent to search recent posts, DataAgent to pull historical traffic data for this intersection"
- **Focus Management**: Prevent agents from going off-topic or down rabbit holes
- **Quality Control**: Ensure agents stay within scope and deliver relevant results
- **Dynamic Re-assignment**: Adjust agent tasks based on emerging findings
- **Collaboration Orchestration**: Coordinate multi-agent conversations and debates

**Recommendation**: Start with enhanced Orchestrator, evolve to dedicated Moderator if coordination becomes complex.

## **Architectural Decision: 5-Agent Sweet Spot**

### 🎯 **Why 5 Agents Instead of 8+?**

**Previously**: 8 specialized agents (Orchestrator, RAG, BigQuery, Targeted Search, Web Search, Synthesizer, Validator, Reporter)
**Now**: 5 balanced agents with comprehensive tooling

### 🔧 **Tool-Rich Agents vs Many Simple Agents**

**Advantages of Current Approach:**
- **Meaningful Specialization**: Each agent has a clear, substantial domain
- **Reduced Coordination Overhead**: Fewer handoffs, simpler orchestration  
- **Tool Autonomy**: Agents can choose appropriate tools for their tasks
- **Competition-Ready**: Demonstrates sophisticated multi-agent coordination without over-engineering
- **Scalable**: Easy to add tools to existing agents rather than creating new agents

**Agent Tool Distribution:**
```
Orchestrator: Coordination & assignment tools
ResearchAgent: 4+ external data collection tools  
DataAgent: 6+ internal knowledge & static data tools
AnalysisAgent: 4+ pattern recognition & synthesis tools
ReportAgent: 4+ validation & output generation tools
```

This approach balances **multi-agent sophistication** with **practical architecture**, giving you intelligent specialization without coordination complexity.

## Research Agent - Multi-Source Data Collection

### 🔍 **Core Capabilities**
The Research Agent handles all external data collection from multiple sources using appropriate tools for each data type.

**Tool Calling Functions:**
```python
@tool
def search_social_media(platform: str, query: str, location: str = None, time_range: str = "24h") -> List[Dict]:
    """Search Reddit, HackerNews, Twitter for recent posts and discussions"""
    # Returns social media content, sentiment, engagement metrics

@tool
def web_search(query: str, source_types: List[str] = ["news", "official", "academic"]) -> List[Dict]:
    """Comprehensive web search across multiple source types"""
    # Returns news articles, official statements, research papers

@tool
def query_live_apis(api_name: str, location: str, parameters: Dict) -> Dict:
    """Query live data APIs (311, traffic, weather, transit)"""
    # Returns real-time city data, traffic conditions, service alerts

@tool
def collect_media_content(search_terms: List[str], content_types: List[str]) -> List[Dict]:
    """Gather images, videos, and multimedia content"""
    # Returns relevant visual content from social media and web sources
```

## Data Agent - Internal Knowledge & Static Data Expert

### 📊 **Core Capabilities**
The Data Agent serves as the expert on both ingested knowledge corpus and static datasets, combining both Vector DB and BigQuery access.

**Tool Calling Functions:**
```python
@tool
def search_knowledge_base(query: str, filters: Dict = None) -> List[Dict]:
    """Semantic search across all collected documents and past investigations"""
    # Searches Vector DB for relevant content from past investigations

@tool
def query_census_demographics(location: str, metrics: List[str]) -> Dict:
    """Query ACS census data for specific NYC areas"""
    # Returns population, income, age, education, housing data

@tool
def get_crime_statistics(area: str, time_period: str, crime_types: List[str] = None) -> Dict:
    """Retrieve historical crime data for area analysis"""
    # Returns NYPD crime statistics, trends, comparisons

@tool
def find_similar_incidents(incident_description: str, location: str = None) -> List[Dict]:
    """Find past incidents similar to current investigation"""
    # Uses embeddings to find pattern matches in historical data

@tool
def get_construction_permits(area: str, date_range: str) -> List[Dict]:
    """Retrieve construction and development permits"""
    # Returns DOB permits, project types, timelines, impact assessments

@tool
def analyze_housing_market(area: str, time_period: str) -> Dict:
    """Analyze housing costs, availability, and displacement patterns"""
    # Returns rent prices, eviction rates, gentrification indicators
```

## Analysis Agent - Pattern Recognition & Synthesis

### 🧠 **Core Capabilities**
The Analysis Agent synthesizes information from multiple sources to identify patterns, connections, and insights across data domains.

**Tool Calling Functions:**
```python
@tool
def analyze_temporal_patterns(events: List[Dict], time_window: str) -> Dict:
    """Identify temporal patterns in event data"""
    # Returns frequency analysis, seasonal trends, peak times

@tool
def correlate_data_sources(research_data: Dict, static_data: Dict) -> Dict:
    """Find correlations between live data and historical patterns"""
    # Cross-references social media sentiment with demographic/economic data

@tool
def identify_risk_factors(incident_data: Dict, area_context: Dict) -> Dict:
    """Assess risk factors and potential escalation patterns"""
    # Combines multiple data sources to assess incident severity and spread risk

@tool
def generate_hypotheses(collected_data: Dict) -> List[Dict]:
    """Generate testable hypotheses about incident causes and implications"""
    # Creates structured hypotheses for validation based on available evidence
```

## Report Agent - Validation & Report Generation

### 📝 **Core Capabilities**
The Report Agent handles fact-checking, confidence assessment, and professional report generation.

**Tool Calling Functions:**
```python
@tool
def fact_check_claims(claims: List[str], evidence_sources: List[Dict]) -> Dict:
    """Validate claims against multiple evidence sources"""
    # Returns confidence scores and supporting/contradicting evidence

@tool
def assess_source_reliability(sources: List[Dict]) -> Dict:
    """Evaluate the reliability and bias of information sources"""
    # Returns credibility scores and potential bias indicators

@tool
def generate_confidence_scores(analysis_results: Dict) -> Dict:
    """Calculate confidence levels for different findings"""
    # Returns statistical confidence measures for investigation conclusions

@tool
def create_slides_report(investigation_data: Dict, template_type: str) -> Dict:
    """Generate professional Google Slides report"""
    # Creates formatted presentation with charts, maps, and recommendations
```

## Investigation Workflow Deep Dive

### 🔄 **Iterative Investigation Process**

The investigation system operates as an **adaptive, iterative workflow** rather than a simple linear task delegation. The Orchestrator Agent manages a dynamic process that evolves based on findings, with the ability to:

1. **Create initial task assignments**
2. **Review intermediate findings** 
3. **Generate follow-up questions and subtasks**
4. **Coordinate agent collaboration**
5. **Adapt investigation scope** based on discoveries

### 🎯 **Three-Phase Investigation Cycle**

#### **Phase 1: Initial Reconnaissance (Parallel)**
```
Orchestrator → [ResearchAgent, DataAgent] (simultaneous)
├── ResearchAgent: "Scan social media and news for [incident_type] at [location]"
├── DataAgent: "Pull demographics, crime stats, and recent incidents for [area]"
└── Timeline: 60-90 seconds for initial data collection
```

#### **Phase 2: Analysis & Hypothesis Generation (Sequential)**
```
Findings Review → Analysis Agent → Hypothesis Formation
├── Orchestrator: "Based on initial findings, what patterns emerge?"
├── AnalysisAgent: "Cross-reference social sentiment with demographic stress factors"
├── Output: 2-3 testable hypotheses with evidence requirements
└── Timeline: 45-60 seconds for pattern analysis
```

#### **Phase 3: Targeted Deep Dive (Adaptive Iteration)**
```
Hypothesis Testing → Refined Questions → Additional Data Collection
├── Orchestrator: "Hypothesis X needs validation - ResearchAgent, find more evidence on Y"
├── Dynamic Subtasks: Based on emerging questions
├── Collaborative Validation: Agents cross-check each other's findings
└── Timeline: 120-180 seconds (may repeat if new questions arise)
```

### 🧠 **Orchestrator Decision Logic**

#### **Initial Task Assignment Strategy**
```python
def create_initial_investigation_plan(alert_data):
    """Orchestrator generates adaptive task assignments"""
    
    investigation_scope = determine_scope(alert_data.severity, alert_data.event_type)
    
    initial_tasks = {
        "research_agent": {
            "primary": f"Collect recent social media and news about {alert_data.summary}",
            "focus_areas": get_search_keywords(alert_data),
            "time_range": "last 4 hours" if alert_data.severity > 7 else "last 24 hours",
            "success_criteria": "Find 5+ relevant posts with location confirmation"
        },
        "data_agent": {
            "primary": f"Analyze area context for {alert_data.location}",
            "datasets": ["demographics", "recent_incidents", "infrastructure"],
            "success_criteria": "Identify 3+ contextual risk factors"
        }
    }
    
    return initial_tasks
```

#### **Adaptive Iteration Logic**
```python
def review_and_iterate(investigation_state):
    """Orchestrator evaluates findings and decides next steps"""
    
    findings_quality = assess_findings_completeness(investigation_state.findings)
    
    if findings_quality.confidence < 0.7:
        # Generate targeted follow-up questions
        follow_up_tasks = generate_targeted_questions(
            initial_findings=investigation_state.findings,
            knowledge_gaps=findings_quality.gaps
        )
        return continue_investigation(follow_up_tasks)
    
    elif findings_quality.new_hypotheses:
        # New patterns discovered - need validation
        validation_tasks = create_validation_tasks(findings_quality.new_hypotheses)
        return continue_investigation(validation_tasks)
    
    else:
        # Sufficient evidence collected - proceed to analysis
        return trigger_synthesis_phase(investigation_state.findings)
```

### 📋 **Dynamic Task Refinement Examples**

#### **Example 1: Traffic Incident Investigation**
```
Initial Alert: "Major delays on Brooklyn Bridge - Reddit reports"

Phase 1 Tasks:
├── ResearchAgent: "Search social media for Brooklyn Bridge traffic incidents"
├── DataAgent: "Get current traffic patterns and recent construction permits"

Phase 1 Findings:
├── ResearchAgent: "Multiple posts about 'police activity', not just traffic"
├── DataAgent: "No scheduled construction, but area has 3x normal incident rate"

Orchestrator Analysis: "Incident type unclear - need clarification"

Phase 2 Iteration:
├── ResearchAgent: "Narrow search to 'police activity Brooklyn Bridge' last 2 hours"
├── DataAgent: "Pull crime statistics and recent police reports for this area"
├── New Question: "Is this a traffic incident or security event?"

Phase 2 Findings:
├── ResearchAgent: "Social media mentions 'suspicious package investigation'"
├── DataAgent: "Area flagged for recent security concerns in city database"

Orchestrator Decision: "Security event confirmed - escalate priority, different report template"
```

#### **Example 2: Community Pattern Discovery**
```
Initial Alert: "Multiple 311 complaints - noise issues in Williamsburg"

Phase 1 Tasks:
├── ResearchAgent: "Search resident social media complaints about noise"
├── DataAgent: "Analyze 311 complaint patterns and area demographics"

Phase 1 Findings:
├── ResearchAgent: "Residents posting about 'construction noise' but also 'late night parties'"
├── DataAgent: "Complaints increased 400% in last month, area gentrifying rapidly"

Orchestrator Analysis: "Two distinct noise sources - need to separate patterns"

Phase 2 Iteration:
├── ResearchAgent: "Separate search: construction vs. nightlife noise complaints"
├── DataAgent: "Cross-reference building permits with entertainment licenses"
├── AnalysisAgent: "Look for correlation between demographic changes and complaint types"

Phase 2 Findings:
├── ResearchAgent: "Construction complaints: daytime, older residents. Party complaints: weekend nights, newer residents"
├── DataAgent: "3 new construction projects + 5 new bars/restaurants opened recently"
├── AnalysisAgent: "Classic gentrification tension pattern - old vs. new resident priorities"

Orchestrator Decision: "Policy recommendation needed - multi-stakeholder mediation report"
```

### 🔀 **Agent Collaboration Patterns**

#### **Parallel Collection → Cross-Validation**
```python
# Agents work simultaneously, then validate each other's findings
research_findings = ResearchAgent.collect_social_media_data()
static_findings = DataAgent.get_historical_context()

# Cross-validation step
validated_social = DataAgent.verify_claims(research_findings.claims)
contextualized_data = ResearchAgent.find_recent_examples(static_findings.patterns)
```

#### **Hypothesis Testing Chain**
```python
# AnalysisAgent generates testable hypotheses
hypotheses = AnalysisAgent.generate_hypotheses(all_findings)

# Other agents collect targeted evidence
for hypothesis in hypotheses:
    supporting_evidence = ResearchAgent.find_evidence(hypothesis.research_questions)
    statistical_support = DataAgent.test_hypothesis(hypothesis.statistical_claims)
    
    confidence_score = ReportAgent.assess_evidence_quality(supporting_evidence, statistical_support)
```

### ⚡ **Real-Time Adaptation Triggers**

#### **Quality Thresholds**
- **Low Confidence (<0.6)**: Automatically trigger additional data collection
- **Contradictory Evidence**: Pause investigation, resolve conflicts before proceeding
- **High Urgency (Severity 9+)**: Skip iterations, proceed with available evidence

#### **Discovery-Driven Pivots**
- **Scope Expansion**: Minor incident reveals larger pattern → expand investigation area
- **Event Type Reclassification**: Traffic incident is actually security event → change agent assignments
- **Stakeholder Discovery**: Investigation reveals additional affected communities → broaden data collection

### 🎛️ **Orchestrator Prompting Strategy**

#### **Adaptive Investigation Prompts**
```python
ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Orchestrator Agent managing a dynamic investigation workflow. Your role is to:

1. **Initial Assessment**: Review alert data and assign appropriate initial tasks
2. **Progress Monitoring**: Continuously evaluate investigation quality and completeness  
3. **Adaptive Refinement**: Generate follow-up questions when findings are incomplete or contradictory
4. **Resource Management**: Balance investigation depth with time constraints
5. **Quality Control**: Ensure agents stay focused and deliver actionable insights

**Decision Framework**:
- If findings confidence < 70%: Create targeted follow-up tasks
- If new patterns emerge: Assign validation tasks to other agents
- If contradictions found: Coordinate agent collaboration to resolve
- If sufficient evidence: Proceed to synthesis and reporting

**Investigation Termination Criteria**:
- High confidence (>85%) with actionable insights
- Maximum investigation time reached (8 minutes)  
- Critical/emergency situations requiring immediate response
- Diminishing returns on additional data collection

For each investigation step, provide:
- Task assignment rationale
- Success criteria for each agent
- Estimated timeline
- Conditions for proceeding to next phase
"""
```

This iterative approach enables the system to **start broad, narrow focus through iteration**, and **adapt to discoveries** while maintaining efficiency and avoiding endless investigation loops.

### ⏱️ **Investigation Timeline Example**

**Total Investigation Time: 6-8 minutes**
```
00:00 - Alert received, Orchestrator reviews
00:30 - Initial tasks assigned (Research + Data agents)
02:00 - Phase 1 findings reviewed
02:30 - Follow-up questions generated, refined tasks assigned
04:30 - Phase 2 findings cross-validated
05:00 - Analysis agent synthesizes patterns
06:30 - Report agent validates and generates output
08:00 - Investigation complete, report delivered
```

The investigation can terminate early for high-confidence findings or extend with additional iterations based on the complexity and importance of the alert.
