"""'Did you mean ...?' suggestions for mistyped names."""

from __future__ import annotations

from collections.abc import Iterable
from difflib import get_close_matches


def did_you_mean(value: str, candidates: Iterable[str], *, limit: int = 3) -> list[str]:
    """Return up to ``limit`` candidates that look like ``value``.

    Matching is case-insensitive and also catches names that merely contain
    the typed text, which ``difflib`` alone tends to miss for short inputs
    (for example ``ROLES`` -> ``MANAGE_ROLES``).
    """
    options = list(candidates)
    needle = value.upper()
    folded = {name.upper(): name for name in options}

    matches = [folded[m] for m in get_close_matches(needle, folded, n=limit, cutoff=0.6)]

    if len(matches) < limit:
        substring = [
            name for name in options if needle and needle in name.upper() and name not in matches
        ]
        matches.extend(sorted(substring, key=len)[: limit - len(matches)])

    return matches[:limit]


def suggestion_hint(value: str, candidates: Iterable[str], *, limit: int = 3) -> str | None:
    """Format a ready-to-print 'did you mean' line, or ``None`` if nothing fits."""
    matches = did_you_mean(value, candidates, limit=limit)
    if not matches:
        return None
    if len(matches) == 1:
        return f"did you mean {matches[0]}?"
    return "did you mean " + ", ".join(matches[:-1]) + f" or {matches[-1]}?"
