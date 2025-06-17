# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coordination tools for state management and workflow control."""

from typing import Dict, Any, List
from google.adk.tools import FunctionTool
from ..investigation.state_manager import state_manager, InvestigationPhase

# TODO: Implement coordination tools


def update_alert_status_func(
    alert_id: str,
    status: str,
    notes: str = ""
) -> dict:
    """Update the status of an alert being investigated.

    Args:
        alert_id: The ID of the alert to update
        status: New status (investigating, escalated, resolved, closed)
        notes: Additional notes about the status change

    Returns:
        Updated alert information
    """
    # Mock implementation for now
    return {
        "alert_id": alert_id,
        "previous_status": "open",
        "new_status": status,
        "updated_at": "2025-01-03T12:00:00Z",
        "notes": notes,
        "updated_by": "investigation_orchestrator"
    }


def manage_investigation_state_func(
    investigation_id: str,
    action: str,
    data: str = ""
) -> dict:
    """Manage the state of an ongoing investigation.

    Args:
        investigation_id: The ID of the investigation
        action: Action to perform (advance_phase, add_finding, update_confidence, complete)
        data: Additional data for the action (JSON string format)

    Returns:
        Updated investigation state information
    """
    import json

    try:
        investigation_state = state_manager.get_investigation(investigation_id)

        if not investigation_state:
            return {
                "error": f"Investigation {investigation_id} not found",
                "success": False
            }

        # Parse data if provided
        parsed_data = {}
        if data:
            try:
                parsed_data = json.loads(
                    data) if isinstance(data, str) else data
            except json.JSONDecodeError:
                # If not JSON, treat as simple string data
                parsed_data = {"data": data}

        if action == "advance_phase":
            # Advance to next investigation phase
            if investigation_state.phase == InvestigationPhase.RECONNAISSANCE:
                investigation_state.phase = InvestigationPhase.ANALYSIS
            elif investigation_state.phase == InvestigationPhase.ANALYSIS:
                investigation_state.phase = InvestigationPhase.DEEP_DIVE
            elif investigation_state.phase == InvestigationPhase.DEEP_DIVE:
                investigation_state.phase = InvestigationPhase.REPORTING

            investigation_state.iteration_count += 1

        elif action == "add_finding":
            # Add a new finding to the investigation
            if parsed_data and "finding" in parsed_data:
                investigation_state.findings.append(parsed_data["finding"])
            elif parsed_data and "data" in parsed_data:
                investigation_state.findings.append(parsed_data["data"])

        elif action == "update_confidence":
            # Update the confidence score
            if parsed_data and "confidence" in parsed_data:
                investigation_state.confidence_score = parsed_data["confidence"]

        elif action == "complete":
            # Mark investigation as complete
            investigation_state.is_complete = True
            investigation_state.phase = InvestigationPhase.REPORTING

        # Update the investigation in the state manager
        state_manager.update_investigation(
            investigation_id, investigation_state)

        return {
            "investigation_id": investigation_id,
            "action_performed": action,
            "current_phase": investigation_state.phase.value,
            "iteration_count": investigation_state.iteration_count,
            "confidence_score": investigation_state.confidence_score,
            "findings_count": len(investigation_state.findings),
            "is_complete": investigation_state.is_complete,
            "success": True
        }

    except Exception as e:
        return {
            "error": f"Failed to manage investigation state: {e}",
            "investigation_id": investigation_id,
            "action": action,
            "success": False
        }


def coordinate_sub_agents_func(
    task_assignments: list,
    priority: str = "normal"
) -> dict:
    """Coordinate task assignments across sub-agents.

    Args:
        task_assignments: List of tasks to assign to sub-agents
        priority: Priority level (low, normal, high, urgent)

    Returns:
        Task assignment results and coordination status
    """
    # Mock implementation for coordinating sub-agents
    coordination_results = {
        "total_tasks": len(task_assignments),
        "assigned_tasks": [],
        "failed_assignments": [],
        "priority": priority,
        "coordination_id": f"coord_{len(task_assignments)}_{priority}"
    }

    for task in task_assignments:
        # Handle both dict and string representations
        if isinstance(task, dict):
            agent_name = task.get("agent", "unknown")
            task_type = task.get("type", "unknown")
        else:
            # If task is a string, parse basic info
            agent_name = "unknown"
            task_type = str(task)

        # Simulate successful assignment
        coordination_results["assigned_tasks"].append({
            "agent": agent_name,
            "task_type": task_type,
            "task_id": f"task_{agent_name}_{task_type}",
            "status": "assigned",
            "estimated_completion": "5-10 minutes"
        })

    return coordination_results


# Create FunctionTool instances
update_alert_status = FunctionTool(update_alert_status_func)
manage_investigation_state = FunctionTool(manage_investigation_state_func)
coordinate_sub_agents = FunctionTool(coordinate_sub_agents_func)


def get_investigation_progress_func(
    investigation_id: str
) -> dict:
    """Get current investigation progress and status.

    Args:
        investigation_id: Unique identifier for the investigation

    Returns:
        Current investigation progress and findings
    """
    # TODO: Implement investigation progress retrieval
    return {}


# Create additional tool when implemented
# get_investigation_progress = FunctionTool(get_investigation_progress_func)
