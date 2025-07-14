"""Investigation workflow management for phase transitions."""

from typing import Dict, List, Optional
from .state_manager import InvestigationPhase, InvestigationState


class WorkflowManager:
    """Manages investigation workflow and phase transitions for 5-agent system."""

    def determine_next_phase(self, state: InvestigationState) -> InvestigationPhase:
        """Determine next investigation phase based on current state and agent findings."""
        current_phase = state.phase
        confidence = state.confidence_score

        # Phase transition logic based on 5-agent workflow
        if current_phase == InvestigationPhase.RECONNAISSANCE:
            # Move to analysis if we have initial findings from research and data agents
            research_findings = state.agent_findings.get("research_agent")
            data_findings = state.agent_findings.get("data_agent")

            if research_findings and data_findings:
                return InvestigationPhase.ANALYSIS
            return InvestigationPhase.RECONNAISSANCE

        elif current_phase == InvestigationPhase.ANALYSIS:
            # Move to deep dive if analysis agent has generated insights
            analysis_findings = state.agent_findings.get("analysis_agent")

            if analysis_findings and confidence < 0.7:
                # Need more investigation
                return InvestigationPhase.DEEP_DIVE
            elif analysis_findings and confidence >= 0.7:
                # Ready for reporting
                return InvestigationPhase.REPORTING
            return InvestigationPhase.ANALYSIS

        elif current_phase == InvestigationPhase.DEEP_DIVE:
            # Additional focused investigation - return to analysis or move to reporting
            if confidence >= 0.75 or state.iteration_count >= 3:
                return InvestigationPhase.REPORTING
            return InvestigationPhase.ANALYSIS

        elif current_phase == InvestigationPhase.REPORTING:
            # Report agent validation and creation
            report_findings = state.agent_findings.get("report_agent")
            if report_findings:
                return InvestigationPhase.COMPLETE
            return InvestigationPhase.REPORTING

        else:
            return InvestigationPhase.COMPLETE

    def generate_agent_tasks(self, state: InvestigationState) -> Dict[str, List[str]]:
        """Generate tasks for agents based on current phase and findings."""
        phase = state.phase
        alert = state.alert_data

        if phase == InvestigationPhase.RECONNAISSANCE:
            return self._generate_reconnaissance_tasks(alert)
        elif phase == InvestigationPhase.ANALYSIS:
            return self._generate_analysis_tasks(state)
        elif phase == InvestigationPhase.DEEP_DIVE:
            return self._generate_deep_dive_tasks(state)
        elif phase == InvestigationPhase.REPORTING:
            return self._generate_reporting_tasks(state)
        else:
            return {}

    def _generate_reconnaissance_tasks(self, alert) -> Dict[str, List[str]]:
        """Generate initial data collection tasks for research and data agents."""
        return {
            "research_agent": [
                f"Search social media for recent posts about {alert.location}",
                f"Find news coverage of {alert.event_type} in {alert.location}",
                f"Query live APIs for current conditions near {alert.location}",
                f"Collect multimedia evidence related to {alert.summary}"
            ],
            "data_agent": [
                f"Get demographic context for {alert.location}",
                f"Find similar historical incidents of type {alert.event_type}",
                f"Check construction permits and development activity",
                f"Analyze crime statistics for the area",
                f"Search knowledge base for related past investigations"
            ],
            "analysis_agent": [],
            "report_agent": []
        }

    def _generate_analysis_tasks(self, state: InvestigationState) -> Dict[str, List[str]]:
        """Generate synthesis tasks for analysis agent."""
        research_findings = state.agent_findings.get("research_agent", {})
        data_findings = state.agent_findings.get("data_agent", {})

        return {
            "research_agent": [],
            "data_agent": [],
            "analysis_agent": [
                "Correlate external research findings with historical data patterns",
                "Identify temporal and spatial patterns in the collected data",
                "Assess risk factors and escalation potential",
                "Generate testable hypotheses about incident causes",
                "Calculate confidence scores for pattern analysis"
            ],
            "report_agent": []
        }

    def _generate_deep_dive_tasks(self, state: InvestigationState) -> Dict[str, List[str]]:
        """Generate focused follow-up tasks based on analysis gaps."""
        analysis_findings = state.agent_findings.get("analysis_agent", {})

        # Determine what additional data is needed based on analysis
        tasks = {
            "research_agent": [],
            "data_agent": [],
            "analysis_agent": [],
            "report_agent": []
        }

        # Add targeted tasks based on confidence gaps
        if state.confidence_score < 0.6:
            tasks["research_agent"].extend([
                "Search for additional external validation of key findings",
                "Collect more recent social media data for trend analysis"
            ])
            tasks["data_agent"].extend([
                "Query additional datasets for statistical confirmation",
                "Find more specific historical precedents"
            ])

        return tasks

    def _generate_reporting_tasks(self, state: InvestigationState) -> Dict[str, List[str]]:
        """Generate validation and reporting tasks."""
        return {
            "research_agent": [],
            "data_agent": [],
            "analysis_agent": [],
            "report_agent": [
                "Fact-check all claims against collected evidence",
                "Assess reliability of all information sources",
                "Generate confidence scores for investigation conclusions",
                "Create comprehensive investigation report as artifacts",
                "Generate Google Slides presentation for stakeholders"
            ]
        }

    def should_continue_investigation(self, state: InvestigationState) -> bool:
        """Determine if investigation should continue based on confidence and time."""
        # Use existing state manager logic
        time_elapsed = (state.updated_at -
                        state.created_at).total_seconds() / 60

        # Continue if confidence is low and we haven't hit time limits
        if state.confidence_score < 0.75 and time_elapsed < 8 and state.iteration_count < 3:
            return True

        # Stop if we have high confidence or hit limits
        return False

    def get_priority_agents(self, state: InvestigationState) -> List[str]:
        """Get list of agents that should be active for current phase."""
        phase = state.phase

        if phase == InvestigationPhase.RECONNAISSANCE:
            return ["research_agent", "data_agent"]  # Parallel data collection
        elif phase == InvestigationPhase.ANALYSIS:
            return ["analysis_agent"]  # Synthesis
        elif phase == InvestigationPhase.DEEP_DIVE:
            # Determine based on what needs follow-up
            if state.confidence_score < 0.6:
                return ["research_agent", "data_agent"]  # More data needed
            else:
                return ["analysis_agent"]  # Better analysis needed
        elif phase == InvestigationPhase.REPORTING:
            return ["report_agent"]  # Validation and output
        else:
            return []
