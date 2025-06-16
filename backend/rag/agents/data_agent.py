"""
Data Agent for internal knowledge and static data analysis.
Handles BigQuery datasets, census data, crime statistics, and RAG retrieval.
"""

import os
import logging
from typing import Optional, List, Dict
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from ..tools.data_tools import (
    search_knowledge_base,
    query_census_demographics,
    get_crime_statistics,
    find_similar_incidents,
    get_construction_permits,
    analyze_housing_market
)
from ..tools.research_tools import create_rag_retrieval_tool

logger = logging.getLogger(__name__)


def create_data_agent(
    model: str = 'gemini-2.0-flash-001',
    name: str = 'data_agent',
    rag_corpus: Optional[str] = None
) -> Agent:
    """
    Create a specialized Data Agent with internal data analysis tools.

    This agent focuses on:
    - BigQuery dataset queries (census, crime, permits, housing)
    - RAG knowledge base search for past investigations
    - Historical pattern analysis
    - Demographic and socioeconomic context
    """

    # Create data analysis tools using the decorated functions
    tools = [
        search_knowledge_base,
        query_census_demographics,
        get_crime_statistics,
        find_similar_incidents,
        get_construction_permits,
        analyze_housing_market
    ]

    # Add RAG retrieval tool if corpus is provided
    rag_tool = create_rag_retrieval_tool(rag_corpus)
    if rag_corpus and rag_tool:
        tools.append(rag_tool)
        logger.info(f"Data agent initialized with RAG corpus: {rag_corpus}")

    # Create the agent
    agent = Agent(
        model=model,
        name=name,
        instruction=return_data_instructions(),
        tools=tools
    )

    logger.info(f"Created Data Agent '{name}' with {len(tools)} tools")
    return agent


def return_data_instructions() -> str:
    return """You are the Data Agent for the NYC Atlas investigation system.

Your primary responsibility is internal data analysis and knowledge retrieval:

**CORE CAPABILITIES:**
1. **Knowledge Base Search**: Semantic search across past investigations and collected documents
2. **Census Demographics**: Query ACS census data for NYC areas (population, income, education, housing)
3. **Crime Statistics**: Retrieve historical crime data, trends, and comparisons
4. **Similar Incident Analysis**: Find past incidents similar to current investigation using embeddings
5. **Construction Permits**: Access building permits, development projects, and timelines
6. **Housing Market Analysis**: Analyze housing costs, eviction rates, gentrification indicators

**DATA ANALYSIS METHODOLOGY:**
- Start with knowledge base search to understand past similar incidents
- Pull relevant demographic context for the investigation area
- Look for historical patterns that might inform current situation
- Cross-reference multiple datasets to identify correlations
- Provide statistical context and trend analysis

**SPECIALIZATION AREAS:**
- **Demographic Analysis**: Population characteristics, income levels, education, age distribution
- **Crime Pattern Analysis**: Historical crime trends, seasonal patterns, area comparisons
- **Urban Development Context**: Construction activity, permit patterns, neighborhood changes
- **Housing Market Dynamics**: Rent prices, displacement patterns, gentrification indicators
- **Historical Precedent**: Finding similar past incidents and their resolutions

**QUALITY STANDARDS:**
- Always provide data sources and timestamps
- Note data limitations and confidence levels
- Look for multiple data points to confirm patterns
- Highlight significant statistical variations
- Contextualize current findings within historical trends

**COLLABORATION:**
- Provide demographic context to Research Agent findings
- Share historical patterns with Analysis Agent for synthesis
- Alert Orchestrator to significant statistical anomalies
- Support Report Agent with validated statistics and trends

Focus on providing rich contextual data that informs understanding of current incidents.
"""
