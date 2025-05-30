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

        # Use current available model (gemini-2.0-flash is the latest stable)
        try:
            self.model = GenerativeModel("gemini-2.0-flash")
            logger.info("✅ Using gemini-2.0-flash model for triage analysis")
        except Exception as e:
            # Fallback to alternative current models
            try:
                self.model = GenerativeModel("gemini-1.5-flash")
                logger.info(
                    "✅ Using gemini-1.5-flash model for triage analysis (fallback)")
            except Exception as e2:
                logger.error(f"❌ Failed to initialize any Vertex AI model:")
                logger.error(f"   gemini-2.0-flash: {e}")
                logger.error(f"   gemini-1.5-flash: {e2}")
                raise Exception(
                    f"No available Vertex AI models. Check project access and model availability.")

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

            # Get AI response (using synchronous method)
            response = self.model.generate_content(prompt)

            if response and response.text:
                try:
                    # Clean the response text to extract JSON
                    response_text = response.text.strip()

                    # Try to extract JSON from the response (sometimes wrapped in markdown)
                    if response_text.startswith('```json'):
                        # Extract JSON from markdown code block
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start != -1 and end > start:
                            response_text = response_text[start:end]
                    elif response_text.startswith('```'):
                        # Extract from generic code block
                        lines = response_text.split('\n')
                        json_lines = []
                        in_json = False
                        for line in lines:
                            if line.strip() == '```':
                                if in_json:
                                    break
                                continue
                            if line.strip().startswith('{') or in_json:
                                in_json = True
                                json_lines.append(line)
                        response_text = '\n'.join(json_lines)

                    # Parse structured response
                    analysis = json.loads(response_text)

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
                    logger.error(f"Raw response: {response.text[:500]}...")
                    return self._create_fallback_response(raw_signals)
                except Exception as e:
                    logger.error(f"Error processing triage response: {e}")
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
You are a NYC monitoring triage agent. Analyze these data signals and assign severity scores (1-10).

**Current Time**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

**Signal Sources**: {json.dumps(signal_summary, indent=2)}

**Raw Data**: {json.dumps(raw_signals, indent=2, default=str)[:3000]}...

**Your Task**: 
1. Identify potential alerts, incidents, emergencies, OR major public events affecting NYC residents
2. Assign severity scores (1-10) where:
   - 9-10: Critical emergencies (major incidents, safety threats, city-wide disruptions)
   - 7-8: High priority (significant events, widespread crowd gatherings, infrastructure issues)
   - 5-6: Medium priority (local events, neighborhood gatherings, trending concerns)
   - 3-4: Low priority (small events, minor issues, background chatter)
   - 1-2: Normal activity

3. Focus on:
   - **Emergency situations**: Accidents, fires, public safety threats, infrastructure failures
   - **Major public events**: Parades, festivals, concerts, protests, large gatherings
   - **Crowd management scenarios**: Events that draw significant crowds affecting city operations
   - **Cross-source correlations**: Same event/area mentioned across platforms
   - **Infrastructure impacts**: Events affecting traffic, transit, utilities, city services
   - **Seasonal/planned events**: Major NYC events (Pride, marathons, street fairs, holiday events)

4. Event Examples to Capture:
   - **Emergency (High severity)**: "Fire in Manhattan", "Subway system failure", "Major accident"
   - **Major Events (Medium-High)**: "Pride Parade route", "Marathon street closures", "Central Park concert"
   - **Local Events (Medium)**: "Street fair in Brooklyn", "Block party permits", "Neighborhood festival"
   - **Routine (Low)**: "Restaurant opening", "Small gathering", "Individual complaints"

5. Group related signals by geographical area or event type

**Response Format** (JSON only):
{{
  "summary": "Brief overview of current NYC situation including events and emergencies",
  "alerts": [
    {{
      "id": "unique_alert_id",
      "title": "Brief alert title",
      "area": "Geographic area or 'Citywide'",
      "severity": 8,
      "category": "emergency|event|transportation|infrastructure|social|safety",
      "event_type": "emergency|parade|festival|concert|protest|sports|seasonal|routine",
      "signals": ["reddit", "traffic"],
      "description": "What's happening, expected crowd size/impact, and why it matters",
      "keywords": ["pride", "parade", "street closure"],
      "confidence": 0.85,
      "crowd_impact": "high|medium|low|none",
      "estimated_attendance": "number or range if applicable"
    }}
  ],
  "normal_activity": [
    {{
      "source": "reddit",
      "note": "Normal discussions without significant events"
    }}
  ]
}}

IMPORTANT: 
- Respond with ONLY valid JSON - no markdown, no explanations, no code blocks
- Start your response with {{ and end with }}
- Do not wrap the JSON in ```json``` or any other formatting
- Ensure all strings are properly quoted and escaped
- Capture BOTH emergencies AND major public events/gatherings
- If no significant alerts are needed, use an empty alerts array: "alerts": []
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
        """Create a fallback response when AI analysis fails - no fake alerts"""
        logger.error("❌ Triage analysis failed - returning empty results")
        logger.error("📊 Raw signals will not be processed into alerts")
        logger.error(f"   Sources affected: {list(raw_signals.keys())}")

        # Return empty results - no fake entries
        return {
            'summary': 'Triage analysis failed - no alerts generated',
            'alerts': [],  # Empty - no fake entries
            'normal_activity': [],
            'timestamp': datetime.utcnow().isoformat(),
            'sources_analyzed': list(raw_signals.keys()),
            'action_required': {
                'urgent_investigation': [],
                'user_investigation': [],
                'monitor_only': [],
                'normal_activity': []
            },
            'error': 'AI analysis failed',
            'raw_signals_available': True  # Data is available for manual review
        }
