"""Progress tracking for investigations."""

import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProgressStatus(Enum):
    """Investigation progress status."""
    STARTING = "starting"
    AGENT_ACTIVE = "agent_active"
    TOOL_EXECUTING = "tool_executing"
    THINKING = "thinking"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressUpdate:
    """A single progress update."""
    timestamp: datetime
    investigation_id: str
    status: ProgressStatus
    active_agent: Optional[str] = None
    current_task: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict] = None


class InvestigationProgressTracker:
    """Tracks progress of ongoing investigations."""

    def __init__(self):
        self._progress_streams: Dict[str, List[ProgressUpdate]] = {}
        self._active_investigations: Dict[str, bool] = {}
        self._progress_queues: Dict[str, asyncio.Queue] = {}

    def start_investigation(self, investigation_id: str):
        """Start tracking an investigation."""
        self._progress_streams[investigation_id] = []
        self._active_investigations[investigation_id] = True
        self._progress_queues[investigation_id] = asyncio.Queue()

        self.add_progress(
            investigation_id=investigation_id,
            status=ProgressStatus.STARTING,
            message="Investigation initiated"
        )

        logger.info(
            f"Started progress tracking for investigation {investigation_id}")

    def add_progress(
        self,
        investigation_id: str,
        status: ProgressStatus,
        active_agent: Optional[str] = None,
        current_task: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Add a progress update."""
        if investigation_id not in self._progress_streams:
            self.start_investigation(investigation_id)

        update = ProgressUpdate(
            timestamp=datetime.utcnow(),
            investigation_id=investigation_id,
            status=status,
            active_agent=active_agent,
            current_task=current_task,
            message=message,
            metadata=metadata
        )

        # Store in progress stream
        self._progress_streams[investigation_id].append(update)

        # Put in queue for streaming
        if investigation_id in self._progress_queues:
            try:
                self._progress_queues[investigation_id].put_nowait(update)
            except asyncio.QueueFull:
                logger.warning(
                    f"Progress queue full for investigation {investigation_id}")

        logger.info(
            f"Progress update for {investigation_id}: {status.value} - {message}")

    def complete_investigation(self, investigation_id: str, message: str = "Investigation completed"):
        """Mark investigation as completed."""
        self.add_progress(
            investigation_id=investigation_id,
            status=ProgressStatus.COMPLETED,
            message=message
        )
        self._active_investigations[investigation_id] = False

        logger.info(
            f"Completed progress tracking for investigation {investigation_id}")

    def error_investigation(self, investigation_id: str, error_message: str):
        """Mark investigation as errored."""
        self.add_progress(
            investigation_id=investigation_id,
            status=ProgressStatus.ERROR,
            message=f"Investigation failed: {error_message}"
        )
        self._active_investigations[investigation_id] = False

        logger.error(
            f"Investigation {investigation_id} failed: {error_message}")

    def get_progress(self, investigation_id: str) -> List[ProgressUpdate]:
        """Get all progress updates for an investigation."""
        return self._progress_streams.get(investigation_id, [])

    def get_latest_progress(self, investigation_id: str) -> Optional[ProgressUpdate]:
        """Get the latest progress update for an investigation."""
        progress = self._progress_streams.get(investigation_id, [])
        return progress[-1] if progress else None

    def is_active(self, investigation_id: str) -> bool:
        """Check if investigation is still active."""
        return self._active_investigations.get(investigation_id, False)

    async def stream_progress(self, investigation_id: str) -> AsyncGenerator[ProgressUpdate, None]:
        """Stream progress updates for an investigation."""
        if investigation_id not in self._progress_queues:
            return

        queue = self._progress_queues[investigation_id]

        # Send existing progress first
        for update in self._progress_streams.get(investigation_id, []):
            yield update

        # Stream new updates
        while self.is_active(investigation_id):
            try:
                update = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield update

                if update.status in [ProgressStatus.COMPLETED, ProgressStatus.ERROR]:
                    break

            except asyncio.TimeoutError:
                continue

    def cleanup_investigation(self, investigation_id: str):
        """Clean up resources for completed investigation."""
        if investigation_id in self._progress_queues:
            del self._progress_queues[investigation_id]

        # Keep progress history but mark as inactive
        self._active_investigations[investigation_id] = False

        logger.info(
            f"Cleaned up progress tracking for investigation {investigation_id}")


# Global progress tracker instance
progress_tracker = InvestigationProgressTracker()


def get_progress_tracker() -> InvestigationProgressTracker:
    """Get the global progress tracker instance."""
    return progress_tracker
