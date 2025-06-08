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

"""Distributed tracing for multi-agent investigations."""

import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TraceEventType(Enum):
    """Types of trace events."""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    MESSAGE_SEND = "message_send"
    MESSAGE_RECEIVE = "message_receive"
    SUB_AGENT_INVOKE = "sub_agent_invoke"
    ERROR = "error"
    MILESTONE = "milestone"


@dataclass
class TraceSpan:
    """A trace span representing a single operation."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    event_type: TraceEventType
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    status: str = "started"
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def finish(self, status: str = "completed", error: Optional[str] = None):
        """Mark the span as finished."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status
        if error:
            self.error = error
            self.status = "error"


@dataclass
class MessageTrace:
    """Trace data for messages between agents."""
    message_id: str
    trace_id: str
    span_id: str
    from_agent: str
    to_agent: Optional[str]
    message_type: str
    timestamp: float
    content_preview: str  # First 200 chars of content
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DistributedTracer:
    """Distributed tracing system for multi-agent investigations."""

    def __init__(self):
        self._traces: Dict[str, List[TraceSpan]] = {}
        self._messages: Dict[str, List[MessageTrace]] = {}
        self._active_spans: Dict[str, TraceSpan] = {}
        self._context_stack: List[str] = []

    def start_trace(self, trace_id: str, operation_name: str, metadata: Dict = None) -> str:
        """Start a new trace."""
        if trace_id not in self._traces:
            self._traces[trace_id] = []
            self._messages[trace_id] = []

        span = self._create_span(
            trace_id=trace_id,
            operation_name=operation_name,
            event_type=TraceEventType.MILESTONE,
            metadata=metadata or {}
        )

        logger.info(f"🔍 Started trace: {trace_id} ({operation_name})")
        return span.span_id

    def _create_span(
        self,
        trace_id: str,
        operation_name: str,
        event_type: TraceEventType,
        parent_span_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Dict = None
    ) -> TraceSpan:
        """Create a new trace span."""
        span_id = str(uuid.uuid4())[:8]

        # Use current context as parent if not specified
        if not parent_span_id and self._context_stack:
            parent_span_id = self._context_stack[-1]

        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            event_type=event_type,
            start_time=time.time(),
            agent_name=agent_name,
            tool_name=tool_name,
            metadata=metadata or {}
        )

        self._traces[trace_id].append(span)
        self._active_spans[span_id] = span

        return span

    @contextmanager
    def span(
        self,
        trace_id: str,
        operation_name: str,
        event_type: TraceEventType,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Dict = None
    ):
        """Context manager for creating and managing spans."""
        span = self._create_span(
            trace_id=trace_id,
            operation_name=operation_name,
            event_type=event_type,
            agent_name=agent_name,
            tool_name=tool_name,
            metadata=metadata
        )

        self._context_stack.append(span.span_id)

        try:
            yield span
            span.finish("completed")
        except Exception as e:
            span.finish("error", str(e))
            raise
        finally:
            self._context_stack.pop()
            if span.span_id in self._active_spans:
                del self._active_spans[span.span_id]

    def trace_agent_execution(
        self,
        trace_id: str,
        agent_name: str,
        operation: str,
        metadata: Dict = None
    ):
        """Trace agent execution."""
        return self.span(
            trace_id=trace_id,
            operation_name=f"agent:{agent_name}:{operation}",
            event_type=TraceEventType.AGENT_START,
            agent_name=agent_name,
            metadata=metadata
        )

    def trace_tool_execution(
        self,
        trace_id: str,
        tool_name: str,
        agent_name: str,
        metadata: Dict = None
    ):
        """Trace tool execution."""
        return self.span(
            trace_id=trace_id,
            operation_name=f"tool:{tool_name}",
            event_type=TraceEventType.TOOL_START,
            agent_name=agent_name,
            tool_name=tool_name,
            metadata=metadata
        )

    def trace_message(
        self,
        trace_id: str,
        from_agent: str,
        to_agent: Optional[str],
        message_type: str,
        content: str,
        metadata: Dict = None
    ) -> str:
        """Trace a message between agents."""
        message_id = str(uuid.uuid4())[:8]

        # Create content preview (first 200 chars)
        content_preview = content[:200] + \
            "..." if len(content) > 200 else content

        # Get current span for correlation
        current_span_id = self._context_stack[-1] if self._context_stack else None

        message_trace = MessageTrace(
            message_id=message_id,
            trace_id=trace_id,
            span_id=current_span_id or "root",
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            timestamp=time.time(),
            content_preview=content_preview,
            metadata=metadata or {}
        )

        if trace_id not in self._messages:
            self._messages[trace_id] = []
        self._messages[trace_id].append(message_trace)

        logger.info(
            f"📨 Message trace: {from_agent} → {to_agent or 'broadcast'} ({message_type})")
        return message_id

    def trace_error(
        self,
        trace_id: str,
        error: Exception,
        agent_name: Optional[str] = None,
        context: str = ""
    ):
        """Trace an error."""
        span = self._create_span(
            trace_id=trace_id,
            operation_name=f"error:{context}",
            event_type=TraceEventType.ERROR,
            agent_name=agent_name,
            metadata={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            }
        )
        span.finish("error", str(error))

        logger.error(f"🚨 Error trace: {context} - {error}")

    def get_trace_summary(self, trace_id: str) -> Dict:
        """Get a summary of a trace."""
        if trace_id not in self._traces:
            return {"error": "Trace not found"}

        spans = self._traces[trace_id]
        messages = self._messages.get(trace_id, [])

        # Calculate trace duration
        start_times = [s.start_time for s in spans if s.start_time]
        end_times = [s.end_time for s in spans if s.end_time]

        total_duration_ms = 0
        if start_times and end_times:
            total_duration_ms = round(
                (max(end_times) - min(start_times)) * 1000, 2)

        # Count events by type
        event_counts = {}
        for span in spans:
            event_type = span.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        # Get agent activity
        agents = set(s.agent_name for s in spans if s.agent_name)

        # Get tools used
        tools = set(s.tool_name for s in spans if s.tool_name)

        return {
            "trace_id": trace_id,
            "total_duration_ms": total_duration_ms,
            "total_spans": len(spans),
            "total_messages": len(messages),
            "event_counts": event_counts,
            "agents_involved": list(agents),
            "tools_used": list(tools),
            "status": "completed" if all(s.status in ["completed", "error"] for s in spans) else "running",
            "errors": [s.error for s in spans if s.error]
        }

    def get_trace_timeline(self, trace_id: str) -> List[Dict]:
        """Get a chronological timeline of trace events."""
        if trace_id not in self._traces:
            return []

        spans = self._traces[trace_id]
        messages = self._messages.get(trace_id, [])

        # Combine spans and messages into timeline
        timeline = []

        # Add span events
        for span in spans:
            timeline.append({
                "timestamp": span.start_time,
                "type": "span_start",
                "span_id": span.span_id,
                "operation": span.operation_name,
                "agent": span.agent_name,
                "tool": span.tool_name,
                "metadata": span.metadata
            })

            if span.end_time:
                timeline.append({
                    "timestamp": span.end_time,
                    "type": "span_end",
                    "span_id": span.span_id,
                    "operation": span.operation_name,
                    "duration_ms": span.duration_ms,
                    "status": span.status,
                    "error": span.error
                })

        # Add message events
        for message in messages:
            timeline.append({
                "timestamp": message.timestamp,
                "type": "message",
                "message_id": message.message_id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type,
                "content_preview": message.content_preview,
                "metadata": message.metadata
            })

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        # Convert timestamps to ISO format
        for event in timeline:
            event["timestamp"] = datetime.fromtimestamp(
                event["timestamp"]).isoformat()

        return timeline

    def export_trace(self, trace_id: str) -> Dict:
        """Export complete trace data."""
        if trace_id not in self._traces:
            return {"error": "Trace not found"}

        spans = [asdict(span) for span in self._traces[trace_id]]
        messages = [asdict(msg) for msg in self._messages.get(trace_id, [])]

        return {
            "trace_id": trace_id,
            "spans": spans,
            "messages": messages,
            "summary": self.get_trace_summary(trace_id),
            "timeline": self.get_trace_timeline(trace_id),
            "exported_at": datetime.utcnow().isoformat()
        }


# Global tracer instance
distributed_tracer = DistributedTracer()


def get_distributed_tracer() -> DistributedTracer:
    """Get the global distributed tracer instance."""
    return distributed_tracer
