"""Three-tier task complexity classifier (rule-based, on-device).

Returns: "simple" | "medium" | "complex"
Checks TierOverride table first; falls back to keyword verb lists.
Unknown prompts default to "complex" (safest assumption).
"""

from __future__ import annotations

import re

_SIMPLE_VERBS = {
    "open", "close", "play", "pause", "stop", "show", "read", "tell",
    "search", "find", "navigate", "go", "what", "when", "who", "where",
    "how", "is", "are", "can", "does", "did", "list", "check", "display",
}

_MEDIUM_VERBS = {
    "create", "make", "write", "save", "install", "update", "download",
    "move", "rename", "copy", "add", "set", "change", "edit", "new",
    "upload", "import", "export", "generate",
}

_COMPLEX_VERBS = {
    "delete", "remove", "execute", "run", "commit", "push", "deploy",
    "format", "merge", "configure", "send", "post", "publish", "build",
    "compile", "refactor", "migrate", "drop", "reset", "overwrite",
    "uninstall", "destroy", "kill", "terminate", "write",
    "implement", "generate",
}


class Classifier:
    """Classifies prompts into Simple / Medium / Complex tiers."""

    def __init__(self, overrides: dict[str, str]) -> None:
        self._overrides = {k.lower(): v for k, v in overrides.items()}

    def classify(self, text: str) -> str:
        """Return 'simple', 'medium', or 'complex'."""
        normalized = text.lower().strip()

        # Check user overrides first
        for pattern, tier in self._overrides.items():
            if re.search(r"\b" + re.escape(pattern) + r"\b", normalized):
                return tier

        # Extract first meaningful verb/word
        words = re.findall(r"\b[a-z]+\b", normalized)
        for word in words:
            if word in _COMPLEX_VERBS:
                return "complex"
            if word in _MEDIUM_VERBS:
                return "medium"
            if word in _SIMPLE_VERBS:
                return "simple"

        return "complex"  # unknown → safest default
