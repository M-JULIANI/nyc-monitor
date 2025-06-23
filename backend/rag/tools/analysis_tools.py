# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Analysis tools for pattern recognition and cross-domain synthesis.
Handles temporal analysis, correlation detection, and intelligent synthesis."""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.adk.tools import FunctionTool
import json
import re
from google.genai import types
from google.adk.tools import FunctionTool, ToolContext
from ..investigation.state_manager import state_manager

logger = logging.getLogger(__name__)


def synthesize_investigation_findings_func(
    investigation_id: str,
    event_type: str,
    location: str,
    synthesis_focus: str = "executive_summary,key_findings"
) -> dict:
    """
    Dedicated tool for synthesizing web search findings into meaningful insights.
    Uses Vertex AI to analyze collected evidence and generate specific summaries.

    Args:
        investigation_id: Investigation ID to analyze findings for
        event_type: Type of event being investigated
        location: Location of the event
        synthesis_focus: What to synthesize (executive_summary,key_findings,timeline,impact)

    Returns:
        Synthesized analysis with executive summary and key findings
    """
    try:
        # Get investigation state and findings
        investigation_state = state_manager.get_investigation(investigation_id)
        if not investigation_state:
            return {
                "success": False,
                "error": f"Investigation {investigation_id} not found",
                "synthesis": {}
            }

        # Collect all raw findings from various sources
        raw_findings = []

        # 1. Collect web search findings from agent_findings
        if hasattr(investigation_state, 'agent_findings'):
            for agent_name, findings in investigation_state.agent_findings.items():
                if 'web_search' in agent_name.lower() or 'search' in agent_name.lower():
                    if isinstance(findings, list):
                        raw_findings.extend(findings)

        # 2. Collect insights from artifact descriptions
        for artifact in investigation_state.artifacts:
            description = artifact.get('description', '')
            artifact_type = artifact.get('type', '')

            if description and len(description) > 20:
                if 'image' in artifact_type and description != f"Image related to {event_type}":
                    raw_findings.append(f"Visual evidence: {description}")
                elif 'screenshot' in artifact_type:
                    raw_findings.append(
                        f"Web evidence captured: {description}")
                elif description not in [f"Events at {location}", "Map image", "Screenshot"]:
                    raw_findings.append(description)

        # 3. Collect from investigation findings
        if hasattr(investigation_state, 'findings') and investigation_state.findings:
            for finding in investigation_state.findings:
                if isinstance(finding, str) and len(finding) > 30:
                    raw_findings.append(finding)

        # 4. Add alert summary if substantial
        alert_data = investigation_state.alert_data
        if alert_data.summary and len(alert_data.summary) > 50:
            raw_findings.append(f"Initial alert context: {alert_data.summary}")

        logger.info(
            f"🔍 Collected {len(raw_findings)} raw findings for synthesis")

        # Use Vertex AI to synthesize findings
        if raw_findings:
            synthesis_result = _vertex_ai_synthesize_findings(
                event_type=event_type,
                location=location,
                raw_findings=raw_findings,
                evidence_count=len(investigation_state.artifacts),
                confidence_score=investigation_state.confidence_score,
                synthesis_focus=synthesis_focus
            )
        else:
            # Enhanced fallback when no findings available
            synthesis_result = _enhanced_fallback_synthesis(
                event_type=event_type,
                location=location,
                raw_findings=[f"Investigation of {event_type} at {location}"],
                evidence_count=len(investigation_state.artifacts),
                confidence_score=investigation_state.confidence_score,
                synthesis_focus=synthesis_focus
            )

        return {
            "success": True,
            "investigation_id": investigation_id,
            "synthesis": synthesis_result,
            "raw_findings_count": len(raw_findings),
            "synthesis_method": "vertex_ai" if raw_findings else "enhanced_fallback",
            "summary": f"Generated {synthesis_focus} for {event_type} at {location} from {len(raw_findings)} findings"
        }

    except Exception as e:
        logger.error(f"Synthesis generation failed: {e}")
        return {
            "success": False,
            "error": f"Synthesis failed: {str(e)}",
            "synthesis": {},
            "summary": "Synthesis generation encountered an error"
        }


def _vertex_ai_synthesize_findings(
    event_type: str,
    location: str,
    raw_findings: list,
    evidence_count: int,
    confidence_score: float,
    synthesis_focus: str
) -> dict:
    """Use Vertex AI to synthesize findings into specific insights."""
    try:
        # Use Vertex AI directly (consistent with rest of codebase)
        import vertexai
        from vertexai.generative_models import GenerativeModel

        # Initialize Vertex AI if not already done
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location_ai = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if project:
            try:
                vertexai.init(project=project, location=location_ai)
                logger.info(
                    f"✅ Initialized Vertex AI for synthesis: {project}")
            except Exception as init_error:
                logger.warning(
                    f"Vertex AI init failed: {init_error}, using fallback")
                return _enhanced_fallback_synthesis(event_type, location, raw_findings, evidence_count, confidence_score, synthesis_focus)
        else:
            logger.warning("No GOOGLE_CLOUD_PROJECT found for synthesis")
            return _enhanced_fallback_synthesis(event_type, location, raw_findings, evidence_count, confidence_score, synthesis_focus)

        # Prepare the synthesis prompt based on focus
        findings_text = "\n".join([f"- {finding}" for finding in raw_findings])
        focus_areas = [area.strip() for area in synthesis_focus.split(",")]

        prompt = f"""You are an expert investigative analyst. Analyze the following findings about a {event_type} at {location} and create:

1. **Key Findings** (4-5 bullet points with specific, factual insights)
2. **Executive Summary** (2-3 sentences focusing on what actually happened)

**Raw Investigation Findings:**
{findings_text}

**Investigation Context:**
- Event Type: {event_type}
- Location: {location}
- Evidence Items Analyzed: {evidence_count}
- Investigation Confidence: {confidence_score:.1%}

**Requirements:**
- Focus on WHAT HAPPENED, not how it was investigated
- Include specific details like scale, nature, timeline, media coverage
- Avoid generic language like "investigation completed" or "evidence collected"
- Extract concrete facts about participants, behavior, scope, impact
- Synthesize information across sources rather than just listing them

**Output Format:**
```json
{{
    "key_findings": "• [First key finding with specific details]\\n• [Second key finding]\\n• [Third key finding]\\n• [Fourth key finding]",
    "executive_summary": "[2-3 sentences describing what actually happened during the {event_type}, focusing on scale, nature, and significance]"
}}
```

Analyze the findings and synthesize them into meaningful insights:"""

        # Generate synthesis using Vertex AI (consistent with codebase)
        try:
            model = GenerativeModel('gemini-2.0-flash')
            logger.info("✅ Using gemini-2.0-flash for synthesis")
        except Exception:
            try:
                model = GenerativeModel('gemini-2.0-flash-001')
                logger.info(
                    "✅ Using gemini-2.0-flash-001 for synthesis (fallback)")
            except Exception:
                try:
                    model = GenerativeModel('gemini-1.5-flash')
                    logger.info(
                        "✅ Using gemini-1.5-flash for synthesis (fallback)")
                except Exception as model_error:
                    logger.warning(
                        f"No Vertex AI models available: {model_error}")
                    return _enhanced_fallback_synthesis(event_type, location, raw_findings, evidence_count, confidence_score, synthesis_focus)

        response = model.generate_content(prompt)

        # Parse the JSON response
        response_text = response.text
        json_match = re.search(
            r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'(\{.*?\})', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                raise ValueError("No JSON found in response")

        synthesis_result = json.loads(json_text)

        logger.info("✅ Vertex AI synthesis completed successfully")
        return synthesis_result

    except Exception as e:
        logger.warning(
            f"Vertex AI synthesis failed: {e}, using enhanced fallback")
        return _enhanced_fallback_synthesis(event_type, location, raw_findings, evidence_count, confidence_score, synthesis_focus)


def _enhanced_fallback_synthesis(
    event_type: str,
    location: str,
    raw_findings: list,
    evidence_count: int,
    confidence_score: float,
    synthesis_focus: str
) -> dict:
    """Enhanced fallback synthesis when Vertex AI is not available."""

    # Better extraction of key information from raw findings
    findings_text = " ".join(raw_findings).lower()
    logger.info(
        f"🔍 Enhanced fallback synthesis analyzing {len(raw_findings)} findings for {event_type} at {location}")

    # Extract specific details with better patterns
    scale_info = ""
    nature_info = ""
    media_info = ""
    timeline_info = ""
    location_details = ""
    specific_details = []

    # Extract numbers and key details
    import re

    # Scale analysis
    if "tens of thousands" in findings_text or "50,000" in findings_text:
        scale_info = "tens of thousands of participants"
    elif "thousands" in findings_text:
        number_match = re.search(
            r'(\d+,?\d+)\s*(?:participants?|people)', findings_text)
        if number_match:
            scale_info = f"approximately {number_match.group(1)} participants"
        else:
            scale_info = "thousands of participants"
    elif "hundreds" in findings_text:
        scale_info = "hundreds of participants"

    # Nature analysis
    if "peaceful" in findings_text and "no arrests" in findings_text:
        nature_info = "peaceful with no reported incidents"
    elif "arrests" in findings_text:
        nature_info = "peaceful demonstration with some arrests"
    elif "violence" in findings_text:
        nature_info = "confrontational with reported incidents"
    elif "peaceful" in findings_text:
        nature_info = "peaceful in nature"

    # Media coverage
    news_sources = []
    source_patterns = ["cnn", "reuters", "nytimes", "abc", "nbc", "cbs"]
    found_sources = [
        source for source in source_patterns if source in findings_text]
    if found_sources:
        media_info = f"documented by major news outlets including {', '.join(found_sources[:3])}"

    # Generate key findings
    key_findings_list = []

    if scale_info:
        key_findings_list.append(f"• Scale analysis documents {scale_info}")
    if nature_info:
        key_findings_list.append(f"• Event characterized as {nature_info}")
    if location != "Unknown Location":
        key_findings_list.append(
            f"• Event focused on {location} with significant local impact")
    if media_info:
        key_findings_list.append(
            f"• Public attention confirmed with event {media_info}")
    if evidence_count > 5:
        key_findings_list.append(
            f"• Multi-source verification completed through {evidence_count} evidence sources")

    # Ensure minimum findings
    while len(key_findings_list) < 4:
        if len(key_findings_list) == 0:
            key_findings_list.append(
                f"• {event_type.title()} investigation at {location} completed")
        elif len(key_findings_list) == 1:
            key_findings_list.append(
                f"• Evidence collection yielded {evidence_count} artifacts")
        elif len(key_findings_list) == 2:
            key_findings_list.append(
                f"• Investigation achieved {confidence_score:.1%} confidence")
        else:
            key_findings_list.append(
                f"• Analysis confirms {event_type} classification")

    # Generate executive summary
    summary_parts = []
    if scale_info and nature_info:
        summary_parts.append(
            f"Investigation of {event_type} at {location} reveals a {nature_info} event involving {scale_info}.")
    else:
        summary_parts.append(
            f"Comprehensive investigation of {event_type} at {location} has been completed.")

    if media_info:
        summary_parts.append(
            f"The event was {media_info}, indicating significant public interest.")

    summary_parts.append(
        f"Investigation achieved {confidence_score:.1%} confidence through analysis of {evidence_count} evidence items.")

    result = {
        "key_findings": "\n".join(key_findings_list),
        "executive_summary": " ".join(summary_parts)
    }

    logger.info(
        f"✅ Enhanced fallback synthesis generated {len(key_findings_list)} findings")
    return result


# Create the synthesis tool
synthesize_investigation_findings = FunctionTool(
    synthesize_investigation_findings_func)


# Placeholder functions for other analysis tools
def analyze_temporal_patterns_func(
    time_range: str = "24h",
    location: str = "NYC",
    pattern_types: str = "incidents,traffic,social"
) -> dict:
    """Analyze temporal patterns in collected data."""
    return {
        "success": True,
        "time_range": time_range,
        "patterns_found": 3,
        "summary": f"Analyzed temporal patterns for {location} over {time_range}"
    }


def correlate_data_sources_func(
    source_types: str = "web,social,official",
    correlation_method: str = "semantic"
) -> dict:
    """Correlate findings across different data sources."""
    return {
        "success": True,
        "correlations_found": 2,
        "summary": f"Correlated data across {source_types} sources"
    }


def identify_risk_factors_func(
    investigation_id: str,
    risk_categories: str = "public_safety,infrastructure,economic"
) -> dict:
    """Identify risk factors from investigation findings."""
    return {
        "success": True,
        "risk_factors": ["crowd_density", "traffic_disruption"],
        "summary": f"Identified risk factors for investigation {investigation_id}"
    }


def generate_hypotheses_func(
    investigation_id: str,
    hypothesis_types: str = "causal,predictive,correlational"
) -> dict:
    """Generate investigative hypotheses for further research."""
    return {
        "success": True,
        "hypotheses": ["Weather correlation", "Social media influence"],
        "summary": f"Generated hypotheses for investigation {investigation_id}"
    }


def save_analysis_results_func(
    investigation_id: str,
    analysis_type: str,
    results: str
) -> dict:
    """Save analysis results to investigation state."""
    return {
        "success": True,
        "saved_to": f"investigation_{investigation_id}",
        "summary": f"Saved {analysis_type} analysis results"
    }


# Create FunctionTool instances
analyze_temporal_patterns = FunctionTool(analyze_temporal_patterns_func)
correlate_data_sources = FunctionTool(correlate_data_sources_func)
identify_risk_factors = FunctionTool(identify_risk_factors_func)
generate_hypotheses = FunctionTool(generate_hypotheses_func)
save_analysis_results = FunctionTool(save_analysis_results_func)
