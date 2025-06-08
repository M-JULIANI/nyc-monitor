"""Report agent for validation and report generation."""

import os
from google.adk.agents import Agent
from ..prompts.report import return_report_instructions

# TODO: Implement report agent
report_agent = None

# report_agent = Agent(
#     model=os.getenv("REPORT_AGENT_MODEL", "gemini-2.0-flash-001"),
#     name="report_agent",
#     instruction=return_report_instructions(),
#     tools=[
#         # fact_check_claims,
#         # assess_source_reliability,
#         # generate_confidence_scores,
#         # create_slides_report,
#     ]
# )
