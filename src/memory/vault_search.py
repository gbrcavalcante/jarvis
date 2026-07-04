"""In-memory vault index — parses Markdown notes and serves relevance search.

No embedding model or external search engine is used (see research.md
Decision 2): a lazy, mtime-based rebuild keeps a plain Python in-memory index
fast enough for vaults up to 10,000 notes.
"""

from __future__ import annotations
