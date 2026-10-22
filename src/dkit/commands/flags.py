"""``dkit flags`` - decode Discord user flags (profile badges) into names."""

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
Translate the public_flags / flags integer of a Discord user into the profile
badge names it contains, or combine badge names back into the integer. Unknown
bits are reported instead of dropped: a set bit with no name usually means
Discord added a badge since dkit's data was last verified.
"""


def user_flags() -> FlagSet:
    """The user flags from ``dkit/data/user_flags.json``."""
    entries = data.load("user_flags")["user_flags"]
    return FlagSet(
        (
            Flag(
                name=entry["name"],
                bit=entry["bit"],
                description=entry.get("description", ""),
            )
            for entry in entries
        ),
        label="user flag",
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit flags``."""
    parser.add_argument(
        "value",
        metavar="NUMBER",
        nargs="?",
        help="a public_flags integer to decode into badge names (e.g. 4194304)",
    )
    parser.add_argument(
        "--names",
        metavar="NAMES",
        help="comma-separated user flag names (VERIFIED_BOT,STAFF) to combine into the integer",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit flags``."""
    flags = user_flags()

    if args.names is not None:
        if args.value is not None:
            raise UsageError(
                "--names cannot be combined with NUMBER",
                hint="decode a number or combine names, but not both",
            )
        names = split_names(args.names)
        if not names:
            raise UsageError(
                "--names did not contain any user flag names",
                hint="example: dkit flags --names VERIFIED_BOT,STAFF",
            )
        value = flags.value_of(names)
        direction = "names-to-number"
    elif args.value is not None:
        raw = args.value.strip()
        if not looks_like_int(raw):
            raise UsageError(
                f"user flags value is not a valid integer: {raw!r}",
                hint="pass badge names with --names, e.g. dkit flags --names VERIFIED_BOT",
            )
        value = parse_int(raw, what="user flags value")
        direction = "number-to-names"
    else:
        raise UsageError(
            "no user flags given",
            hint="examples: dkit flags 4194304 | dkit flags --names VERIFIED_BOT,STAFF",
        )

    return _render_result(value, direction, flags, out)


def _render_result(value: int, direction: str, flags: FlagSet, out: Printer) -> dict[str, Any]:
    matched = flags.flags_in(value)
    warnings: list[str] = []
    unknown = flags.unknown_bits(value)
    if unknown:
        warnings.append(
            "value contains bits dkit has no name for: "
            + ", ".join(str(bit) for bit in unknown)
            + f" (data last verified {data.provenance('user_flags')['last_verified']})"
        )

    out.heading(f"User flags {out.style(str(value), 'green', 'bold')}")
    out.note(f"  hex {value:#06x}  ({len(matched)} of {len(flags)} known user flags)")
    out.line()
    if matched:
        for flag in matched:
            row = f"  {out.style(flag.name.ljust(28), 'green')} 1 << {flag.bit:<3}"
            if flag.description:
                row += f"  {flag.description}"
            out.line(row.rstrip())
    else:
        out.note("  (no user flags set)")

    out.warnings(warnings)

    return {
        "direction": direction,
        "value": str(value),
        "value_int": value,
        "hex": f"0x{value:04x}",
        "bit_count": len(matched),
        "user_flags": [flag.as_dict() for flag in matched],
        "names": [flag.name for flag in matched],
        "unknown_bits": unknown,
        "warnings": warnings,
        "source": data.provenance("user_flags"),
    }


COMMAND = Command(
    name="flags",
    help="decode a user's public_flags integer into badge names and back",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit flags 4194304\n"
        "  dkit flags 0x400000\n"
        "  dkit flags --names VERIFIED_BOT,STAFF\n"
        "  dkit --json flags 131072\n"
    ),
)
