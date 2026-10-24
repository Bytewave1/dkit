"""``dkit errors`` - look up Discord HTTP and JSON error codes."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command

DESCRIPTION = """\
Look up an HTTP status code or Discord JSON error code, or list every known
code. Use --search to find matching types, codes, or descriptions with exact,
case-sensitive text.
HTTP codes include entries such as 404 and 5xx.
"""


def error_codes() -> list[dict[str, str]]:
    """Return HTTP and JSON error codes from ``dkit/data/error_codes.json``."""
    codes = data.load("error_codes")
    return [
        {"type": code_type, "code": code, "description": description}
        for code_type in ("http", "json")
        for code, description in codes[f"{code_type}_codes"].items()
    ]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit errors``."""
    parser.add_argument(
        "value",
        metavar="CODE",
        nargs="?",
        help="an HTTP status code or Discord JSON error code",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="list codes whose type, code, or description contains TEXT (case-sensitive)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit errors``."""
    if args.value is not None and args.search is not None:
        raise UsageError(
            "an error code cannot be combined with --search",
            hint="look up one code, or search for matching codes, but not both",
        )

    entries = error_codes()
    if args.search is not None:
        query = args.search.strip()
        if not query:
            raise UsageError(
                "no search text given", hint="example: dkit errors --search permissions"
            )
        matches = _search(query, entries)
        _render_all(out, matches, title=f"Discord error codes matching {query!r}")
        return {
            "mode": "search",
            "query": query,
            "count": len(matches),
            "error_codes": matches,
            "source": data.provenance("error_codes"),
        }

    if args.value is None:
        _render_all(out, entries)
        return {
            "mode": "all",
            "count": len(entries),
            "error_codes": entries,
            "source": data.provenance("error_codes"),
        }

    query = args.value.strip()
    match = next((entry for entry in entries if entry["code"].casefold() == query.casefold()), None)
    if match is None:
        raise UsageError(
            f"unknown Discord error code: {query!r}",
            hint="run 'dkit errors' to list every known HTTP and JSON error code",
        )

    _render_one(out, match)
    return {
        "mode": "lookup",
        **match,
        "source": data.provenance("error_codes"),
    }


def _search(query: str, entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return entries containing ``query`` with case-sensitive matching."""
    return [
        entry
        for entry in entries
        if any(query in entry[field] for field in ("type", "code", "description"))
    ]


def _render_one(out: Printer, entry: dict[str, str]) -> None:
    """Render one HTTP or JSON error code."""
    out.heading("Discord error code")
    out.field("Type", entry["type"].upper())
    out.field("Code", out.style(entry["code"], "green", "bold"))
    out.field("Description", entry["description"])


def _render_all(
    out: Printer, entries: list[dict[str, str]], *, title: str = "Discord error codes"
) -> None:
    """Render every known HTTP and JSON error code."""
    out.heading(f"{title} ({len(entries)})")
    code_width = max((len(entry["code"]) for entry in entries), default=0)
    for entry in entries:
        code = entry["code"]
        padding = " " * (code_width - len(code))
        out.line(
            f"  {out.style(code, 'green')}{padding}  "
            f"{entry['type'].upper():4}  {entry['description']}"
        )


COMMAND = Command(
    name="errors",
    help="look up Discord HTTP and JSON error codes",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n  dkit errors\n  dkit errors 404\n  dkit errors 50013\n  dkit errors 5xx\n"
        "  dkit errors --search permissions\n"
    ),
)
