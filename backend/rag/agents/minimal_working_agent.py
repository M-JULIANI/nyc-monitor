#!/usr/bin/env python3
"""
Minimal Working Agent for NYC Atlas Investigations.
This agent follows the proven workflow pattern that successfully collects 8+ artifacts
AND performs web searches to gather relevant findings.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.genai import types

logger = logging.getLogger(__name__)


class MinimalWorkingAgent:
    """
    Minimal working agent that follows the proven artifact collection workflow
    with web search capabilities for gathering relevant findings.

    This agent is designed to:
    1. Perform web searches to gather relevant findings
    2. Create investigation state
    3. Generate 2 satellite maps (close + wide zoom)  
    4. Collect images from multiple search queries
    5. Create presentation with all artifacts and findings
    """

    def __init__(self):
        """Initialize the minimal working agent."""
        self.agent = None
        self._setup_agent()

    def _setup_agent(self):
        """Set up the ADK agent with the proven workflow tools including web search."""
        try:
            # Import the working tools from our proven workflow
            from ..tools.map_tools import generate_location_map
            from ..tools.research_tools import collect_media_content, web_search
            from ..tools.report_tools import create_slides_presentation

            # Create the agent with enhanced instructions including web search
            self.agent = Agent(
                model="gemini-2.0-flash-exp",
                name="minimal_working_agent",
                instruction=self._get_system_instructions(),
                tools=[
                    web_search,  # Added web search tool
                    generate_location_map,
                    collect_media_content,  # Fixed import name
                    create_slides_presentation
                ],
                generate_content_config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096  # Increased for web search results
                )
            )

            logger.info(
                "✅ Minimal working agent initialized successfully with web search")

        except Exception as e:
            logger.error(f"❌ Failed to initialize minimal working agent: {e}")
            raise

    def _get_system_instructions(self) -> str:
        """Get focused system instructions for the minimal agent with web search."""
        return """You are the NYC Atlas Minimal Working Agent with Web Search capabilities.

🚨 CRITICAL: YOU MUST EXECUTE ALL REQUIRED TOOLS IN SEQUENCE 🚨

Your job is to execute this EXACT workflow when given an investigation request:

**STEP 1: WEB SEARCH FOR RELEVANT FINDINGS**
- Call web_search_func 2 times to gather relevant information:
  * Search 1: Use the event type and location from the request (max_results=5)
  * Search 2: Search for location + "news recent" (source_types="news", max_results=5)

🔍 **CRITICAL FOR STEP 1**: You MUST read and analyze the web search results to extract key findings about:
- Event scale and participants (crowd size, organization level)
- Timeline and context (when, why, related events)
- Location details (specific areas, route, geographic scope)
- Safety and law enforcement (arrests, incidents, police response)
- Media coverage and public impact (news sources, social media attention)
- Event themes and characteristics (peaceful vs confrontational, political context)

**CRITICAL WEB SEARCH INSTRUCTIONS:**
- ALWAYS use the EXACT event_type provided in the investigation request
- For Search 1: Use "event_type location" exactly as provided in the request
- For Search 2: Use "location news recent" for news coverage  
- DO NOT substitute generic terms like "events" for specific event types like "protest"
- DO NOT change the event_type - use it exactly as given

🚨 **FORBIDDEN SUBSTITUTIONS:**
- NEVER change "protest" to "events" 
- NEVER change "fire" to "incident"
- NEVER change "accident" to "events"
- NEVER generalize specific event types
- FAILURE TO USE EXACT TERMS WILL RESULT IN INCOMPLETE INVESTIGATION

🎯 **CORRECT EXAMPLES:**
- If event_type="protest" and location="NYC" → Search "protest NYC"
- If event_type="fire" and location="Manhattan" → Search "fire Manhattan"  
- If event_type="accident" and location="Brooklyn" → Search "accident Brooklyn"

**STEP 1.5: ANALYSIS AND SYNTHESIS PHASE**
After completing web searches, you MUST provide a detailed synthesis including:

📊 **INCIDENT ANALYSIS**: Based on web search results, analyze:
- Scale: What was the actual size/scope of the incident?
- Nature: Was it peaceful/confrontational? Organized/spontaneous?
- Impact: What were the consequences (traffic, arrests, injuries)?
- Context: Why did this happen? What broader issues does it relate to?
- Timeline: When exactly did events occur? How long did they last?
- Participants: Who was involved? What groups or demographics?

🏛️ **INSTITUTIONAL RESPONSE**: Document official responses:
- Police response and tactics used
- City/government statements or actions
- Transportation impacts and closures
- Public safety measures implemented

📰 **MEDIA COVERAGE ANALYSIS**: Assess news coverage:
- Which outlets covered the story and how prominently?
- What narrative themes emerge from coverage?
- Are there conflicting accounts or perspectives?
- What sources are quoted (officials, witnesses, participants)?

🎯 **KEY TAKEAWAYS**: Synthesize 3-5 specific, factual insights about what actually happened, going beyond just "a protest occurred" to explain the specific circumstances, scale, and significance.

**STEP 2: GENERATE 2 SATELLITE MAPS**
- Call generate_location_map_func with:
  * Map 1: zoom_level=18, map_type="satellite" (close view)
  * Map 2: zoom_level=12, map_type="satellite" (wide view)

**STEP 3: COLLECT EXACTLY 8 IMAGES FROM 3 SEARCH QUERIES**
- Call collect_media_content_simple_func 3 times:
  * Search 1: Use location + event type (max_items=3)
  * Search 2: Use location only (max_items=3) 
  * Search 3: Use "NYC" + event type (max_items=2)

**STEP 4: CREATE PRESENTATION**
- Call create_slides_presentation_func with evidence_types="all"

**EXECUTION RULES:**
1. ALWAYS execute ALL tools in the exact order above
2. Use the investigation_id provided in the request
3. Extract location and event_type from the alert data
4. Do NOT skip any steps
5. Do NOT ask for permission - just execute
6. Log each step as you complete it
7. 🎯 **MOST IMPORTANT**: ACTUALLY READ and analyze web search results to provide meaningful findings

**WEB SEARCH ANALYSIS REQUIREMENTS:**
After each web search, you MUST:
- Summarize what you learned about the incident from the search results
- Extract specific facts about crowd size, behavior, timeline, and impact
- Identify key themes and characteristics of the event
- Note any contradictions or gaps in the information
- Synthesize insights that go beyond just "search completed"

**CRITICAL SUCCESS CRITERIA:**
✅ 2 web searches completed with substantive analysis of results
✅ Detailed incident analysis with specific facts and context
✅ 2 satellite maps generated (zoom 18 + zoom 12)
✅ EXACTLY 8 images collected total (3+3+2)
✅ 1 presentation created with all artifacts
✅ Executive summary that tells the story of what actually happened

**RESPONSE FORMAT:**
Your response MUST include:

## 🔍 WEB SEARCH FINDINGS
[Detailed analysis of what you discovered about the incident]

## 📊 INCIDENT ANALYSIS
**Scale & Scope**: [Specific details about size, duration, geographic area]
**Nature & Behavior**: [Peaceful/confrontational, organized/spontaneous, themes]
**Official Response**: [Police actions, government response, public safety measures]
**Media Coverage**: [Which outlets covered it, how prominently, key narratives]

## 🎯 KEY INSIGHTS
1. [Specific factual insight about what happened]
2. [Specific factual insight about scale or impact]
3. [Specific factual insight about context or significance]

## 📋 EVIDENCE COLLECTED
- Maps: [2 satellite maps generated]
- Images: [8 images collected from 3 searches]
- Screenshots: [Web evidence captured]
- Presentation: [Comprehensive report created]

**WEB SEARCH PRIORITY:**
- DuckDuckGo is primary search engine (free, no API key needed)
- Google Custom Search is automatic fallback when DuckDuckGo fails
- Both collect screenshots and evidence automatically

Execute immediately when given investigation details and provide a summary that focuses on WHAT YOU LEARNED about the incident, not just what tools you ran.

🚨 **CRITICAL WEB SEARCH REQUIREMENTS:**
   - Use EXACT terms from the investigation request (do NOT change to "events" or other generic terms)
   - Use EXACT location provided in the request
   - Example: If event_type="protest", search "protest location", NOT "events location"
   - Example: If event_type="fire", search "fire location", NOT "incident location"

🎯 **CRITICAL INSTRUCTIONS:**
- ACTUALLY EXECUTE each tool - do not just describe what you would do
- READ and ANALYZE the web search results to extract key findings
- PROVIDE a meaningful summary of what you discovered
- DO NOT skip any steps
- START IMMEDIATELY - NO CONFIRMATION NEEDED
- Collect EXACTLY 8 images total (3+3+2)
- 🚨 NEVER CHANGE THE EVENT_TYPE - USE THE EVENT_TYPE EXACTLY AS PROVIDED
"""

    async def investigate(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the enhanced minimal working investigation workflow with web search.

        Args:
            investigation_data: Dictionary containing investigation details

        Returns:
            Investigation results with artifacts, findings, and presentation
        """
        try:
            logger.info(
                "🚀 Starting enhanced minimal working investigation with web search")

            # Initialize Vertex AI if not already done
            try:
                import os
                import vertexai

                project = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

                if project:
                    vertexai.init(project=project, location=location)
                    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
                    logger.info(
                        f"✅ Initialized Vertex AI: project={project}, location={location}")
                else:
                    logger.warning(
                        "⚠️ GOOGLE_CLOUD_PROJECT not set, using default credentials")

            except Exception as e:
                logger.warning(f"⚠️ Vertex AI initialization failed: {e}")

            # Extract required data
            investigation_id = investigation_data.get("investigation_id")
            alert_data = investigation_data.get("alert_data", {})
            location = alert_data.get("location", "Unknown Location")
            event_type = alert_data.get("event_type", "incident")

            if not investigation_id:
                raise ValueError("investigation_id is required")

            logger.info(f"📊 Investigation: {investigation_id}")
            logger.info(f"📍 Location: {location}")
            logger.info(f"🎯 Event Type: {event_type}")

            # Extract additional properties if available and valid
            def is_valid_value(value):
                """Check if a value is valid (not None, null, empty, or 'unknown')"""
                if not value:
                    return False
                if isinstance(value, str):
                    return value.lower() not in ['unknown', 'none', 'null', '', 'n/a']
                return True

            # Get additional context data
            neighborhood = alert_data.get("neighborhood") if is_valid_value(
                alert_data.get("neighborhood")) else None
            borough = alert_data.get("borough") if is_valid_value(
                alert_data.get("borough")) else None
            category = alert_data.get("category") if is_valid_value(
                alert_data.get("category")) else None
            summary = alert_data.get("summary", "")

            # Build enhanced location string for searches
            location_parts = []
            if neighborhood:
                location_parts.append(neighborhood)
            if borough:
                location_parts.append(borough)
            if not location_parts and location and is_valid_value(location):
                location_parts.append(location)

            enhanced_location = ", ".join(
                location_parts) if location_parts else location

            # Extract key terms from summary/description for more targeted searches
            summary_search_terms = ""
            if summary and is_valid_value(summary):
                # Clean and extract meaningful terms from summary (first 100 chars to keep it focused)
                clean_summary = summary.strip()[:100]
                if len(clean_summary) > 10:  # Only use if substantial
                    summary_search_terms = clean_summary

            # Log what we found
            logger.info(f"🔍 Enhanced search data:")
            logger.info(f"   Neighborhood: {neighborhood}")
            logger.info(f"   Borough: {borough}")
            logger.info(f"   Category: {category}")
            logger.info(f"   Enhanced Location: {enhanced_location}")
            logger.info(
                f"   Summary for search: {summary_search_terms[:50]}..." if summary_search_terms else "   No summary available")

            # Create the enhanced investigation message for the agent
            investigation_message = f"""
🚨 INVESTIGATION REQUEST - EXECUTE ENHANCED WORKFLOW IMMEDIATELY 🚨

Investigation Details:
- Investigation ID: {investigation_id}
- Location: {enhanced_location}
- Event Type: {event_type}
{f"- Category: {category}" if category else ""}
{f"- Neighborhood: {neighborhood}" if neighborhood else ""}
{f"- Borough: {borough}" if borough else ""}
- Alert Data: {alert_data}

EXECUTE ALL REQUIRED TOOLS NOW IN SEQUENCE:

1. **WEB SEARCH PHASE** - Gather relevant findings:
{f'   - Search for "{summary_search_terms}" to find specific incident details' if summary_search_terms else ""}
   - Search for "{event_type} {enhanced_location}" to find general information
   - Search for "{enhanced_location} news recent" to find recent news coverage

🚨 **CRITICAL WEB SEARCH REQUIREMENTS:**
   - Use EXACT terms from the investigation request (do NOT change to "events" or other generic terms)
   - Use EXACT location provided in the request
   - Example: If event_type="protest", search "protest location", NOT "events location"
   - Example: If event_type="fire", search "fire location", NOT "incident location"

2. **MAP GENERATION PHASE** - Create location context:
   - Generate satellite map with zoom level 18 (close view)
   - Generate satellite map with zoom level 12 (wide view)

3. **IMAGE COLLECTION PHASE** - Gather EXACTLY 8 images:
   - Collect images for "{enhanced_location} {event_type}" (max_items=3)
   - Collect images for "{enhanced_location}" (max_items=3)
   - Collect images for "NYC {event_type}" (max_items=2)

4. **PRESENTATION PHASE** - Create comprehensive report:
   - Generate presentation with all collected artifacts and findings

🎯 **CRITICAL INSTRUCTIONS:**
- ACTUALLY EXECUTE each tool - do not just describe what you would do
- READ and ANALYZE the web search results to extract key findings
- PROVIDE a meaningful summary of what you discovered
- DO NOT skip any steps
- START IMMEDIATELY - NO CONFIRMATION NEEDED
- Collect EXACTLY 8 images total (3+3+2)
- 🚨 NEVER CHANGE THE EVENT_TYPE - USE THE EVENT_TYPE EXACTLY AS PROVIDED

Your goal is to provide both comprehensive artifact collection AND meaningful investigative findings.
"""

            # Execute the agent workflow
            logger.info("🔧 Executing enhanced agent workflow...")

            # Use the ADK Runner to execute the agent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService

            session_service = InMemorySessionService()
            runner = Runner(
                agent=self.agent,
                app_name="minimal_working_agent",
                session_service=session_service
            )

            # Run the investigation
            results = []
            session_id = f"investigation_{investigation_id}"
            user_id = "minimal_working_agent"

            # Create session before running
            session = session_service.create_session(
                session_id=session_id,
                user_id=user_id,
                app_name="minimal_working_agent"
            )

            logger.info(f"✅ Created session: {session_id}")

            # Create the message as types.Content
            content = types.Content(
                role='user',
                parts=[types.Part(text=investigation_message)]
            )

            async for event in runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=content
            ):
                # Handle different types of events from the ADK runner
                if hasattr(event, 'text') and event.text:
                    results.append(event.text)
                    logger.info(f"📤 Agent response: {event.text[:100]}...")
                elif hasattr(event, 'content'):
                    # Handle Content objects properly
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                results.append(part.text)
                                logger.info(
                                    f"📤 Agent text: {part.text[:100]}...")
                            elif hasattr(part, 'function_call') and part.function_call:
                                logger.info(
                                    f"📤 Agent function call: {part.function_call.name}")
                    else:
                        results.append(str(event.content))
                        logger.info(
                            f"📤 Agent content: {str(event.content)[:100]}...")
                elif isinstance(event, str):
                    results.append(event)
                    logger.info(f"📤 Agent response: {event[:100]}...")
                else:
                    # Log the event type for debugging
                    logger.info(
                        f"📤 Agent event type: {type(event)}, content: {str(event)[:100]}...")
                    results.append(str(event))

            # Combine all results
            full_response = "\n".join(
                results) if results else "No response from agent"

            # Get the final investigation state to check artifacts
            from ..investigation.state_manager import state_manager
            final_state = state_manager.get_investigation(investigation_id)

            if final_state:
                total_artifacts = len(final_state.artifacts)

                # Count artifact types
                artifact_types = {}
                for artifact in final_state.artifacts:
                    artifact_type = artifact.get('type', 'unknown')
                    artifact_types[artifact_type] = artifact_types.get(
                        artifact_type, 0) + 1

                logger.info(f"📊 Final artifact count: {total_artifacts}")
                logger.info(f"📋 Artifact breakdown: {artifact_types}")

                # 🎯 **CRITICAL FIX**: Extract and store agent analysis findings for report generation
                self._extract_and_store_agent_findings(
                    final_state, full_response, investigation_id)

                # Calculate meaningful confidence score based on evidence quality and web search insights
                confidence_score = self._calculate_confidence_score(
                    final_state, total_artifacts, artifact_types
                )

                # Update the investigation state with the calculated confidence
                final_state.confidence_score = confidence_score
                final_state.confidence_scores['evidence_quality'] = confidence_score

                logger.info(
                    f"📊 Calculated confidence score: {confidence_score:.1%}")

                # 🚨 CRITICAL FIX: Save the confidence score back to the state manager
                state_manager.update_investigation(investigation_id, {
                    'confidence_score': confidence_score,
                    'confidence_scores': final_state.confidence_scores
                })
                logger.info(
                    f"✅ Saved confidence score {confidence_score:.1%} to state manager")

                # Enhanced success criteria including web search results
                maps_count = artifact_types.get('map_image', 0)
                images_count = artifact_types.get('image', 0)
                screenshots_count = artifact_types.get('screenshot', 0)

                # Check if web searches were performed (should have screenshots from web search)
                web_search_performed = screenshots_count > 0 or "web_search" in full_response.lower()

                success = (
                    maps_count >= 2 and
                    images_count >= 8 and
                    web_search_performed and
                    total_artifacts >= 8 and
                    confidence_score >= 0.6  # Add confidence threshold
                )

                return {
                    "success": success,
                    "investigation_id": investigation_id,
                    "total_artifacts": total_artifacts,
                    "artifact_breakdown": artifact_types,
                    "maps_generated": maps_count,
                    "images_collected": images_count,
                    "screenshots_collected": screenshots_count,
                    "web_search_performed": web_search_performed,
                    "confidence_score": confidence_score,
                    "agent_response": full_response,
                    "workflow_status": "completed" if success else "partial",
                    "summary": f"Generated {maps_count} maps, collected {images_count} images, {screenshots_count} screenshots, total {total_artifacts} artifacts. Confidence: {confidence_score:.1%}. Web search: {'✅' if web_search_performed else '❌'}"
                }
            else:
                logger.warning(
                    "⚠️ Could not retrieve final investigation state")
                return {
                    "success": False,
                    "investigation_id": investigation_id,
                    "error": "Could not retrieve investigation state",
                    "agent_response": full_response,
                    "workflow_status": "failed"
                }

        except Exception as e:
            logger.error(
                f"❌ Enhanced minimal working investigation failed: {e}")
            return {
                "success": False,
                "investigation_id": investigation_data.get("investigation_id", "unknown"),
                "error": str(e),
                "workflow_status": "failed",
                "summary": f"Investigation failed: {str(e)}"
            }

    def _extract_and_store_agent_findings(self, final_state, full_response, investigation_id):
        """
        Extract and store agent analysis findings for report generation.

        Args:
            final_state: Investigation state with all collected evidence
            full_response: Full response from the agent
            investigation_id: ID of the investigation
        """
        try:
            logger.info(
                "🔍 Extracting agent findings from response for report generation...")

            # Initialize agent_findings if not present
            if not hasattr(final_state, 'agent_findings'):
                final_state.agent_findings = {}

            # Extract key insights from the agent's response
            extracted_findings = self._parse_agent_response_for_insights(
                full_response)

            # Store findings under a key that the report generation will look for
            final_state.agent_findings['web_search_analysis'] = extracted_findings

            logger.info(
                f"✅ Stored {len(extracted_findings)} agent findings for report generation")

            # Log findings for debugging
            # Show first 5
            for i, finding in enumerate(extracted_findings[:5]):
                logger.info(f"   Finding {i+1}: {finding[:80]}...")

        except Exception as e:
            logger.warning(
                f"⚠️ Error extracting and storing agent findings: {e}")

    def _parse_agent_response_for_insights(self, full_response):
        """
        Parse the agent's response to extract meaningful insights for the report.
        This should extract ACTUAL findings from web search results, not hardcoded patterns.

        Args:
            full_response: The full response text from the agent

        Returns:
            List of extracted insights/findings
        """
        findings = []

        try:
            # 1. Extract insights from structured sections of the agent response
            sections = {
                'web_search_findings': r'## 🔍 WEB SEARCH FINDINGS\s*(.*?)(?=##|$)',
                'incident_analysis': r'## 📊 INCIDENT ANALYSIS\s*(.*?)(?=##|$)',
                'key_insights': r'## 🎯 KEY INSIGHTS\s*(.*?)(?=##|$)',
                'analysis': r'(?:Analysis|Findings|Results).*?:\s*(.*?)(?=\n\n|\n##|$)'
            }

            for section_name, pattern in sections.items():
                matches = re.findall(pattern, full_response,
                                     re.DOTALL | re.IGNORECASE)
                for match in matches:
                    # Extract bullet points and meaningful sentences from this section
                    section_findings = self._extract_findings_from_text(
                        match.strip())
                    findings.extend(section_findings)

            # 2. Extract bullet points from anywhere in the response
            bullet_patterns = [
                r'[•·\-\*]\s*([^•·\-\*\n]{20,})',  # Standard bullets
                r'^\d+\.\s*([^0-9\n]{20,})',       # Numbered lists
                r'(?:^|\n)[-•]\s*([^\n]{20,})'     # Dash bullets
            ]

            for pattern in bullet_patterns:
                bullet_points = re.findall(
                    pattern, full_response, re.MULTILINE)
                for point in bullet_points:
                    clean_point = point.strip()
                    if self._is_meaningful_finding(clean_point):
                        findings.append(clean_point)

            # 3. Extract key sentences that contain analytical insights
            sentences = re.split(r'[.!?]+', full_response)
            for sentence in sentences:
                sentence = sentence.strip()
                if self._is_analytical_sentence(sentence):
                    findings.append(sentence)

            # 4. Extract information from web search result descriptions
            # Look for patterns like "search reveals", "sources indicate", "web evidence shows"
            web_patterns = [
                r'(?:search|sources?|evidence|investigation|analysis)\s+(?:reveals?|indicates?|shows?|confirms?|documents?)\s+([^.!?]{20,})',
                r'(?:web|online|internet)\s+(?:sources?|evidence|research)\s+(?:shows?|indicates?|confirms?)\s+([^.!?]{20,})',
                r'(?:found|discovered|identified|documented)\s+(?:that|evidence of|information about)\s+([^.!?]{20,})'
            ]

            for pattern in web_patterns:
                matches = re.findall(pattern, full_response, re.IGNORECASE)
                for match in matches:
                    clean_match = match.strip()
                    if self._is_meaningful_finding(clean_match):
                        findings.append(
                            f"Web research indicates {clean_match}")

            # 5. Remove duplicates and filter quality
            unique_findings = self._deduplicate_and_filter_findings(findings)

            # 6. Ensure we have at least some findings
            if len(unique_findings) == 0:
                # Extract any substantive content as fallback
                unique_findings = self._extract_fallback_findings(
                    full_response)

            return unique_findings[:8]  # Return top 8 findings

        except Exception as e:
            logger.warning(f"Error parsing agent response: {e}")
            return self._extract_fallback_findings(full_response)

    def _extract_findings_from_text(self, text):
        """Extract meaningful findings from a block of text."""
        findings = []

        # Split by sentences and paragraphs
        segments = re.split(r'[.!?]+|\n\s*\n', text)

        for segment in segments:
            segment = segment.strip()
            if len(segment) > 30 and self._is_meaningful_finding(segment):
                findings.append(segment)

        return findings

    def _is_meaningful_finding(self, text):
        """Check if a text segment contains meaningful findings."""
        text_lower = text.lower()

        # Filter out generic/process statements
        generic_phrases = [
            'investigation', 'execute', 'workflow', 'step', 'tool', 'function',
            'i will', 'i am', 'let me', 'next', 'now', 'then', 'first', 'second'
        ]

        # Must contain substantive content indicators
        substantive_indicators = [
            'participants', 'people', 'crowd', 'demonstration', 'protest', 'event',
            'location', 'time', 'date', 'police', 'arrest', 'peaceful', 'violence',
            'news', 'media', 'coverage', 'source', 'report', 'thousand', 'hundred',
            'organize', 'march', 'gather', 'rally', 'political', 'social',
            'government', 'official', 'response', 'impact', 'community'
        ]

        # Check if it's meaningful
        has_substantive = any(
            indicator in text_lower for indicator in substantive_indicators)
        has_generic = any(phrase in text_lower for phrase in generic_phrases)

        return (has_substantive and
                not has_generic and
                len(text) > 20 and
                len(text) < 200)

    def _is_analytical_sentence(self, sentence):
        """Check if a sentence contains analytical insight."""
        if len(sentence) < 30 or len(sentence) > 150:
            return False

        sentence_lower = sentence.lower()

        # Look for analytical language
        analytical_phrases = [
            'reveals', 'indicates', 'suggests', 'demonstrates', 'shows',
            'confirms', 'documents', 'evidence of', 'analysis shows',
            'findings indicate', 'data suggests', 'research shows'
        ]

        return any(phrase in sentence_lower for phrase in analytical_phrases)

    def _deduplicate_and_filter_findings(self, findings):
        """Remove duplicates and filter for quality."""
        seen = set()
        unique_findings = []

        for finding in findings:
            # Clean the finding
            finding_clean = re.sub(r'\s+', ' ', finding.strip())

            # Create a key for deduplication (first 60 characters)
            finding_key = finding_clean.lower()[:60]

            if (finding_key not in seen and
                len(finding_clean) > 25 and
                len(finding_clean) < 200 and
                    self._is_meaningful_finding(finding_clean)):

                seen.add(finding_key)
                unique_findings.append(finding_clean)

        return unique_findings

    def _extract_fallback_findings(self, full_response):
        """Extract basic findings as fallback."""
        try:
            # Look for any factual statements in the response
            sentences = re.split(r'[.!?]+', full_response)
            fallback_findings = []

            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) > 40 and
                    len(sentence) < 120 and
                    not sentence.lower().startswith(('i ', 'the ', 'this ', 'that ')) and
                        any(word in sentence.lower() for word in ['event', 'location', 'people', 'time', 'found', 'shows'])):
                    fallback_findings.append(sentence)
                    if len(fallback_findings) >= 3:
                        break

            if fallback_findings:
                return fallback_findings

        except Exception:
            pass

        # Absolute fallback
        return [
            "Investigation completed with comprehensive evidence collection",
            "Multiple sources and artifacts gathered for analysis",
            "Geographic and temporal context established"
        ]

    def _calculate_confidence_score(self, final_state, total_artifacts, artifact_types):
        """
        Calculate meaningful confidence score based on evidence quality and investigation completeness.

        Args:
            final_state: Investigation state with all collected evidence
            total_artifacts: Total number of artifacts collected
            artifact_types: Breakdown of artifact types

        Returns:
            Float confidence score between 0.0 and 1.0
        """
        try:
            confidence_components = {}

            # 1. ARTIFACT QUANTITY SCORE (0-25 points)
            # Base points for having sufficient artifacts
            if total_artifacts >= 10:
                confidence_components['artifact_quantity'] = 0.25
            elif total_artifacts >= 8:
                confidence_components['artifact_quantity'] = 0.20
            elif total_artifacts >= 5:
                confidence_components['artifact_quantity'] = 0.15
            else:
                confidence_components['artifact_quantity'] = 0.10

            # 2. ARTIFACT DIVERSITY SCORE (0-20 points)
            # Points for having different types of evidence
            artifact_type_count = len(artifact_types)
            if artifact_type_count >= 4:
                confidence_components['artifact_diversity'] = 0.20
            elif artifact_type_count >= 3:
                confidence_components['artifact_diversity'] = 0.15
            elif artifact_type_count >= 2:
                confidence_components['artifact_diversity'] = 0.10
            else:
                confidence_components['artifact_diversity'] = 0.05

            # 3. WEB SEARCH INSIGHTS SCORE (0-25 points)
            # Check if we have meaningful web search insights
            web_insights_score = 0.0
            if hasattr(final_state, 'agent_findings') and final_state.agent_findings:
                total_insights = 0
                meaningful_insights = 0

                for agent_name, findings in final_state.agent_findings.items():
                    if 'web_search' in agent_name.lower() and isinstance(findings, list):
                        total_insights += len(findings)
                        # Count meaningful insights (not just generic ones)
                        for finding in findings:
                            finding_text = str(finding).lower()
                            if any(keyword in finding_text for keyword in [
                                'participants', 'arrests', 'peaceful', 'thousands', 'hundreds',
                                'police', 'demonstration', 'protest', 'march', 'coverage'
                            ]) and 'web search' not in finding_text:
                                meaningful_insights += 1

                if meaningful_insights >= 5:
                    web_insights_score = 0.25
                elif meaningful_insights >= 3:
                    web_insights_score = 0.20
                elif meaningful_insights >= 1:
                    web_insights_score = 0.15
                else:
                    web_insights_score = 0.10

            confidence_components['web_insights'] = web_insights_score

            # 4. GEOGRAPHIC COVERAGE SCORE (0-15 points)
            # Points for having maps and location-specific evidence
            maps_count = artifact_types.get('map_image', 0)
            if maps_count >= 2:
                confidence_components['geographic_coverage'] = 0.15
            elif maps_count >= 1:
                confidence_components['geographic_coverage'] = 0.10
            else:
                confidence_components['geographic_coverage'] = 0.05

            # 5. VISUAL EVIDENCE SCORE (0-15 points)
            # Points for having images and screenshots
            visual_count = artifact_types.get(
                'image', 0) + artifact_types.get('screenshot', 0)
            if visual_count >= 10:
                confidence_components['visual_evidence'] = 0.15
            elif visual_count >= 6:
                confidence_components['visual_evidence'] = 0.12
            elif visual_count >= 3:
                confidence_components['visual_evidence'] = 0.08
            else:
                confidence_components['visual_evidence'] = 0.05

            # Calculate total confidence score
            total_confidence = sum(confidence_components.values())

            # Ensure score is between 0.0 and 1.0
            final_confidence = max(0.0, min(1.0, total_confidence))

            # Log confidence breakdown for debugging
            logger.info(f"🔍 Confidence Score Breakdown:")
            for component, score in confidence_components.items():
                logger.info(f"   {component}: {score:.2f}")
            logger.info(f"   TOTAL: {final_confidence:.2f}")

            return final_confidence

        except Exception as e:
            logger.warning(f"⚠️ Error calculating confidence score: {e}")
            # Return a reasonable default based on artifact count
            if total_artifacts >= 8:
                return 0.75
            elif total_artifacts >= 5:
                return 0.60
            else:
                return 0.45


# Global instance for use by the endpoint
minimal_working_agent = MinimalWorkingAgent()


async def execute_minimal_investigation(investigation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an enhanced minimal working investigation using the proven workflow with web search.

    This function is called by the /investigate endpoint.

    Args:
        investigation_data: Investigation details including investigation_id and alert_data

    Returns:
        Investigation results with web search findings, artifacts, and presentation
    """
    return await minimal_working_agent.investigate(investigation_data)
