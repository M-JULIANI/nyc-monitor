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
        recent_alerts_summary = []

        for source, data in raw_signals.items():
            if source == 'recent_alerts':
                # Handle recent alerts for duplicate detection
                recent_alerts_summary = data if isinstance(data, list) else []
                continue
            elif isinstance(data, list):
                signal_summary[source] = f"{len(data)} items"
            else:
                signal_summary[source] = "1 dataset"

        # Create the raw data snippet (excluding recent alerts from main data)
        signals_for_analysis = {k: v for k, v in raw_signals.items(
        ) if k not in ['recent_alerts', 'timestamp', 'collection_window']}
        raw_data_snippet = json.dumps(
            signals_for_analysis, indent=2, default=str)[:4000]
        signal_sources_json = json.dumps(signal_summary, indent=2)
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

        # Recent alerts summary for duplicate detection
        recent_alerts_snippet = ""
        if recent_alerts_summary:
            recent_alerts_snippet = f"""
**RECENT ALERTS (for duplicate detection)**:
{json.dumps([{
    'title': alert.get('title', ''),
    'event_type': alert.get('event_type', ''),
    'area': alert.get('area', ''),
    'specific_streets': alert.get('specific_streets', []),
    'venue_address': alert.get('venue_address', ''),
    'event_date': alert.get('event_date', ''),
    'created_at': alert.get('created_at', ''),
    'document_id': alert.get('document_id', '')
} for alert in recent_alerts_summary[:10]], indent=2, default=str)}
"""

        prompt = f"""
You are a NYC monitoring triage agent. Analyze these data signals and assign severity scores (1-10).

**Current Time**: {current_time}

**Signal Sources**: {signal_sources_json}

{recent_alerts_snippet}

**Raw Data**: {raw_data_snippet}...

**DUPLICATE DETECTION REQUIREMENTS**:
1. **Check Recent Alerts**: Before creating new alerts, compare against recent alerts from the last 6 hours
2. **Same Event Criteria**: Consider events duplicates if they share:
   - Same or overlapping specific streets/intersections
   - Same venue or landmark
   - Same event type (parade, concert, emergency, etc.) 
   - Same or adjacent time period (within 6 hours)
3. **New Information Assessment**: Create a new alert ONLY if:
   - Significant new details (route changes, time updates, new safety concerns)
   - Different perspective or community reaction
   - Escalation in severity or scope
   - First-hand witness accounts vs. second-hand reports
4. **Update vs. New Alert**: If it's the same event with minor updates, mark it as "duplicate_of" and include the original alert's document_id

**CONTENT AND SENTIMENT ANALYSIS**:
1. **Analyze Actual Content**: Examine the full text, sentiment, and tone of Reddit posts
2. **Community Reaction**: Note if posts show concern, excitement, avoidance, or participation
3. **Information Quality**: Prioritize first-hand accounts and detailed reports over vague references
4. **Urgency Markers**: Look for "happening now", "urgent", "breaking", "just saw" etc.
5. **Tone Analysis**: Consider whether posts are informational, questioning, concerned, or angry

**CRITICAL REQUIREMENT - LOCATION SPECIFICITY**: 
Only create alerts if you can identify SPECIFIC locations with actionable geographic detail:
- Specific street names, intersections, or addresses
- Named venues, parks, or landmarks  
- Specific subway stations or transportation hubs
- Precise neighborhood boundaries with street references
- Exact venues (Madison Square Garden, Central Park Sheep Meadow, etc.)

**DO NOT create alerts for**:
- Vague references like "affected areas", "throughout the city", "various locations"
- General borough mentions without specific areas
- Events without clear geographic boundaries
- Broad descriptions like "downtown" or "uptown" without street references

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

4. Event Examples to Capture (WITH SPECIFIC LOCATIONS):
   - **Emergency (High severity)**: "Fire at 123 Main St, Manhattan", "Subway shutdown at Union Square-14th St", "Water main break on Broadway between 42nd-45th St"
   - **Major Events (Medium-High)**: "Pride Parade on 5th Ave from 36th to 8th St", "Marathon closures on Verrazzano Bridge and 4th Ave Brooklyn", "Concert at Central Park Great Lawn"
   - **Local Events (Medium)**: "Street fair on Smith St between Atlantic-Pacific", "Block party on 85th St between 2nd-3rd Ave", "Festival in Prospect Park Bandshell area"

5. For alert titles, use descriptive event names WITHOUT date prefixes:
   - Example: "Pride Parade - 5th Ave (36th to 8th St)"
   - Example: "Water Main Break - Broadway/42nd St" 
   - Example: "Concert - Central Park Great Lawn"

6. For event dates, include as a separate field in YYYY-MM-DD format

7. For descriptions, include:
   - Specific streets, cross-streets, or landmarks affected
   - Estimated crowd size and duration
   - Transportation/traffic impacts with specific routes
   - Recommended alternate routes when applicable

**Response Format** (JSON only):
{{
  "summary": "Brief overview of current NYC situation including events and emergencies",
  "alerts": [
    {{
      "id": "example_event_id",
      "title": "Example Event - Specific Location",
      "event_date": "2025-06-01",
      "area": "Specific Area - Street/Venue Description",
      "severity": 8,
      "category": "event",
      "event_type": "parade",
      "signals": ["reddit"],
      "description": "Detailed description with specific streets, times, and transportation impacts.",
      "keywords": ["example", "keywords"],
      "confidence": 0.85,
      "crowd_impact": "high",
      "estimated_attendance": "50000-100000",
      "specific_streets": ["Main Street", "First Avenue"],
      "cross_streets": ["1st St", "2nd St", "3rd St"],
      "transportation_impact": "Street closures and alternative routes",
      "venue_address": "Specific address or area description",
      "coordinates": {{"lat": 40.7505, "lng": -73.9858}},
      "is_duplicate": false,
      "duplicate_of": null,
      "duplicate_reason": null,
      "new_information": null,
      "community_sentiment": "concerned",
      "information_quality": "first-hand",
      "urgency_markers": ["happening now", "urgent"],
      "tone_analysis": "informational"
    }}
  ],
  "duplicates_detected": [
    {{
      "original_alert_id": "2025-06-01_1234_parade_5th_ave",
      "reason": "Same parade route and timing",
      "new_information": "Updated crowd size estimate",
      "action": "no_new_alert_needed"
    }}
  ],
  "normal_activity": [
    {{
      "source": "reddit",
      "note": "Normal discussions without significant events"
    }}
  ],
  "rejected_signals": [
    {{
      "reason": "Insufficient location specificity",
      "example": "Event mentioned without specific streets or venues"
    }}
  ]
}}

IMPORTANT: 
- Respond with ONLY valid JSON - no markdown, no explanations, no code blocks
- Start your response with '{{' and end with '}}'
- Do not wrap the JSON in ```json``` or any other formatting
- Ensure all strings are properly quoted and escaped
- ONLY create alerts with specific, actionable location information
- Include "specific_streets", "cross_streets", "venue_address", and "coordinates" fields when possible
- Use descriptive titles WITHOUT date prefixes - dates go in separate "event_date" field
- If no locationally-specific alerts can be created, use an empty alerts array: "alerts": []
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
