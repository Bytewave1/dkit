"""``dkit guild-levels`` - look up Discord guild configuration levels."""

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
Look up Discord guild configuration levels: verification, default message
notifications, explicit content filtering, MFA, premium tier and age restriction.
The integers overlap between groups, so always name the group. Values can be
looked up by integer or name, and each group can be listed or searched.
"""

HINT_ALL = "run 'dkit guild-levels' to list every group"


def groups() -> dict[str, dict[str, Any]]:
    """The enum groups from ``dkit/data/guild_levels.json``."""
    return dict(data.load("guild_levels")["groups"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit guild-levels``."""
    parser.add_argument(
        "group",
        metavar="GROUP",
        nargs="?",
        help=("verification, notifications, content-filter, mfa, premium-tier or age-restriction"),
    )
    parser.add_argument(
        "value",
        metavar="VALUE",
        nargs="?",
        help="an integer (e.g. 3) or a name (e.g. HIGH) within GROUP",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="list the values of GROUP whose name or description contains TEXT",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit guild-levels``."""
    if args.value is not None and args.search is not None:
        raise UsageError(
            "a value cannot be combined with --search",
            hint="look up one value, or search a group, but not both",
        )

    if args.group is None:
        if args.search is not None:
            raise UsageError(
                "--search needs a group",
                hint="example: dkit guild-levels verification --search phone",
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
                hint="example: dkit guild-levels verification --search phone",
            )
        matches = [entry for entry in values if _matches(entry, query)]
        _render_values(out, f"{title} values matching {query!r}", matches)
        return {
            "mode": "search",
            "group": key,
            "query": query,
            "count": len(matches),
            "values": [dict(entry) for entry in matches],
            "source": data.provenance("guild_levels"),
        }

    if args.value is None:
        _render_values(out, title, values)
        return {
            "mode": "group",
            "group": key,
            "count": len(values),
            "values": [dict(entry) for entry in values],
            "source": data.provenance("guild_levels"),
        }

    entry = _lookup(key, title, values, args.value)
    _render_one(out, title, entry)
    return {
        "mode": "lookup",
        "group": key,
        **entry,
        "source": data.provenance("guild_levels"),
    }


def _resolve_group(raw: str) -> tuple[str, dict[str, Any]]:
    """Return the key and data of the group named raw, or raise a usage error."""
    available = groups()
    key = raw.strip().casefold().replace("_", "-")
    if key not in available:
        hint = suggestion_hint(key, list(available), limit=1) or HINT_ALL
        raise UsageError(f"unknown guild level group: {raw!r}", hint=hint)
    return key, available[key]


def _lookup(key: str, title: str, values: list[dict[str, Any]], raw: str) -> dict[str, Any]:
    """Find one value of a group by integer or by name."""
    text = raw.strip()
    hint = f"run 'dkit guild-levels {key}' to list the values of this group"
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
        hint=suggestion_hint(norm, names, limit=1) or hint,
    )


def _matches(entry: dict[str, Any], query: str) -> bool:
    """Case-insensitive match against a value name or its optional description."""
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
            key: {
                "title": group["title"],
                "values": [dict(entry) for entry in group["values"]],
            }
            for key, group in available.items()
        },
        "source": data.provenance("guild_levels"),
    }


def _render_one(out: Printer, title: str, entry: dict[str, Any]) -> None:
    """Render a single value."""
    out.heading(title)
    out.field("Name", out.style(entry["name"], "green", "bold"))
    out.field("Value", entry["value"])
    if entry["description"] is not None:
        out.field("Description", entry["description"])


def _render_values(out: Printer, title: str, entries: list[dict[str, Any]]) -> None:
    """Render a list of values."""
    out.heading(f"{title} ({len(entries)})")
    name_width = max((len(entry["name"]) for entry in entries), default=0)
    for entry in entries:
        padding = " " * (name_width - len(entry["name"]))
        line = f"  {entry['value']:>2}  {out.style(entry['name'], 'green')}"
        if entry["description"] is not None:
            line += f"{padding}  {entry['description']}"
        out.line(line)


COMMAND = Command(
    name="guild-levels",
    help="look up Discord guild configuration levels",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit guild-levels\n"
        "  dkit guild-levels verification 3\n"
        "  dkit guild-levels premium-tier TIER_2\n"
        "  dkit guild-levels verification --search phone\n"
        "  dkit --json guild-levels mfa\n"
    ),
)
