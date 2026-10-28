"""``dkit scheduled-events`` - look up Discord guild scheduled event enums."""

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
Look up the enums of Discord guild scheduled events: entity types, privacy
levels and statuses. The integers overlap between groups (2 is VOICE, GUILD_ONLY
and ACTIVE), so the group must always be named: entity, privacy or status.
These are plain enums, not bitfields. Use --transitions to see which status
changes Discord documents as valid.
"""

HINT_ALL = "run 'dkit scheduled-events' to list every group"


def groups() -> dict[str, dict[str, Any]]:
    """The enum groups from ``dkit/data/scheduled_event_types.json``."""
    return dict(data.load("scheduled_event_types")["groups"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit scheduled-events``."""
    parser.add_argument(
        "group",
        metavar="GROUP",
        nargs="?",
        help="entity, privacy or status",
    )
    parser.add_argument(
        "value",
        metavar="VALUE",
        nargs="?",
        help="an integer (e.g. 4) or a name (e.g. CANCELED) within GROUP",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="list the values of GROUP whose name or description contains TEXT",
    )
    parser.add_argument(
        "--transitions",
        action="store_true",
        help="show the documented status transitions",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit scheduled-events``."""
    if args.transitions:
        if args.group is not None or args.value is not None or args.search is not None:
            raise UsageError(
                "--transitions cannot be combined with a group, a value or --search",
                hint="run 'dkit scheduled-events --transitions' on its own",
            )
        return _transitions(out)

    if args.value is not None and args.search is not None:
        raise UsageError(
            "a value cannot be combined with --search",
            hint="look up one value, or search a group, but not both",
        )

    if args.group is None:
        if args.search is not None:
            raise UsageError(
                "--search needs a group",
                hint="example: dkit scheduled-events status --search act",
            )
        return _all(out)

    key, group = _resolve_group(args.group)
    title = group["title"]
    values = group["values"]

    if args.search is not None:
        query = args.search.strip()
        if not query:
            raise UsageError(
                "no search text given",
                hint="example: dkit scheduled-events status --search act",
            )
        matches = [entry for entry in values if _matches(entry, query)]
        _render_values(out, f"{title} values matching {query!r}", matches)
        return {
            "mode": "search",
            "group": key,
            "query": query,
            "count": len(matches),
            "values": [dict(entry) for entry in matches],
            "source": data.provenance("scheduled_event_types"),
        }

    if args.value is None:
        _render_values(out, title, values)
        return {
            "mode": "group",
            "group": key,
            "count": len(values),
            "values": [dict(entry) for entry in values],
            "source": data.provenance("scheduled_event_types"),
        }

    entry = _lookup(key, title, values, args.value)
    _render_one(out, title, entry)
    return {
        "mode": "lookup",
        "group": key,
        **entry,
        "source": data.provenance("scheduled_event_types"),
    }


def _resolve_group(raw: str) -> tuple[str, dict[str, Any]]:
    """Return the key and data of the group named ``raw``, or raise a usage error."""
    available = groups()
    key = raw.strip().casefold()
    if key not in available:
        hint = suggestion_hint(key, list(available)) or HINT_ALL
        raise UsageError(f"unknown scheduled event group: {raw!r}", hint=hint)
    return key, available[key]


def _lookup(key: str, title: str, values: list[dict[str, Any]], raw: str) -> dict[str, Any]:
    """Find one value of a group by integer or by name."""
    text = raw.strip()
    hint = f"run 'dkit scheduled-events {key}' to list the values of this group"
    if looks_like_int(text):
        number = parse_int(text, what=title.lower())
        for entry in values:
            if entry["value"] == number:
                return entry
        raise UsageError(f"unknown {title.lower()} integer: {raw!r}", hint=hint)

    norm = normalise_name(text)
    for entry in values:
        if entry["name"] == norm:
            return entry
    names = [entry["name"] for entry in values]
    raise UsageError(
        f"unknown {title.lower()}: {raw!r}",
        hint=suggestion_hint(norm, names) or hint,
    )


def _matches(entry: dict[str, Any], query: str) -> bool:
    """Case-insensitive match of ``query`` against a value's name and description."""
    needle = query.casefold()
    return needle in entry["name"].casefold() or needle in (entry["description"] or "").casefold()


def _transitions(out: Printer) -> dict[str, Any]:
    """Render the documented status transitions."""
    dataset = data.load("scheduled_event_types")
    transitions = [dict(item) for item in dataset["status_transitions"]]
    terminal = [entry["name"] for entry in groups()["status"]["values"] if entry["terminal"]]
    out.heading(f"Valid status transitions ({len(transitions)})")
    for item in transitions:
        out.line(f"  {item['from']} -> {item['to']}")
    out.line("")
    out.line(f"  {dataset['status_note']}")
    return {
        "mode": "transitions",
        "count": len(transitions),
        "transitions": transitions,
        "terminal": terminal,
        "note": dataset["status_note"],
        "source": data.provenance("scheduled_event_types"),
    }


def _all(out: Printer) -> dict[str, Any]:
    """Render every group."""
    available = groups()
    for group in available.values():
        _render_values(out, group["title"], group["values"])
    return {
        "mode": "all",
        "groups": {
            key: {"title": group["title"], "values": [dict(entry) for entry in group["values"]]}
            for key, group in available.items()
        },
        "source": data.provenance("scheduled_event_types"),
    }


def _render_one(out: Printer, title: str, entry: dict[str, Any]) -> None:
    """Render a single value."""
    out.heading(title)
    out.field("Name", out.style(entry["name"], "green", "bold"))
    out.field("Value", entry["value"])
    if entry["description"] is not None:
        out.field("Description", entry["description"])
    if entry.get("terminal"):
        out.field("Final", "yes, the status can no longer be updated")


def _render_values(out: Printer, title: str, entries: list[dict[str, Any]]) -> None:
    """Render a list of values of one group."""
    out.heading(f"{title} ({len(entries)})")
    name_width = max((len(entry["name"]) for entry in entries), default=0)
    for entry in entries:
        padding = " " * (name_width - len(entry["name"]))
        line = f"  {entry['value']:>2}  {out.style(entry['name'], 'green')}"
        if entry["description"] is not None:
            line += f"{padding}  {entry['description']}"
        elif entry.get("terminal"):
            line += f"{padding}  (final)"
        out.line(line)


COMMAND = Command(
    name="scheduled-events",
    help="look up Discord scheduled event types, privacy levels and statuses",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit scheduled-events\n"
        "  dkit scheduled-events entity EXTERNAL\n"
        "  dkit scheduled-events status 4\n"
        "  dkit scheduled-events status --search act\n"
        "  dkit scheduled-events --transitions\n"
        "  dkit --json scheduled-events status\n"
    ),
)
