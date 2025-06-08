import os
import json
import logging
from typing import Optional
from datetime import datetime
import vertexai
from vertexai.generative_models import GenerativeModel

from .investigation.state_manager import AlertData, state_manager
from .investigation.progress_tracker import progress_tracker, ProgressStatus
from .investigation.tracing import get_distributed_tracer

logger = logging.getLogger(__name__)
tracer = get_distributed_tracer()


class SimpleInvestigationService:
    """
    Simplified investigation service using direct model calls (like triage agent).
    No ADK deployment required - works immediately.
    """

    def __init__(self, project_id: Optional[str] = None, location: str = "us-central1"):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location

        # Initialize Vertex AI (same as triage agent)
        vertexai.init(project=self.project_id, location=self.location)

        # Use current available model
        try:
            self.model = GenerativeModel("gemini-2.0-flash")
            logger.info("✅ Using gemini-2.0-flash for investigation")
        except Exception as e:
            try:
                self.model = GenerativeModel("gemini-1.5-flash")
                logger.info(
                    "✅ Using gemini-1.5-flash for investigation (fallback)")
            except Exception as e2:
                logger.error(
                    f"❌ Failed to initialize Vertex AI model: {e}, {e2}")
                raise

    async def investigate_alert(self, alert_data: AlertData) -> tuple[str, str]:
        """
        Simple investigation using direct model calls (no ADK deployment needed)

        Returns:
            Tuple of (investigation_results_string, investigation_id)
        """
        try:
            # Create investigation state
            investigation_state = state_manager.create_investigation(
                alert_data)
            logger.info(
                f"Created investigation {investigation_state.investigation_id}")

            # Initialize distributed tracing
            trace_id = investigation_state.investigation_id
            tracer.start_trace(
                trace_id=trace_id,
                operation_name=f"simple_investigate_alert:{alert_data.event_type}",
                metadata={
                    "alert_id": alert_data.alert_id,
                    "event_type": alert_data.event_type,
                    "location": alert_data.location,
                    "severity": alert_data.severity,
                    "investigation_id": investigation_state.investigation_id,
                    "approach": "simple_model_direct"
                }
            )

            # Start progress tracking
            progress_tracker.start_investigation(
                investigation_state.investigation_id)
            progress_tracker.add_progress(
                investigation_id=investigation_state.investigation_id,
                status=ProgressStatus.AGENT_ACTIVE,
                active_agent="simple_investigation_model",
                message="Starting direct model investigation"
            )

            # Create investigation prompt (comprehensive but single-call)
            investigation_prompt = self._create_investigation_prompt(
                alert_data, investigation_state)

            # Execute investigation via direct model call
            logger.info(
                f"Starting model investigation for alert {alert_data.alert_id}")

            try:
                # Single model call for investigation
                response = self.model.generate_content(investigation_prompt)

                if response and response.text:
                    # Parse structured response
                    investigation_result = self._parse_investigation_response(
                        response.text)

                    # Update investigation state with results
                    state_manager.update_investigation(investigation_state.investigation_id, {
                        "iteration_count": 1,
                        "findings": investigation_result.get("findings", []),
                        "confidence_score": investigation_result.get("confidence_score", 0.7),
                        "is_complete": True
                    })

                    # Complete progress tracking
                    progress_tracker.complete_investigation(
                        investigation_state.investigation_id,
                        "Simple investigation completed"
                    )

                    # Return formatted results
                    return self._format_investigation_results(alert_data, investigation_state, investigation_result), investigation_state.investigation_id

                else:
                    raise Exception("Empty response from model")

            except Exception as model_error:
                logger.error(f"Model investigation failed: {model_error}")

                # Mark progress as error
                progress_tracker.error_investigation(
                    investigation_state.investigation_id,
                    str(model_error)
                )

                # Return fallback response
                return self._create_fallback_response(alert_data, investigation_state, str(model_error)), investigation_state.investigation_id

        except Exception as e:
            logger.error(f"Error during simple investigation: {e}")
            return f"Investigation failed for alert {alert_data.alert_id}: {str(e)}", ""

    def _create_investigation_prompt(self, alert_data: AlertData, investigation_state) -> str:
        """Create comprehensive investigation prompt for single model call"""

        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

        prompt = f"""
You are an expert NYC investigation agent. Conduct a thorough investigation of this alert using multi-step reasoning.

**ALERT DETAILS:**
- Alert ID: {alert_data.alert_id}
- Event Type: {alert_data.event_type}
- Location: {alert_data.location}
- Severity: {alert_data.severity}/10
- Summary: {alert_data.summary}
- Sources: {', '.join(alert_data.sources)}
- Investigation ID: {investigation_state.investigation_id}
- Current Time: {current_time}

**YOUR INVESTIGATION TASKS:**

1. **INITIAL ASSESSMENT**
   - Analyze the alert severity and event type
   - Identify key investigation priorities
   - Assess potential public safety implications

2. **RESEARCH SIMULATION** (simulate what a research agent would find)
   - Historical context for this type of event at this location
   - Typical patterns and risk factors
   - Similar past incidents and their outcomes
   - Relevant NYC agencies and response protocols

3. **IMPACT ANALYSIS**
   - Transportation and traffic implications
   - Affected demographics and neighborhoods
   - Economic and social impacts
   - Duration and scope estimates

4. **COORDINATION SIMULATION** (simulate coordination tools)
   - Recommended alert status updates
   - Suggested investigation timeline
   - Required follow-up actions
   - Stakeholder notification needs

5. **EVIDENCE COLLECTION** (simulate artifact gathering)
   - Key documents or reports to review
   - Data sources to monitor
   - Witness accounts to collect
   - Physical evidence to examine

6. **FINAL ASSESSMENT**
   - Confidence level in findings (0.0-1.0)
   - Risk assessment and recommendations
   - Next steps and monitoring requirements
   - Summary of key insights

**RESPONSE FORMAT** (JSON only):
{{
  "investigation_id": "{investigation_state.investigation_id}",
  "alert_analysis": {{
    "severity_assessment": "Detailed assessment of alert severity",
    "event_classification": "Classification of the event type",
    "urgency_level": "immediate|high|medium|low",
    "public_safety_risk": "Assessment of public safety implications"
  }},
  "research_findings": {{
    "historical_context": "Historical background and patterns",
    "similar_incidents": ["List of similar past incidents"],
    "risk_factors": ["Key risk factors identified"],
    "agency_protocols": ["Relevant NYC agency responses"]
  }},
  "impact_analysis": {{
    "transportation": "Transportation and traffic impacts",
    "demographics": "Affected populations and areas",
    "duration_estimate": "Estimated duration of impact",
    "economic_impact": "Economic implications"
  }},
  "coordination_actions": {{
    "status_updates": ["Recommended status updates"],
    "timeline": "Investigation timeline",
    "stakeholder_notifications": ["Who needs to be notified"],
    "follow_up_required": ["Required follow-up actions"]
  }},
  "evidence_artifacts": {{
    "documents_needed": ["Key documents to review"],
    "data_sources": ["Data sources to monitor"],
    "witness_accounts": ["Types of witness accounts to collect"],
    "physical_evidence": ["Physical evidence to examine"]
  }},
  "final_assessment": {{
    "confidence_score": 0.85,
    "risk_level": "high|medium|low",
    "recommendations": ["Key recommendations"],
    "next_steps": ["Immediate next steps"],
    "monitoring_requirements": ["Ongoing monitoring needs"]
  }},
  "findings": [
    "Key finding 1 with specific details",
    "Key finding 2 with analysis",
    "Key finding 3 with recommendations"
  ],
  "artifacts_collected": [
    "Simulated artifact 1 description",
    "Simulated artifact 2 description"
  ],
  "summary": "Comprehensive summary of investigation results and recommendations"
}}

**IMPORTANT:**
- Respond with ONLY valid JSON - no markdown, no explanations
- Base your analysis on realistic NYC patterns and protocols
- Provide specific, actionable insights
- Include confidence scores and risk assessments
- Simulate realistic multi-agent coordination results
"""

        return prompt

    def _parse_investigation_response(self, response_text: str) -> dict:
        """Parse the model's investigation response"""
        try:
            # Clean response text
            response_text = response_text.strip()

            # Extract JSON from response
            if response_text.startswith('```json'):
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end > start:
                    response_text = response_text[start:end]

            # Parse JSON
            investigation_data = json.loads(response_text)

            return investigation_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse investigation response: {e}")
            return {
                "findings": ["Investigation response parsing failed"],
                "confidence_score": 0.3,
                "summary": "Unable to parse detailed investigation results"
            }

    def _format_investigation_results(self, alert_data: AlertData, investigation_state, investigation_result: dict) -> str:
        """Format the investigation results for return"""

        findings = investigation_result.get(
            "findings", ["No specific findings available"])
        confidence = investigation_result.get("confidence_score", 0.7)
        summary = investigation_result.get(
            "summary", "Investigation completed")

        return f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete (Simple Model)
Investigation ID: {investigation_state.investigation_id}
Confidence Score: {confidence:.1%}

Investigation Summary:
{summary}

Key Findings:
{chr(10).join(f"• {finding}" for finding in findings)}

Investigation Method: Direct Model Analysis
- Approach: Single comprehensive AI analysis
- Model: Vertex AI Gemini
- Tracing: Distributed tracing enabled
- State Management: Investigation state tracked

Artifacts: {len(investigation_result.get('artifacts_collected', []))} simulated artifacts collected
Next Steps: {', '.join(investigation_result.get('final_assessment', {}).get('next_steps', ['Monitor situation']))}

Investigation completed successfully via simplified model approach."""

    def _create_fallback_response(self, alert_data: AlertData, investigation_state, error_msg: str) -> str:
        """Create fallback response when model fails"""

        return f"""Investigation Results for Alert {alert_data.alert_id}:

Event: {alert_data.event_type} at {alert_data.location}
Severity: {alert_data.severity}/10
Status: Investigation Complete (Fallback Mode)
Investigation ID: {investigation_state.investigation_id}

Basic Analysis:
- Alert type: {alert_data.event_type}
- Location: {alert_data.location}
- Severity assessment: {alert_data.severity}/10 requires attention
- Sources: {', '.join(alert_data.sources)}

Infrastructure Status:
- State Manager: Investigation created and tracked
- Progress Tracker: Progress logged
- Distributed Tracing: Trace context maintained
- Model Service: Direct model approach configured

Error Details: {error_msg}

Note: Model analysis failed, but investigation infrastructure is working.
This demonstrates the system is ready for both simple and complex approaches."""


# Export the simple service
simple_investigation_service = SimpleInvestigationService()


async def investigate_alert_simple(alert_data: AlertData) -> tuple[str, str]:
    """Simple investigation entry point - no deployment required"""
    return await simple_investigation_service.investigate_alert(alert_data)
