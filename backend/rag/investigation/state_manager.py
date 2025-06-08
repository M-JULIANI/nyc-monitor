"""Investigation state management for multi-agent coordination."""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class InvestigationPhase(Enum):
    """Investigation phases for workflow tracking."""
    RECONNAISSANCE = "reconnaissance"
    ANALYSIS = "analysis"
    DEEP_DIVE = "deep_dive"
    REPORTING = "reporting"
    COMPLETE = "complete"


@dataclass
class AlertData:
    """Alert data structure."""
    alert_id: str
    severity: int
    event_type: str
    location: str
    summary: str
    timestamp: datetime
    sources: list


@dataclass
class InvestigationState:
    """Investigation state tracking."""
    investigation_id: str
    alert_data: AlertData
    phase: InvestigationPhase
    iteration_count: int
    artifact_ticker: int  # Auto-incrementing counter for artifact naming
    findings: list  # Investigation findings
    artifacts: list  # Collected artifacts during investigation
    confidence_score: float  # Overall confidence score
    is_complete: bool  # Whether investigation is complete
    agent_findings: Dict[str, Any]
    confidence_scores: Dict[str, float]
    next_actions: list
    created_at: datetime
    updated_at: datetime


class InvestigationStateManager:
    """Manages investigation state and transitions."""

    def __init__(self):
        """Initialize the state manager."""
        self.investigations: Dict[str, InvestigationState] = {}

    def create_investigation(self, alert_data: AlertData) -> InvestigationState:
        """Create a new investigation state.

        Args:
            alert_data: Alert information to investigate

        Returns:
            New investigation state
        """
        investigation_id = f"{alert_data.alert_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        state = InvestigationState(
            investigation_id=investigation_id,
            alert_data=alert_data,
            phase=InvestigationPhase.RECONNAISSANCE,
            iteration_count=0,
            artifact_ticker=0,
            findings=[],
            artifacts=[],
            confidence_score=0.0,
            is_complete=False,
            agent_findings={},
            confidence_scores={},
            next_actions=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.investigations[investigation_id] = state
        return state

    def update_investigation(
        self,
        investigation_id: str,
        updates: Dict[str, Any]
    ) -> Optional[InvestigationState]:
        """Update investigation state.

        Args:
            investigation_id: ID of investigation to update
            updates: Dictionary of updates to apply

        Returns:
            Updated investigation state or None if not found
        """
        if investigation_id not in self.investigations:
            return None

        state = self.investigations[investigation_id]

        # Apply updates
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.updated_at = datetime.utcnow()
        return state

    def get_investigation(self, investigation_id: str) -> Optional[InvestigationState]:
        """Get investigation state by ID.

        Args:
            investigation_id: ID of investigation to retrieve

        Returns:
            Investigation state or None if not found
        """
        return self.investigations.get(investigation_id)

    def advance_phase(
        self,
        investigation_id: str,
        new_phase: InvestigationPhase
    ) -> Optional[InvestigationState]:
        """Advance investigation to next phase.

        Args:
            investigation_id: ID of investigation to advance
            new_phase: New phase to transition to

        Returns:
            Updated investigation state or None if not found
        """
        return self.update_investigation(investigation_id, {"phase": new_phase})

    def calculate_overall_confidence(self, investigation_id: str) -> float:
        """Calculate overall confidence score for investigation.

        Args:
            investigation_id: ID of investigation to calculate confidence for

        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        state = self.get_investigation(investigation_id)
        if not state or not state.confidence_scores:
            return 0.0

        # Simple average of all confidence scores
        scores = list(state.confidence_scores.values())
        return sum(scores) / len(scores)

    def get_next_artifact_ticker(self, investigation_id: str) -> int:
        """Get next artifact ticker and increment counter.

        Args:
            investigation_id: ID of investigation

        Returns:
            Next available ticker value for artifact naming
        """
        state = self.get_investigation(investigation_id)
        if not state:
            return 1

        state.artifact_ticker += 1
        state.updated_at = datetime.utcnow()
        return state.artifact_ticker

    def should_terminate_investigation(self, investigation_id: str) -> bool:
        """Determine if investigation should be terminated.

        Args:
            investigation_id: ID of investigation to check

        Returns:
            True if investigation should terminate
        """
        state = self.get_investigation(investigation_id)
        if not state:
            return True

        # Termination criteria
        confidence = self.calculate_overall_confidence(investigation_id)
        time_elapsed = (datetime.utcnow() -
                        state.created_at).total_seconds() / 60  # minutes

        # High confidence threshold
        if confidence > 0.85:
            return True

        # Maximum time limit (8 minutes)
        if time_elapsed > 8:
            return True

        # Emergency situations (high severity)
        if state.alert_data.severity >= 9 and time_elapsed > 4:
            return True

        # Maximum iterations
        if state.iteration_count > 3:
            return True

        return False


# Global state manager instance
state_manager = InvestigationStateManager()
