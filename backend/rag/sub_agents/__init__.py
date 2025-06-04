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

"""Sub-agents module for multi-agent investigation system."""

from .research_agent import research_agent

# TODO: Add other agents as they are implemented
# from .data_agent import data_agent
# from .analysis_agent import analysis_agent
# from .report_agent import report_agent

__all__ = [
    "research_agent",
    # "data_agent",
    # "analysis_agent",
    # "report_agent",
]
