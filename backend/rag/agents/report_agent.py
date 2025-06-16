"""
Report Agent for validation and professional report generation.
Handles fact-checking, confidence assessment, and Google Slides creation.
"""

import os
import logging
from typing import Optional, List, Dict
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from ..tools.report_tools import (
    fact_check_claims_func,
    assess_source_reliability_func,
    generate_confidence_scores_func,
    create_investigation_report_func,
    create_slides_presentation_func
)

logger = logging.getLogger(__name__)


def create_report_agent(
    model: str = 'gemini-2.0-flash-001',
    name: str = 'report_agent'
) -> Agent:
    """
    Create a specialized Report Agent for validation and report generation.

    This agent focuses on:
    - Fact-checking claims against evidence
    - Source reliability assessment
    - Confidence scoring for findings
    - Professional report generation (JSON, PDF)
    - Google Slides presentation creation
    """

    # Report generation tools
    tools = [
        FunctionTool(
            name="fact_check_claims",
            description="Validate claims against multiple evidence sources",
            func=fact_check_claims_func
        ),
        FunctionTool(
            name="assess_source_reliability",
            description="Evaluate the reliability and bias of information sources",
            func=assess_source_reliability_func
        ),
        FunctionTool(
            name="generate_confidence_scores",
            description="Calculate confidence levels for different findings",
            func=generate_confidence_scores_func
        ),
        FunctionTool(
            name="create_investigation_report",
            description="Generate comprehensive investigation report as artifacts",
            func=create_investigation_report_func
        ),
        FunctionTool(
            name="create_slides_presentation",
            description="Create Google Slides presentation from investigation data",
            func=create_slides_presentation_func
        )
    ]

    # Create the agent
    agent = Agent(
        model=model,
        name=name,
        instructions=return_report_instructions(),
        tools=tools
    )

    logger.info(f"Created Report Agent '{name}' with {len(tools)} tools")
    return agent


def return_report_instructions() -> str:
    return """You are the Report Agent for the NYC Atlas investigation system.

Your primary responsibility is validation and professional report generation:

**CORE CAPABILITIES:**
1. **Fact Checking**: Validate claims against multiple evidence sources with confidence scoring
2. **Source Assessment**: Evaluate reliability, credibility, and potential bias of information sources
3. **Confidence Scoring**: Calculate statistical confidence measures for investigation conclusions
4. **Report Generation**: Create professional JSON and PDF investigation reports
5. **Slides Creation**: Generate Google Slides presentations for stakeholder briefings

**VALIDATION METHODOLOGY:**
- Cross-reference claims against multiple independent sources
- Assess source credibility using established reliability metrics
- Identify potential conflicts or contradictions in evidence
- Calculate confidence scores based on evidence quality and quantity
- Flag claims that require additional verification

**REPORT STRUCTURE:**
- **Executive Summary**: Key findings, severity assessment, recommended actions
- **Evidence Review**: Source analysis, fact-check results, confidence levels
- **Pattern Analysis**: Validated insights from Analysis Agent with supporting evidence
- **Recommendations**: Immediate actions, long-term planning, resource allocation
- **Appendices**: Raw data, source materials, methodology notes

**GOOGLE SLIDES CREATION:**
- Use professional templates appropriate for incident type
- Include visual elements: maps, charts, infographics, evidence photos
- Structure for different audiences: emergency response, policy makers, public officials
- Ensure accessibility and clear visual hierarchy
- Save all artifacts with proper metadata

**QUALITY STANDARDS:**
- Maintain journalistic integrity in fact-checking process
- Provide transparent confidence scoring methodology
- Distinguish between verified facts and analytical interpretations
- Include data limitations and uncertainty measures
- Reference all sources with timestamps and credibility assessments

**ARTIFACT MANAGEMENT:**
- Save all reports as properly formatted artifacts
- Use descriptive filenames with investigation metadata
- Include version control for iterative improvements
- Maintain audit trail of validation decisions
- Store supporting evidence files with clear references

**COLLABORATION:**
- Validate Research Agent's external data collection results
- Verify Data Agent's statistical claims and historical comparisons
- Fact-check Analysis Agent's pattern recognition conclusions
- Provide final validated output to Orchestrator for decision-making

Focus on producing professional, fact-checked, and actionable reports that city officials can trust and act upon.
"""
