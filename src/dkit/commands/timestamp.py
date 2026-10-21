"""``dkit timestamp`` - format a timestamp as a Discord ``<t:...>`` tag."""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from typing import Any

from dkit.commands.snowflake import decode, parse_snowflake
from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import format_datetime, parse_datetime
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
Turn an ISO-8601 timestamp, or the creation time of a snowflake ID, into the
Discord <t:UNIX:STYLE> tags that render as a localised date or time. Without
--style every documented style is printed; styles are case-sensitive.
"""


def timestamp_styles() -> list[dict[str, Any]]:
    """The timestamp styles from ``dkit/data/timestamp_styles.json``."""
    return list(data.load("timestamp_styles")["styles"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit timestamp``."""
    parser.add_argument(
        "value",
        metavar="TIMESTAMP",
        nargs="?",
        help=(
            "an ISO-8601 timestamp to format, or 'now' for the current time, "
            "e.g. 2026-10-20T08:30:00Z"
        ),
    )
    parser.add_argument(
        "--style",
        metavar="STYLE",
        help="print one style only: t, T, d, D, f, F, s, S or R",
    )
    parser.add_argument(
        "--from-snowflake",
        metavar="ID",
        help="use the creation time of a snowflake ID instead of TIMESTAMP",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit timestamp``."""
    if args.from_snowflake is not None and args.value is not None:
        raise UsageError(
            "--from-snowflake cannot be combined with a timestamp",
            hint="format a timestamp, or use a snowflake's creation time, but not both",
        )
    if args.from_snowflake is None and args.value is None:
        raise UsageError(
            "no timestamp given",
            hint=(
                "examples: dkit timestamp now | "
                "dkit timestamp 2026-10-20T08:30:00Z | "
                "dkit timestamp --from-snowflake 175928847299117063"
            ),
        )

    moment = _moment(args)
    seconds = math.floor(moment.timestamp())
    styles = _select_styles(args.style)

    out.heading(f"Timestamp {out.style(format_datetime(moment), 'green', 'bold')}")
    out.field("Unix", str(seconds))
    out.line()
    for entry in styles:
        tag = f"<t:{seconds}:{entry['style']}>"
        out.line(
            f"  {out.style(tag.ljust(18), 'green')} {entry['name']}"
            f"  {out.style(entry['example'], 'dim')}"
        )
    out.line()
    out.note("  Discord renders these tags in the viewer's locale and timezone.")
    out.note(f"  Examples come from the official table (verified {_verified()}).")

    return {
        "timestamp": format_datetime(moment),
        "unix": seconds,
        "styles": [
            {
                "style": entry["style"],
                "name": entry["name"],
                "tag": f"<t:{seconds}:{entry['style']}>",
                "example": entry["example"],
            }
            for entry in styles
        ],
        "source": data.provenance("timestamp_styles"),
    }


def _current_time() -> datetime:
    """Return the current UTC time truncated to whole seconds."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def _moment(args: argparse.Namespace) -> datetime:
    """Resolve TIMESTAMP or --from-snowflake into a UTC datetime."""
    if args.from_snowflake is not None:
        decoded = decode(parse_snowflake(args.from_snowflake))
        return datetime.fromtimestamp(decoded["unix_ms"] / 1000, tz=timezone.utc)
    if args.value is not None and args.value.strip().lower() == "now":
        return _current_time()
    return parse_datetime(args.value, what="timestamp")


def _select_styles(style: str | None) -> list[dict[str, Any]]:
    """Return every style, or the single requested one."""
    styles = timestamp_styles()
    if style is None:
        return styles

    known = [entry["style"] for entry in styles]
    for entry in styles:
        if entry["style"] == style:
            return [entry]
    raise UsageError(
        f"unknown timestamp style: {style!r}",
        hint=suggestion_hint(style, known) or f"valid styles: {', '.join(known)}",
    )


def _verified() -> str:
    return str(data.provenance("timestamp_styles")["last_verified"])


COMMAND = Command(
    name="timestamp",
    help="format a timestamp as a Discord <t:...> tag",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit timestamp now\n"
        "  dkit timestamp now --style R\n"
        "  dkit timestamp 2026-10-20T08:30:00Z\n"
        "  dkit timestamp 2026-10-20T08:30:00Z --style R\n"
        "  dkit timestamp --from-snowflake 175928847299117063\n"
    ),
)
