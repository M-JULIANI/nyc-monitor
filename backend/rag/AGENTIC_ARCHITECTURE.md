# Agentic Architecture - NYC Atlas Investigation System

## Overview

The NYC Atlas system uses a **balanced 5-agent architecture** that follows ADK idioms with direct sub-agent coordination and leverages existing investigation infrastructure.

## Architecture Flow (ADK Idiomatic)

```
main.py (FastAPI)
    ↓
root_agent.py (ADK Entry Point - Coordinates 5 Direct Sub-Agents)
    ├── Research Agent (External data collection)
    ├── Data Agent (Internal knowledge & BigQuery)
    ├── Analysis Agent (Pattern recognition)
    └── Report Agent (Validation & deliverables)
    ↓
[Existing Investigation Infrastructure]
```

## ADK Integration

### **✅ Properly Structured** (ADK Idiomatic):
```python
Root Agent
├── Research Agent (sub_agent)
├── Data Agent (sub_agent)  
├── Analysis Agent (sub_agent)
└── Report Agent (sub_agent)
```

**Not**: ~~Root Agent → Orchestrator Agent → Sub-Agents~~ (extra layer)

## 5 Specialized Agents

### 1. **Root Agent** (`root_agent.py`) - **ADK Entry Point & Coordinator**
- **Role**: Main entry point, coordinates 5 direct sub-agents
- **Integration**: Uses `WorkflowManager`, `state_manager`, `progress_tracker`, `tracing`
- **Tools**: `update_alert_status`, `manage_investigation_state`
- **Sub-Agents**: All 4 specialized agents as direct children

### 2. **Research Agent** (`research_agent.py`)  
- **Role**: External data collection
- **Tools**: `web_search`, `collect_media_content`, `save_screenshot`, `list_artifacts`, `rag_retrieval`
- **Focus**: Web search, social media, live APIs, multimedia evidence

### 3. **Data Agent** (`data_agent.py`)
- **Role**: Internal knowledge and BigQuery datasets
- **Tools**: `search_knowledge_base`, `query_census_demographics`, `get_crime_statistics`, `find_similar_incidents`, `get_construction_permits`, `analyze_housing_market`, `rag_retrieval`
- **Focus**: Census data, crime stats, permits, housing market, historical patterns

### 4. **Analysis Agent** (`analysis_agent.py`)
- **Role**: Pattern recognition and cross-domain synthesis  
- **Tools**: `analyze_temporal_patterns`, `correlate_data_sources`, `identify_risk_factors`, `generate_hypotheses`
- **Focus**: Temporal/spatial patterns, risk assessment, hypothesis generation

### 5. **Report Agent** (`report_agent.py`)
- **Role**: Validation and professional output generation
- **Tools**: `fact_check_claims`, `assess_source_reliability`, `generate_confidence_scores`, `create_investigation_report`, `create_slides_presentation`
- **Focus**: Fact-checking, Google Slides creation, PDF reports

## Why We Keep Investigation Infrastructure

### **✅ Still Needed** (Complement ADK's implicit state):

#### **`progress_tracker.py`** - ✅ **ESSENTIAL**
- **Purpose**: Real-time streaming to frontend dashboard
- **Why**: ADK doesn't provide async progress streaming
- **Usage**: `progress_tracker.stream_progress(investigation_id)`

#### **`state_manager.py`** - ✅ **ESSENTIAL**
- **Purpose**: Investigation-specific state (phases, confidence, artifacts)
- **Why**: ADK's implicit state is generic, this is investigation-focused
- **Usage**: `state_manager.create_investigation(alert_data)`

#### **`tracing.py`** - ✅ **ESSENTIAL**
- **Purpose**: Detailed execution tracing and message flow
- **Why**: More granular than ADK's built-in tracing
- **Usage**: `tracer.trace_agent_execution()`

#### **`workflow.py`** - ✅ **ESSENTIAL**
- **Purpose**: Phase-based investigation logic and task generation
- **Why**: Investigation-specific workflow rules
- **Usage**: `workflow_manager.determine_next_phase(state)`

## Investigation Workflow

### **Phase-Based Coordination** (via `WorkflowManager`):

1. **RECONNAISSANCE**: Research + Data agents work in parallel
2. **ANALYSIS**: Analysis agent synthesizes findings
3. **DEEP_DIVE**: Additional investigation if confidence < 70%
4. **REPORTING**: Report agent validates and creates deliverables
5. **COMPLETE**: Investigation finished with actionable insights

## Key Benefits of This Structure

1. **ADK Idiomatic**: Direct sub-agent coordination (no unnecessary layers)
2. **Simple Integration**: Works with existing `main.py` flow
3. **No State Conflicts**: Leverages existing investigation infrastructure
4. **Clear Separation**: ADK handles agent coordination, investigation/ handles domain logic
5. **Efficient**: Parallel agent execution when beneficial
6. **Professional Output**: Automated Google Slides and report generation

## Usage

```python
# From main.py investigation endpoint
result = await root_agent_instance.investigate(investigation_prompt, context)

# Root agent coordinates 5 direct sub-agents based on workflow phases
# Uses existing investigation/ infrastructure for domain-specific needs
```

## Summary: **What Changed & Why**

### **❌ Removed**: 
- `orchestrator_agent.py` (unnecessary layer, not ADK idiomatic)

### **✅ Restructured**:
- Root agent now coordinates 5 direct sub-agents (ADK idiomatic)
- Coordination logic moved from orchestrator into root agent

### **✅ Kept All Investigation Infrastructure**:
- `progress_tracker.py` - Frontend streaming
- `state_manager.py` - Investigation state
- `tracing.py` - Detailed execution tracking  
- `workflow.py` - Phase-based logic

**Result**: Clean ADK structure + rich investigation capabilities! 