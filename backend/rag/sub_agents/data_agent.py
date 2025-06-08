"""Data agent for internal knowledge and static data analysis."""

import os
from google.adk.agents import Agent
from ..prompts.data import return_data_instructions

# TODO: Implement data agent
data_agent = None

# data_agent = Agent(
#     model=os.getenv("DATA_AGENT_MODEL", "gemini-2.0-flash-001"),
#     name="data_agent",
#     instruction=return_data_instructions(),
#     tools=[
#         # search_knowledge_base,
#         # query_census_demographics,
#         # get_crime_statistics,
#         # find_similar_incidents,
#         # get_construction_permits,
#         # analyze_housing_market,
#     ]
# )
