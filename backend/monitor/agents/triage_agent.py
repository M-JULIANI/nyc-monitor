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

        # Enhanced triage prompt with specific categorization requirements
        prompt = f"""
You are a NYC monitoring triage agent. Analyze these data signals and assign SPECIFIC event types and categories instead of generic "general" classifications.

**Current Time**: {current_time}

**Signal Sources**: {signal_sources_json}

{recent_alerts_snippet}

**Raw Data**: {raw_data_snippet}...

**CRITICAL REQUIREMENT - SPECIFIC CATEGORIZATION**: 
You MUST categorize each alert with specific event types. DO NOT use "general" unless absolutely no other category fits.

**AVAILABLE EVENT TYPES** (choose the most specific one):

**INFRASTRUCTURE**: water_system, power_outage, elevator, gas_leak, plumbing
**EMERGENCY**: fire, medical_emergency, structural_emergency, hazmat  
**TRANSPORTATION**: traffic_incident, transit_disruption, parking_violation, street_closure
**EVENTS**: parade, festival, concert, protest, filming
**SAFETY**: crime, building_safety, public_safety
**ENVIRONMENT**: noise_complaint, air_quality, sanitation, water_quality
**HOUSING**: heat_hot_water, housing_violation

**CATEGORIZATION GUIDELINES**:
1. **Water issues** → "water_system" (hydrants, leaks, water main breaks)
2. **Power/electrical** → "power_outage" 
3. **Building emergencies** → "structural_emergency" or "building_safety"
4. **Traffic/roads** → "traffic_incident" or "street_closure"
5. **Public events** → "parade", "festival", "concert", "protest"
6. **Crime/safety** → "crime", "public_safety"
7. **Noise issues** → "noise_complaint"
8. **Environmental** → "air_quality", "sanitation"
9. **311 emergency types** → match to appropriate emergency category

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
1. **Analyze Actual Content**: Examine the full text, sentiment, and tone across all sources (Reddit posts, Tweets, HackerNews stories, 311 reports, etc.)
2. **Community Reaction**: Note if content shows concern, excitement, avoidance, or participation across different platforms
3. **Information Quality**: Prioritize first-hand accounts and detailed reports over vague references, regardless of source
4. **Urgency Markers**: Look for "happening now", "urgent", "breaking", "just saw", "live from", "currently at" etc.
5. **Tone Analysis**: Consider whether content is informational, questioning, concerned, or angry
6. **Source-Specific Context**:
   - **Reddit**: Community discussions, local neighborhood insights, eyewitness accounts
   - **Twitter**: Real-time updates, breaking news, immediate reactions, official announcements
   - **HackerNews**: Tech community perspective, startup events, infrastructure discussions
   - **311**: Official reports, service requests, infrastructure issues, planned maintenance
   - **Other sources**: Government feeds, emergency services, traffic systems, etc.

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
1. Identify potential alerts, incidents, emergencies, OR major public events affecting NYC residents from ANY SOURCE
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
   - **Cross-source correlations**: Same event/area mentioned across multiple platforms (Reddit + Twitter + 311, etc.)
   - **Infrastructure impacts**: Events affecting traffic, transit, utilities, city services
   - **Seasonal/planned events**: Major NYC events (Pride, marathons, street fairs, holiday events)
   - **Tech/Business events**: From HackerNews - conferences, meetups, startup events in NYC
   - **Official reports**: From 311 - service disruptions, planned maintenance, public notices

4. Event Examples to Capture (WITH SPECIFIC LOCATIONS):
   - **Emergency (High severity)**: "Fire at 123 Main St, Manhattan", "Subway shutdown at Union Square-14th St", "Water main break on Broadway between 42nd-45th St"
   - **Major Events (Medium-High)**: "Pride Parade on 5th Ave from 36th to 8th St", "Marathon closures on Verrazzano Bridge and 4th Ave Brooklyn", "Concert at Central Park Great Lawn"
   - **Local Events (Medium)**: "Street fair on Smith St between Atlantic-Pacific", "Block party on 85th St between 2nd-3rd Ave", "Festival in Prospect Park Bandshell area"
   - **Tech Events (Medium)**: "Tech conference at Javits Center", "Startup demo day at Brooklyn Navy Yard", "Hackathon at Cornell Tech Roosevelt Island"
   - **311 Reports (Variable)**: "Street closure for filming on Park Ave 42nd-45th", "Water service interruption E 14th St between 1st-2nd Ave"

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
  "summary": "Brief overview of current NYC situation including events and emergencies from all monitored sources",
  "alerts": [
    {{
      "id": "example_event_id",
      "title": "Example Event - Specific Location",
      "event_date": "2025-06-01",
      "area": "Specific Area - Street/Venue Description",
      "severity": 8,
      "category": "infrastructure",
      "event_type": "water_system",
      "signals": ["reddit", "twitter", "311"],
      "description": "Detailed description with specific streets, times, and transportation impacts. Cross-referenced across multiple sources.",
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
      "tone_analysis": "informational",
      "source_breakdown": {{
        "reddit": "Community discussion and eyewitness accounts",
        "twitter": "Real-time updates and official announcements", 
        "311": "Official street closure notifications",
        "hackernews": "Tech community event details"
      }}
    }}
  ],
  "duplicates_detected": [
    {{
      "original_alert_id": "2025-06-01_1234_parade_5th_ave",
      "reason": "Same parade route and timing across multiple sources",
      "new_information": "Updated crowd size estimate from Twitter",
      "action": "no_new_alert_needed"
    }}
  ],
  "normal_activity": [
    {{
      "source": "reddit",
      "note": "Normal discussions without significant events"
    }},
    {{
      "source": "twitter", 
      "note": "Regular NYC chatter and routine updates"
    }},
    {{
      "source": "hackernews",
      "note": "Standard tech discussions not NYC-specific"
    }}
  ],
  "rejected_signals": [
    {{
      "reason": "Insufficient location specificity",
      "example": "Event mentioned without specific streets or venues",
      "sources": ["reddit", "twitter"]
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
- Use SPECIFIC event_type from the list above - NO "general" unless absolutely necessary
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
        logger.error(
            "📊 Raw signals from all sources will not be processed into alerts")
        logger.error(f"   Sources affected: {list(raw_signals.keys())}")

        # Get source names for logging (excluding metadata)
        sources = [k for k in raw_signals.keys() if k not in [
            'recent_alerts', 'timestamp', 'collection_window']]
        logger.error(f"   Data sources with unprocessed signals: {sources}")

        # Return empty results - no fake entries
        return {
            'summary': 'Triage analysis failed - no alerts generated from any source',
            'alerts': [],  # Empty - no fake entries
            'normal_activity': [],
            'timestamp': datetime.utcnow().isoformat(),
            'sources_analyzed': sources,
            'action_required': {
                'urgent_investigation': [],
                'user_investigation': [],
                'monitor_only': [],
                'normal_activity': []
            },
            'error': 'AI analysis failed - check logs for details',
            'raw_signals_available': True,  # Data is available for manual review
            'affected_sources': sources
        }
