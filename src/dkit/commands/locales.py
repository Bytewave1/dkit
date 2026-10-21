"""``dkit locales`` - look up the locale codes Discord accepts."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
List the locale codes Discord accepts for localised command names and
responses. Give a CODE for an exact lookup, or --search to find locales by
language name. Codes are case-sensitive: en-US is valid, en_US and en are not.
"""

NOT_FOUND_HINT = "run 'dkit locales' for every code, or 'dkit locales --search NAME' to search"


def locales() -> list[dict[str, str]]:
    """The locales from ``dkit/data/locales.json``."""
    return list(data.load("locales")["locales"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit locales``."""
    parser.add_argument(
        "value",
        metavar="CODE",
        nargs="?",
        help="a locale code to look up exactly, e.g. de or en-US",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="list locales whose language name contains TEXT (case-insensitive)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit locales``."""
    if args.value is not None and args.search is not None:
        raise UsageError(
            "a locale code cannot be combined with --search",
            hint="look up one code, or search by language name, but not both",
        )

    entries = locales()
    query: str | None = None
    if args.value is not None:
        mode, query, matches = "lookup", args.value, [_lookup(args.value, entries)]
    elif args.search is not None:
        mode, query = "search", args.search.strip()
        matches = _search(query, entries)
    else:
        mode, matches = "all", entries

    _render(out, mode, query, matches)

    return {
        "mode": mode,
        "query": query,
        "count": len(matches),
        "locales": [dict(entry) for entry in matches],
        "source": data.provenance("locales"),
    }


def _lookup(code: str, entries: list[dict[str, str]]) -> dict[str, str]:
    """Return the entry whose code is exactly ``code``."""
    for entry in entries:
        if entry["code"] == code:
            return entry
    raise UsageError(
        f"unknown locale: {code!r}",
        hint=suggestion_hint(code, [entry["code"] for entry in entries]) or NOT_FOUND_HINT,
    )


def _search(text: str, entries: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return the entries whose language name contains ``text``."""
    if not text:
        raise UsageError("no search text given", hint="example: dkit locales --search portug")
    needle = text.casefold()
    return [entry for entry in entries if needle in entry["name"].casefold()]


def _render(out: Printer, mode: str, query: str | None, matches: list[dict[str, str]]) -> None:
    """Print the text output; every call is a no-op in ``--json`` mode."""
    if mode == "lookup":
        entry = matches[0]
        out.heading("Locale")
        out.field("Code", out.style(entry["code"], "green", "bold"))
        out.field("Language", entry["name"])
    else:
        title = "Locales" if mode == "all" else f"Locales matching {query!r}"
        out.heading(f"{title} ({len(matches)})")
        code_width = max((len(entry["code"]) for entry in matches), default=0)
        for entry in matches:
            padding = " " * (code_width - len(entry["code"]))
            out.line(f"  {out.style(entry['code'], 'green')}{padding}  {entry['name']}")
        if not matches:
            out.note("  (no locales match)")

    out.line()
    out.note("  Codes are exact and case-sensitive: en-US, not en_US or en.")
    out.note(f"  Data comes from the official table (verified {_verified()}).")


def _verified() -> str:
    return str(data.provenance("locales")["last_verified"])


COMMAND = Command(
    name="locales",
    help="look up Discord locale codes",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=("examples:\n  dkit locales\n  dkit locales de\n  dkit locales --search portug\n"),
)
