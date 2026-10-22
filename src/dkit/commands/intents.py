"""``dkit intents`` - translate between gateway intent names and the integer."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.bits import Flag, FlagSet
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import looks_like_int, parse_int, split_names
from dkit.core.registry import Command

DESCRIPTION = """\
Convert gateway intent names into the integer passed in the IDENTIFY payload,
or decode such an integer back into names. Privileged intents are called out,
because they must be enabled in the Discord Developer Portal first.
"""


def intent_flags() -> FlagSet:
    """The gateway intents from ``dkit/data/intents.json``."""
    entries = data.load("intents")["intents"]
    return FlagSet(
        (
            Flag(
                name=entry["name"],
                bit=entry["bit"],
                privileged=entry.get("privileged", False),
                events=tuple(entry.get("events", ())),
            )
            for entry in entries
        ),
        label="intent",
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit intents``."""
    parser.add_argument(
        "value",
        metavar="NAMES|NUMBER",
        nargs="?",
        help=("comma-separated intent names (GUILDS,GUILD_MESSAGES) or an intents integer (33280)"),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list every known gateway intent with its bit value",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit intents``."""
    if args.list:
        if args.value is not None:
            raise UsageError(
                "--list cannot be combined with NAMES|NUMBER",
                hint="list every intent, or convert names/a number, but not both",
            )
        return _list(intent_flags(), out)

    flags = intent_flags()
    if args.value is None:
        raise UsageError(
            "no intents given",
            hint=(
                "examples: dkit intents GUILDS,GUILD_MESSAGES | dkit intents 33280"
                " | dkit intents --list"
            ),
        )

    raw = args.value.strip()
    if not raw:
        raise UsageError(
            "no intents given",
            hint=(
                "examples: dkit intents GUILDS,GUILD_MESSAGES | dkit intents 33280"
                " | dkit intents --list"
            ),
        )

    if looks_like_int(raw):
        value = parse_int(raw, what="intents value")
        direction = "number-to-names"
    else:
        names = split_names(raw)
        value = flags.value_of(names)
        direction = "names-to-number"

    matched = flags.flags_in(value)
    privileged = [flag for flag in matched if flag.privileged]
    warnings = _warnings(value, flags, privileged)

    out.heading(f"Intents {out.style(str(value), 'green', 'bold')}")
    out.note(f"  hex {value:#06x}  ({len(matched)} of {len(flags)} known intents)")
    out.line()
    if matched:
        for flag in matched:
            # MESSAGE_CONTENT is the one intent with no associated gateway events.
            summary = f"{len(flag.events)} events" if flag.events else "no events"
            # Pad outside the style so the padding is never part of a color span.
            events = out.style(summary, "dim") + " " * max(0, 9 - len(summary))
            row = f"  {out.style(flag.name.ljust(32), 'green')} 1 << {flag.bit:<3}  {events}"
            if flag.privileged:
                row += out.style("  [privileged]", "yellow")
            out.line(row.rstrip())
    else:
        out.note("  (no intents set)")

    if privileged:
        out.line()
        out.line(out.style("Privileged intents in this value:", "yellow", "bold"))
        for flag in privileged:
            out.line(f"  - {flag.name}")
        out.line()
        for line in _privileged_explanation():
            out.note(f"  {line}")

    out.warnings(warnings)

    return {
        "direction": direction,
        "value": str(value),
        "value_int": value,
        "hex": f"0x{value:04x}",
        "bit_count": len(matched),
        "intents": [flag.as_dict() for flag in matched],
        "names": [flag.name for flag in matched],
        "privileged": [flag.name for flag in privileged],
        "unknown_bits": flags.unknown_bits(value),
        "warnings": warnings,
        "source": data.provenance("intents"),
    }


def _list(flags: FlagSet, out: Printer) -> dict[str, Any]:
    sorted_flags = sorted(flags, key=lambda f: f.bit)

    out.heading(f"Intents ({len(sorted_flags)})")
    out.line()
    for flag in sorted_flags:
        suffix = f"  {out.style('[privileged]', 'yellow')}" if flag.privileged else ""
        bit_str = out.style(f"bit {flag.bit:>2}", "dim")
        out.line(
            f"  {bit_str}  {out.style(flag.name.ljust(36), 'green')} {flag.hex}"
            f"  {flag.value}{suffix}"
        )
    out.line()
    out.note("  Markers: [privileged] = must be enabled in the Developer Portal before IDENTIFY.")
    verified = data.provenance("intents")["last_verified"]
    out.note(f"  Data from the official table (verified {verified}).")

    return {
        "intents": [flag.as_dict() for flag in sorted_flags],
        "total": len(sorted_flags),
        "source": data.provenance("intents"),
    }


def _privileged_explanation() -> list[str]:
    dataset = data.load("intents")
    return [
        "These must be enabled for your application in the Discord Developer Portal",
        f"({dataset['privileged_portal_url']}) under Bot -> Privileged Gateway Intents",
        "before they can be passed in IDENTIFY. Passing one that is not enabled",
        "closes the gateway connection with close code 4014.",
        "Apps above 10,000 users additionally need approval to keep using them.",
    ]


def _warnings(value: int, flags: FlagSet, privileged: list[Flag]) -> list[str]:
    warnings: list[str] = []
    if privileged:
        names = ", ".join(flag.name for flag in privileged)
        warnings.append(
            f"privileged intent(s) {names} must be enabled in the Developer Portal "
            "or the gateway will close the connection with code 4014"
        )
    unknown = flags.unknown_bits(value)
    if unknown:
        warnings.append(
            "value contains bits dkit has no name for: "
            + ", ".join(str(bit) for bit in unknown)
            + f" (data last verified {data.provenance('intents')['last_verified']})"
        )
    return warnings


COMMAND = Command(
    name="intents",
    help="convert gateway intent names to the integer and back",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit intents GUILDS,GUILD_MESSAGES,MESSAGE_CONTENT\n"
        "  dkit intents 33280\n"
        "  dkit intents --list\n"
    ),
)
