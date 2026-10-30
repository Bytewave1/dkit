"""``dkit components`` - look up Discord Component types."""

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
Look up Discord component types by type number or name, search for matching
component types, or list every known component type.
"""

HINT_ALL = "run 'dkit components --list' to list every known component type"


def component_types() -> list[dict[str, str]]:
    """Return component types from ``dkit/data/component_types.json``."""
    components = data.load("component_types")

    return [
        {
            "type": component_type["type"],
            "name": component_type["name"],
            "description": component_type["description"],
            "style": component_type["style"],
            "usage": component_type["usage"],
        }
        for component_type in components["types"]
    ]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit components``."""
    parser.add_argument(
        "value",
        metavar="TYPE",
        nargs="?",
        help="a component type number (e.g. 2) or name (e.g. Button)",
    )

    parser.add_argument(
        "--search",
        metavar="TEXT",
        help=(
            "list components whose type, name, description, style, or usage contains TEXT "
            "(case-insensitive)"
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="list all component types",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit components``."""

    entries = component_types()
    if args.list:
        if args.value is not None:
            raise UsageError(
                "a component type cannot be combined with --list",
                hint="run 'dkit components --list' or look up one component, not both",
            )
        if args.search is not None:
            raise UsageError(
                "--list cannot be combined with --search",
                hint="run 'dkit components --list' or search by text, not both",
            )

        _render_all(out, entries)

        return {
            "mode": "all",
            "count": len(entries),
            "component_types": [dict(entry) for entry in entries],
            "source": data.provenance("component_types"),
        }

    if args.value is not None and args.search is not None:
        raise UsageError(
            "a component type cannot be combined with --search",
            hint="look up one component or search for matching components, not both",
        )

    if args.search is not None:
        query = args.search.strip()

        if not query:
            raise UsageError(
                "no search text given",
                hint="example: dkit components --search Interactive",
            )

        matches = _search(query, entries)

        _render_all(out, matches)

        return {
            "mode": "search",
            "query": query,
            "count": len(matches),
            "types": matches,
            "source": data.provenance("component_types"),
        }

    if args.value is None:
        raise UsageError(
            "no component type given",
            hint=HINT_ALL,
        )

    raw = args.value.strip()

    if looks_like_int(raw):
        int_val = parse_int(raw, what="component type")
        str_val = str(int_val)

        for entry in entries:
            if entry["type"] == str_val:
                _render_one(out, entry)

                return {
                    "mode": "lookup",
                    **entry,
                    "source": data.provenance("component_types"),
                }

        raise UsageError(
            f"unknown component type number: {raw!r}",
            hint=HINT_ALL,
        )

    norm = normalise_name(raw)

    for entry in entries:
        if normalise_name(entry["name"]) == norm:
            _render_one(out, entry)

            return {
                "mode": "lookup",
                **entry,
                "source": data.provenance("component_types"),
            }

    known_names = [entry["name"] for entry in entries]

    hint = suggestion_hint(raw, known_names) or HINT_ALL

    raise UsageError(
        f"unknown component type: {raw!r}",
        hint=hint,
    )


def _search(
    query: str,
    entries: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Return entries containing ``query`` with case-insensitive matching."""
    needle = query.casefold()
    return [
        entry
        for entry in entries
        if any(
            needle in entry[field].casefold()
            for field in ("type", "name", "description", "style", "usage")
        )
    ]


def _render_one(out: Printer, entry: dict[str, str]) -> None:
    """Render a single component type."""
    out.heading("Component type")

    out.field(
        "Type",
        out.style(entry["type"], "green", "bold"),
    )

    out.field("Name", entry["name"])
    out.field("Description", entry["description"])
    out.field("Style", entry["style"])
    out.field("Usage", entry["usage"])


def _render_all(
    out: Printer,
    entries: list[dict[str, str]],
) -> None:
    """Render every component type in tabular form."""
    out.heading(f"Component types ({len(entries)})")

    type_width = max(
        (len(entry["type"]) for entry in entries),
        default=0,
    )

    name_width = max(
        (len(entry["name"]) for entry in entries),
        default=0,
    )

    for entry in entries:
        type_str = entry["type"].rjust(type_width)
        name = entry["name"]
        padding = " " * (name_width - len(name))

        styled_name = out.style(name, "green")

        out.line(f"  {type_str}  {styled_name}{padding}  {entry['description']}")


COMMAND = Command(
    name="components",
    help="look up Discord component types",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit components --list\n"
        "  dkit components 1\n"
        "  dkit components Button\n"
        "  dkit components --search Interactive"
    ),
)
