"""
Lightweight Triage Agent for NYC Monitor System.
Quickly analyzes raw signals from multiple sources and assigns severity scores.
Designed to be fast and cost-effective for 15-minute monitoring cycles.
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger(__name__)


class TriageAgent:
    """Lightweight AI agent for quick severity assessment of NYC signals"""

    def __init__(self, project_id: Optional[str] = None, location: str = "us-central1"):
        """
        Initialize the Triage Agent

        Args:
            project_id: GCP project ID
            location: Vertex AI location/region
        """
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Use fast, lightweight model
        self.model = GenerativeModel("gemini-1.5-flash")

        # Severity thresholds for alerting
        self.severity_thresholds = {
            'urgent_investigation': 8,  # Immediate full investigation
            'user_investigation': 5,   # Queue for user-triggered investigation
            'monitor_only': 3          # Just monitor, no action
        }

    async def analyze_signals(self, raw_signals: Dict) -> Dict:
        """
        Analyze raw signals from multiple sources and assign severity scores

        Args:
            raw_signals: Dictionary containing data from all sources

        Returns:
            Dictionary with alerts and severity scores
        """
        try:
            logger.info("Starting triage analysis of collected signals")

            # Create prompt for AI analysis
            prompt = self._create_triage_prompt(raw_signals)

            # Get AI response
            response = await self.model.generate_content_async(prompt)

            if response and response.text:
                try:
                    # Parse structured response
                    analysis = json.loads(response.text.strip())

                    # Add metadata
                    analysis['timestamp'] = datetime.utcnow().isoformat()
                    analysis['sources_analyzed'] = list(raw_signals.keys())

                    # Categorize alerts by severity
                    analysis['action_required'] = self._categorize_by_severity(
                        analysis.get('alerts', []))

                    logger.info(
                        f"Triage complete: {len(analysis.get('alerts', []))} alerts generated")
                    return analysis

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse triage response: {e}")
                    return self._create_fallback_response(raw_signals)
            else:
                logger.warning("Empty response from triage agent")
                return self._create_fallback_response(raw_signals)

        except Exception as e:
            logger.error(f"Error in triage analysis: {str(e)}")
            return self._create_fallback_response(raw_signals)

    def _create_triage_prompt(self, raw_signals: Dict) -> str:
        """Create the triage analysis prompt"""

        # Count signals for context
        signal_summary = {}
        for source, data in raw_signals.items():
            if isinstance(data, list):
                signal_summary[source] = f"{len(data)} items"
            else:
                signal_summary[source] = "1 dataset"

        prompt = f"""
You are a NYC emergency monitoring triage agent. Analyze these data signals and assign severity scores (1-10).

**Current Time**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

**Signal Sources**: {json.dumps(signal_summary, indent=2)}

**Raw Data**: {json.dumps(raw_signals, indent=2, default=str)[:3000]}...

**Your Task**: 
1. Identify potential alerts, incidents, or anomalies affecting NYC residents
2. Assign severity scores (1-10) where:
   - 9-10: Emergency/breaking news (subway outage, major incident)
   - 7-8: High priority (significant traffic, widespread complaints, safety issues)
   - 5-6: Medium priority (local disruptions, trending concerns)
   - 3-4: Low priority (minor issues, background chatter)
   - 1-2: Normal activity

3. Focus on:
   - Cross-source correlations (same issue mentioned across platforms)
   - Unusual volume spikes
   - Safety/emergency keywords
   - Infrastructure problems (MTA, traffic, utilities)
   - Public health concerns

4. Group related signals by geographical area or theme

**Response Format** (JSON only):
{{
  "summary": "Brief overview of current NYC situation",
  "alerts": [
    {{
      "id": "unique_alert_id",
      "title": "Brief alert title",
      "area": "Geographic area or 'Citywide'",
      "severity": 8,
      "category": "transportation|safety|weather|infrastructure|social",
      "signals": ["reddit", "traffic"],
      "description": "What's happening and why it matters",
      "keywords": ["subway", "delays"],
      "confidence": 0.85
    }}
  ],
  "normal_activity": [
    {{
      "source": "reddit",
      "note": "Normal food/entertainment discussions"
    }}
  ]
}}
"""
        return prompt

    def _categorize_by_severity(self, alerts: List[Dict]) -> Dict:
        """Categorize alerts by required action based on severity"""
        categorized = {
            'urgent_investigation': [],
            'user_investigation': [],
            'monitor_only': [],
            'normal_activity': []
        }

        for alert in alerts:
            severity = alert.get('severity', 0)

            if severity >= self.severity_thresholds['urgent_investigation']:
                categorized['urgent_investigation'].append(alert)
            elif severity >= self.severity_thresholds['user_investigation']:
                categorized['user_investigation'].append(alert)
            elif severity >= self.severity_thresholds['monitor_only']:
                categorized['monitor_only'].append(alert)
            else:
                categorized['normal_activity'].append(alert)

        return categorized

    def _create_fallback_response(self, raw_signals: Dict) -> Dict:
        """Create a fallback response when AI analysis fails"""
        return {
            'summary': 'Triage analysis failed - manual review required',
            'alerts': [{
                'id': f'fallback_{int(datetime.utcnow().timestamp())}',
                'title': 'System Alert: Triage Analysis Failed',
                'area': 'System',
                'severity': 5,
                'category': 'infrastructure',
                'signals': list(raw_signals.keys()),
                'description': 'Automated triage failed. Raw data collected but needs manual review.',
                'keywords': ['system', 'error'],
                'confidence': 1.0
            }],
            'normal_activity': [],
            'timestamp': datetime.utcnow().isoformat(),
            'sources_analyzed': list(raw_signals.keys()),
            'action_required': {
                'urgent_investigation': [],
                'user_investigation': [{'id': f'fallback_{int(datetime.utcnow().timestamp())}'}],
                'monitor_only': [],
                'normal_activity': []
            }
        }
