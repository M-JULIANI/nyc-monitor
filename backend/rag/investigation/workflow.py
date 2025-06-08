"""Investigation workflow management for phase transitions."""

from typing import Dict, List
from .state_manager import InvestigationPhase, InvestigationState


class WorkflowManager:
    """Manages investigation workflow and phase transitions."""

    def determine_next_phase(self, state: InvestigationState) -> InvestigationPhase:
        """Determine next investigation phase based on current state."""
        # TODO: Implement phase transition logic
        current_phase = state.phase

        if current_phase == InvestigationPhase.RECONNAISSANCE:
            return InvestigationPhase.ANALYSIS
        elif current_phase == InvestigationPhase.ANALYSIS:
            return InvestigationPhase.DEEP_DIVE
        elif current_phase == InvestigationPhase.DEEP_DIVE:
            return InvestigationPhase.REPORTING
        else:
            return InvestigationPhase.COMPLETE

    def generate_agent_tasks(self, state: InvestigationState) -> Dict[str, List[str]]:
        """Generate tasks for agents based on current phase."""
        # TODO: Implement task generation logic
        return {
            "research_agent": [],
            "data_agent": [],
            "analysis_agent": [],
            "report_agent": []
        }
