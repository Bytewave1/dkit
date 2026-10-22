"""``dkit scopes`` - look up Discord OAuth2 scopes."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
List every OAuth2 scope Discord supports, or look one up by name. Scopes marked
[approval] are only available to approved partners: requesting them without
Discord's approval may cause errors or undocumented behavior in the OAuth2
flow. Scope names are lowercase and exact: identify and guilds.members.read
are valid, Identify is not.
"""

NOT_FOUND_HINT = "run 'dkit scopes' for every scope, or 'dkit scopes --search TEXT'"


def scopes() -> list[dict[str, Any]]:
    """The OAuth2 scopes from ``dkit/data/oauth2.json``."""
    return list(data.load("oauth2")["scopes"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit scopes``."""
    parser.add_argument(
        "value",
        metavar="SCOPE",
        nargs="?",
        help="a scope name to look up exactly, e.g. identify",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="list scopes whose name or description contains TEXT (case-insensitive)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit scopes``."""
    if args.value is not None and args.search is not None:
        raise UsageError(
            "a scope name cannot be combined with --search",
            hint="look up one scope, or search by text, but not both",
        )

    entries = scopes()
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
        "scopes": [dict(entry) for entry in matches],
        "source": data.provenance("oauth2"),
    }


def _lookup(scope: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the entry whose name is exactly ``scope``."""
    for entry in entries:
        if entry["name"] == scope:
            return entry
    raise UsageError(
        f"unknown OAuth2 scope: {scope!r}",
        hint=suggestion_hint(scope, [entry["name"] for entry in entries]) or NOT_FOUND_HINT,
    )


def _search(text: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the entries whose name or description contains ``text``."""
    if not text:
        raise UsageError("no search text given", hint="example: dkit scopes --search voice")
    needle = text.casefold()
    return [
        entry
        for entry in entries
        if needle in entry["name"].casefold() or needle in entry["description"].casefold()
    ]


def _render(out: Printer, mode: str, query: str | None, matches: list[dict[str, Any]]) -> None:
    """Print the text output; every call is a no-op in ``--json`` mode."""
    if mode == "lookup":
        entry = matches[0]
        out.heading("OAuth2 scope")
        out.field("Name", out.style(entry["name"], "green", "bold"))
        out.field("Description", entry["description"])
        if entry.get("approval_required"):
            out.field("Approval", out.style("required from Discord", "yellow"))
    else:
        title = "OAuth2 scopes" if mode == "all" else f"OAuth2 scopes matching {query!r}"
        out.heading(f"{title} ({len(matches)})")
        name_width = max((len(entry["name"]) for entry in matches), default=0)
        for entry in matches:
            padding = " " * (name_width - len(entry["name"]))
            marker = out.style("  [approval]", "yellow") if entry.get("approval_required") else ""
            out.line(
                f"  {out.style(entry['name'], 'green')}{padding}  {entry['description']}{marker}"
            )
        if not matches:
            out.note("  (no scopes match)")

    out.line()
    out.note("  Scope names are lowercase and exact.")
    out.note("  [approval] = only available to approved partners.")
    verified = data.provenance("oauth2")["last_verified"]
    out.note(f"  Data comes from the official table (verified {verified}).")


COMMAND = Command(
    name="scopes",
    help="list and look up Discord OAuth2 scopes",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit scopes\n"
        "  dkit scopes identify\n"
        "  dkit scopes guilds.j\n"
        "  dkit scopes --search voice\n"
        "  dkit --json scopes\n"
    ),
)
