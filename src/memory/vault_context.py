"""Builds AgentRequest.system_prefix context from vault search results.

Called from the pipeline immediately before dispatch (US2). Never raises —
any vault error degrades to an empty context string (FR-012).
"""

from __future__ import annotations
