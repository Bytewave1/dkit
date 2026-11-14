"""``dkit stickers`` - look up Discord sticker enums."""

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
Look up the enums of Discord stickers: sticker types and sticker format
types. The integers overlap between groups (1 is STANDARD and PNG), so the
group must always be named: type or format. These are plain enums, not
bitfields.
"""

HINT_ALL = "run 'dkit stickers' to list every group"


def groups() -> dict[str, dict[str, Any]]:
    """The enum groups from ``dkit/data/sticker_types.json``."""
    return dict(data.load("sticker_types")["groups"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit stickers``."""
    parser.add_argument(
        "group",
        metavar="GROUP",
        nargs="?",
        help="type or format",
    )
    parser.add_argument(
        "value",
        metavar="VALUE",
        nargs="?",
        help="an integer (e.g. 2) or a name (e.g. GUILD) within GROUP",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="list the values of GROUP whose name or description contains TEXT",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit stickers``."""
    if args.value is not None and args.search is not None:
        raise UsageError(
            "a value cannot be combined with --search",
            hint="look up one value, or search a group, but not both",
        )

    if args.group is None:
        if args.search is not None:
            raise UsageError(
                "--search needs a group",
                hint="example: dkit stickers format --search png",
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
                hint="example: dkit stickers format --search png",
            )
        matches = [entry for entry in values if _matches(entry, query)]
        _render_values(out, f"{title} values matching {query!r}", matches)
        return {
            "mode": "search",
            "group": key,
            "query": query,
            "count": len(matches),
            "values": [dict(entry) for entry in matches],
            "source": data.provenance("sticker_types"),
        }

    if args.value is None:
        _render_values(out, title, values)
        return {
            "mode": "group",
            "group": key,
            "count": len(values),
            "values": [dict(entry) for entry in values],
            "source": data.provenance("sticker_types"),
        }

    entry = _lookup(key, title, values, args.value)
    _render_one(out, title, entry)
    return {
        "mode": "lookup",
        "group": key,
        **entry,
        "source": data.provenance("sticker_types"),
    }


def _resolve_group(raw: str) -> tuple[str, dict[str, Any]]:
    """Return the key and data of the group named ``raw``, or raise a usage error."""
    available = groups()
    key = raw.strip().casefold()
    if key not in available:
        hint = suggestion_hint(key, list(available)) or HINT_ALL
        raise UsageError(f"unknown sticker group: {raw!r}", hint=hint)
    return key, available[key]


def _lookup(key: str, title: str, values: list[dict[str, Any]], raw: str) -> dict[str, Any]:
    """Find one value of a group by integer or by name."""
    text = raw.strip()
    hint = f"run 'dkit stickers {key}' to list the values of this group"
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
        "source": data.provenance("sticker_types"),
    }


def _render_one(out: Printer, title: str, entry: dict[str, Any]) -> None:
    """Render a single value."""
    out.heading(title)
    out.field("Name", out.style(entry["name"], "green", "bold"))
    out.field("Value", entry["value"])
    if entry["description"] is not None:
        out.field("Description", entry["description"])


def _render_values(out: Printer, title: str, entries: list[dict[str, Any]]) -> None:
    """Render a list of values of one group."""
    out.heading(f"{title} ({len(entries)})")
    name_width = max((len(entry["name"]) for entry in entries), default=0)
    for entry in entries:
        padding = " " * (name_width - len(entry["name"]))
        line = f"  {entry['value']:>2}  {out.style(entry['name'], 'green')}"
        if entry["description"] is not None:
            line += f"{padding}  {entry['description']}"
        out.line(line)


COMMAND = Command(
    name="stickers",
    help="look up Discord sticker types and format types",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit stickers\n"
        "  dkit stickers format 3\n"
        "  dkit stickers type GUILD\n"
        "  dkit stickers format --search png\n"
        "  dkit --json stickers type\n"
    ),
)
