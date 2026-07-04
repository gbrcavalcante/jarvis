"""Extracts durable knowledge at session end and writes it to the vault.

Raw transcripts are never persisted (SC-005) — only the LLM-extracted
summary, upserted by topic slug under `_jarvis/knowledge/`.
"""

from __future__ import annotations
