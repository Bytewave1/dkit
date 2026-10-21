"""``dkit channels`` - look up Discord channel types."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import looks_like_int, normalise_name, parse_int
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
Look up Discord channel types by integer value or name, or list every known
channel type. Channel types are an enum (integers 0 to 16), not a bitfield.
"""

HINT_ALL = "run 'dkit channels' to list every known channel type"


def channel_types() -> list[dict[str, Any]]:
    """The channel types from ``dkit/data/channel_types.json``."""
    return list(data.load("channel_types")["channel_types"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit channels``."""
    parser.add_argument(
        "value",
        metavar="TYPE",
        nargs="?",
        help="an integer channel type (e.g. 15) or type name (e.g. GUILD_FORUM)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit channels``."""
    entries = channel_types()

    if args.value is None:
        _render_all(out, entries)
        return {
            "mode": "all",
            "count": len(entries),
            "channel_types": [dict(entry) for entry in entries],
            "source": data.provenance("channel_types"),
        }

    raw = args.value.strip()
    if looks_like_int(raw):
        int_val = parse_int(raw, what="channel type")
        for entry in entries:
            if entry["value"] == int_val:
                _render_one(out, entry)
                return {
                    "mode": "lookup",
                    "name": entry["name"],
                    "value": entry["value"],
                    "description": entry["description"],
                    "source": data.provenance("channel_types"),
                }
        raise UsageError(
            f"unknown channel type integer: {raw!r}",
            hint=HINT_ALL,
        )

    norm = normalise_name(raw)
    for entry in entries:
        if entry["name"] == norm:
            _render_one(out, entry)
            return {
                "mode": "lookup",
                "name": entry["name"],
                "value": entry["value"],
                "description": entry["description"],
                "source": data.provenance("channel_types"),
            }

    known_names = [entry["name"] for entry in entries]
    hint = suggestion_hint(norm, known_names) or HINT_ALL
    raise UsageError(f"unknown channel type: {raw!r}", hint=hint)


def _render_one(out: Printer, entry: dict[str, Any]) -> None:
    """Render a single channel type."""
    out.heading("Channel type")
    out.field("Name", out.style(entry["name"], "green", "bold"))
    out.field("Value", entry["value"])
    out.field("Description", entry["description"])


def _render_all(out: Printer, entries: list[dict[str, Any]]) -> None:
    """Render every channel type in tabular form."""
    out.heading(f"Channel types ({len(entries)})")
    name_width = max((len(entry["name"]) for entry in entries), default=0)
    for entry in entries:
        val_str = f"{entry['value']:>2}"
        name = entry["name"]
        padding = " " * (name_width - len(name))
        styled_name = out.style(name, "green")
        out.line(f"  {val_str}  {styled_name}{padding}  {entry['description']}")


COMMAND = Command(
    name="channels",
    help="look up Discord channel types",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit channels\n"
        "  dkit channels 15\n"
        "  dkit channels GUILD_FORUM\n"
        "  dkit channels --json 15\n"
    ),
)
