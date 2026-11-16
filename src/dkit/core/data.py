"""Access to the bundled JSON data files.

Every Discord constant dkit knows about lives in ``dkit/data/*.json`` so that
updating a value never means touching logic. Each file carries a ``source``
URL and a ``last_verified`` date.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

DATA_PACKAGE = "dkit.data"

#: Data files shipped with dkit, without the ``.json`` suffix.
DATASETS = (
    "snowflake",
    "permissions",
    "intents",
    "oauth2",
    "timestamp_styles",
    "locales",
    "channel_types",
    "user_flags",
    "error_codes",
    "scheduled_event_types",
    "component_types",
)


@cache
def load(name: str) -> dict[str, Any]:
    """Return the parsed contents of ``dkit/data/<name>.json``.

    Results are cached, so callers may treat the returned mapping as
    read-only shared state.
    """
    resource = resources.files(DATA_PACKAGE).joinpath(f"{name}.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def provenance(name: str) -> dict[str, Any]:
    """Return the ``source``/``last_verified`` metadata of a data file."""
    data = load(name)
    return {
        "source": data.get("source"),
        "source_rendered": data.get("source_rendered"),
        "last_verified": data.get("last_verified"),
    }
