"""Keyword-based urgency detection (rules are stored in the configuration)."""

from __future__ import annotations

import re
from collections.abc import Iterable


def is_urgent(text: str, keywords: Iterable[str]) -> bool:
    """Return ``True`` if any urgency keyword occurs in ``text`` as a whole word/phrase."""
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(k.lower())}\b", lowered) for k in keywords)
