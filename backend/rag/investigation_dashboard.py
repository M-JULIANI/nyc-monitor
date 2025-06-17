#!/usr/bin/env python3
"""
Real-time Investigation Dashboard for Atlas Multi-Agent System
Provides live monitoring of agent interactions, tool calls, and investigation progress.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from rag.investigation.state_manager import state_manager
import logging

# Configure logging to capture everything
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s')


@dataclass
class InvestigationEvent:
    """Represents an event in the investigation timeline"""
    timestamp: datetime
    event_type: str  # 'agent_start', 'tool_call', 'state_update', 'error', 'completion'
    agent: str
    tool: str = None
    message: str = ""
    data: Dict[str, Any] = None


class InvestigationDashboard:
    """Real-time dashboard for monitoring investigation progress"""

    def __init__(self):
        self.events: List[InvestigationEvent] = []
        self.active_investigations: Dict[str, Dict] = {}
        self.monitoring = False

    def log_event(self, event_type: str, agent: str, tool: str = None, message: str = "", data: Dict = None):
        """Log an investigation event"""
        event = InvestigationEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            agent=agent,
            tool=tool,
            message=message,
            data=data or {}
        )
        self.events.append(event)
        self._display_event(event)

    def _display_event(self, event: InvestigationEvent):
        """Display an event in real-time"""
        time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

        # Color-coded output based on event type
        colors = {
            'agent_start': '🟢',
            'tool_call': '🔧',
            'state_update': '📊',
            'error': '🔴',
            'completion': '✅',
            'info': 'ℹ️'
        }

        icon = colors.get(event.event_type, '📝')
        tool_info = f" [{event.tool}]" if event.tool else ""

        print(f"{time_str} | {icon} {event.agent}{tool_info} | {event.message}")

        # Show data if available and interesting
        if event.data and any(key in event.data for key in ['result', 'error', 'progress']):
            for key, value in event.data.items():
                if key in ['result', 'error', 'progress']:
                    value_str = str(value)[
                        :100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"    ↳ {key}: {value_str}")

    def start_monitoring(self, investigation_id: str):
        """Start monitoring a specific investigation"""
        self.monitoring = True
        self.active_investigations[investigation_id] = {
            'start_time': datetime.utcnow(),
            'events': 0,
            'agents_active': set(),
            'tools_called': set()
        }

        print(f"\n🎯 INVESTIGATION DASHBOARD STARTED")
        print(f"📋 Investigation ID: {investigation_id}")
        print(
            f"⏰ Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def update_investigation_stats(self, investigation_id: str):
        """Update statistics for an investigation"""
        if investigation_id in self.active_investigations:
            stats = self.active_investigations[investigation_id]
            stats['events'] = len([e for e in self.events if investigation_id in str(
                e.data.get('investigation_id', ''))])

            # Get current investigation state
            investigation_state = state_manager.get_investigation(
                investigation_id)
            if investigation_state:
                print(f"\n📊 INVESTIGATION STATS UPDATE:")
                print(f"   Phase: {investigation_state.phase}")
                print(f"   Iteration: {investigation_state.iteration_count}")
                print(
                    f"   Confidence: {investigation_state.confidence_score:.2f}")
                print(f"   Artifacts: {len(investigation_state.artifacts)}")
                print(f"   Events Logged: {stats['events']}")
                print("-" * 40)

    def show_investigation_timeline(self):
        """Show a chronological timeline of all events"""
        print(f"\n📅 INVESTIGATION TIMELINE ({len(self.events)} events)")
        print("=" * 60)

        for i, event in enumerate(self.events[-20:], 1):  # Show last 20 events
            time_str = event.timestamp.strftime("%H:%M:%S")
            tool_info = f" → {event.tool}" if event.tool else ""
            print(f"{i:2d}. {time_str} | {event.agent}{tool_info} | {event.message}")

    def show_agent_summary(self):
        """Show summary of agent activities"""
        agent_stats = {}
        tool_stats = {}

        for event in self.events:
            # Count agent activities
            if event.agent not in agent_stats:
                agent_stats[event.agent] = {'events': 0, 'tools': set()}
            agent_stats[event.agent]['events'] += 1
            if event.tool:
                agent_stats[event.agent]['tools'].add(event.tool)

                # Count tool usage
                if event.tool not in tool_stats:
                    tool_stats[event.tool] = 0
                tool_stats[event.tool] += 1

        print(f"\n👥 AGENT ACTIVITY SUMMARY:")
        print("-" * 40)
        for agent, stats in agent_stats.items():
            tools_used = len(stats['tools'])
            print(
                f"   {agent}: {stats['events']} events, {tools_used} unique tools")

        print(f"\n🔧 TOOL USAGE SUMMARY:")
        print("-" * 25)
        for tool, count in sorted(tool_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {tool}: {count} calls")

    def stop_monitoring(self):
        """Stop monitoring and show final summary"""
        self.monitoring = False
        print(f"\n🏁 INVESTIGATION DASHBOARD STOPPED")
        print("=" * 50)

        self.show_investigation_timeline()
        self.show_agent_summary()

        print(f"\n📈 FINAL SUMMARY:")
        print(f"   Total Events: {len(self.events)}")
        print(f"   Active Time: {datetime.utcnow().strftime('%H:%M:%S')}")
        print("=" * 50)


# Global dashboard instance
dashboard = InvestigationDashboard()


class DashboardLogger(logging.Handler):
    """Custom logging handler that feeds events to the dashboard"""

    def emit(self, record):
        try:
            # Extract information from log record
            module_parts = record.name.split('.')
            agent = 'system'
            tool = None

            # Identify agent from module name
            if 'research_agent' in record.name:
                agent = 'Research Agent'
            elif 'data_agent' in record.name:
                agent = 'Data Agent'
            elif 'analysis_agent' in record.name:
                agent = 'Analysis Agent'
            elif 'report_agent' in record.name:
                agent = 'Report Agent'
            elif 'state_manager' in record.name:
                agent = 'State Manager'
            elif 'investigation_service' in record.name:
                agent = 'Investigation Service'

            # Identify tool calls
            if 'tools' in record.name:
                module_parts = record.name.split('.')
                if len(module_parts) > 2:
                    tool = module_parts[-1].replace('_tools',
                                                    '').replace('_func', '')

            # Determine event type
            event_type = 'info'
            if record.levelname == 'ERROR':
                event_type = 'error'
            elif 'starting' in record.getMessage().lower():
                event_type = 'agent_start'
            elif 'calling' in record.getMessage().lower() or tool:
                event_type = 'tool_call'
            elif 'state' in record.getMessage().lower():
                event_type = 'state_update'
            elif 'complete' in record.getMessage().lower():
                event_type = 'completion'

            # Log to dashboard
            dashboard.log_event(
                event_type=event_type,
                agent=agent,
                tool=tool,
                message=record.getMessage(),
                data={'level': record.levelname, 'module': record.name}
            )

        except Exception:
            pass  # Don't break if dashboard logging fails


def setup_dashboard_logging():
    """Set up logging to feed into the dashboard"""
    dashboard_handler = DashboardLogger()
    dashboard_handler.setLevel(logging.DEBUG)

    # Add to specific loggers
    loggers_to_monitor = [
        'rag.investigation_service',
        'rag.investigation.state_manager',
        'rag.agents.research_agent',
        'rag.agents.data_agent',
        'rag.agents.analysis_agent',
        'rag.agents.report_agent',
        'rag.tools.research_tools',
        'rag.tools.data_tools',
        'rag.tools.analysis_tools',
        'rag.tools.report_tools'
    ]

    for logger_name in loggers_to_monitor:
        logger = logging.getLogger(logger_name)
        logger.addHandler(dashboard_handler)


async def run_investigation_with_dashboard(test_alert):
    """Run an investigation with dashboard monitoring"""
    from rag.investigation_service import investigate_alert

    # Set up dashboard logging
    setup_dashboard_logging()

    # Start monitoring
    investigation_id = f"DASH-{int(time.time())}"
    dashboard.start_monitoring(investigation_id)

    try:
        # Run investigation
        dashboard.log_event(
            'agent_start', 'Investigation Service', message="Starting investigation")
        result, actual_investigation_id = await investigate_alert(test_alert)

        # Update with actual ID
        investigation_id = actual_investigation_id
        dashboard.log_event('completion', 'Investigation Service',
                            message=f"Investigation completed: {investigation_id}")

        # Show periodic updates
        dashboard.update_investigation_stats(investigation_id)

        return result, investigation_id

    except Exception as e:
        dashboard.log_event('error', 'Investigation Service',
                            message=f"Investigation failed: {str(e)}")
        raise
    finally:
        dashboard.stop_monitoring()


if __name__ == "__main__":
    print("🎯 Investigation Dashboard - Ready for monitoring")
    print("Import this module and use run_investigation_with_dashboard() to monitor investigations.")
