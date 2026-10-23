"""``dkit color`` - convert a color between decimal, hex and RGB."""

from __future__ import annotations

import argparse
import re
from typing import Any

from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command

DESCRIPTION = """\
Convert a color between the three forms people use: the decimal integer of a
Discord embed 'color' field, hex (#RRGGBB) and RGB components.

Give a COLOR as #RRGGBB, RRGGBB, 0xRRGGBB, #RGB shorthand or a decimal
integer, or give the channels with --rgb R,G,B. Bare digits are always
decimal: 123456 is the integer 123456, not hex. Write 0x123456 or #123456 for
the hex color. Quote a leading # in your shell.
"""

MAX_COLOR = 0xFFFFFF
INPUT_HINT = "examples: '#5865F2', 5865F2, 0x5865F2, '#58F', 5793266 (bare digits are decimal)"
RGB_HINT = "example: --rgb 88,101,242 (each component is 0-255)"
USAGE_HINT = "examples: dkit color '#5865F2', dkit color 5793266, dkit color --rgb 88,101,242"

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_DECIMAL_DIGITS = frozenset("0123456789")
_CHANNEL = re.compile(r"-?[0-9]+")
_CHANNEL_NAMES = ("red", "green", "blue")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit color``."""
    parser.add_argument(
        "value",
        metavar="COLOR",
        nargs="?",
        help="a color as #RRGGBB, RRGGBB, 0xRRGGBB, #RGB or a decimal integer",
    )
    parser.add_argument(
        "--rgb",
        metavar="R,G,B",
        help="give the color as three 0-255 components instead, e.g. 88,101,242",
    )


def _invalid(text: str) -> UsageError:
    return UsageError(f"not a valid color: {text!r}", hint=INPUT_HINT)


def _from_hex(digits: str, text: str) -> int:
    if not digits or not _HEX_DIGITS.issuperset(digits):
        raise _invalid(text)
    return int(digits, 16)


def parse_color(text: str) -> int:
    """Parse a color given as hex or decimal into its integer value.

    Raises:
        UsageError: if the text is not a color in the range 0..0xFFFFFF.
    """
    raw = text.strip()
    if not raw:
        raise UsageError("color is empty", hint=INPUT_HINT)
    if raw.startswith("-"):
        raise UsageError(f"color must not be negative: {text!r}", hint=INPUT_HINT)

    if raw.startswith("#"):
        digits = raw[1:]
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        if len(digits) != 6:
            raise _invalid(text)
        value = _from_hex(digits, text)
    elif raw[:2].lower() == "0x":
        value = _from_hex(raw[2:], text)
    elif _DECIMAL_DIGITS.issuperset(raw):
        value = int(raw)
    elif len(raw) == 6:
        value = _from_hex(raw, text)
    else:
        raise _invalid(text)

    if value > MAX_COLOR:
        raise UsageError(
            f"color is above 0xFFFFFF ({MAX_COLOR}): {text!r}",
            hint="Discord colors are 24-bit: 0 to 16777215",
        )
    return value


def parse_rgb(text: str) -> tuple[int, int, int]:
    """Parse ``R,G,B`` into three 0-255 components."""
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 3:
        raise UsageError(f"--rgb needs three components R,G,B: {text!r}", hint=RGB_HINT)
    channels: list[int] = []
    for name, part in zip(_CHANNEL_NAMES, parts, strict=True):
        if not _CHANNEL.fullmatch(part):
            raise UsageError(f"{name} component is not a whole number: {part!r}", hint=RGB_HINT)
        channel = int(part)
        if not 0 <= channel <= 255:
            raise UsageError(f"{name} component out of range 0-255: {channel}", hint=RGB_HINT)
        channels.append(channel)
    red, green, blue = channels
    return red, green, blue


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit color``."""
    if args.value is not None and args.rgb is not None:
        raise UsageError(
            "a color cannot be combined with --rgb",
            hint="give one COLOR, or --rgb R,G,B, but not both",
        )
    if args.value is not None:
        value = parse_color(args.value)
    elif args.rgb is not None:
        red, green, blue = parse_rgb(args.rgb)
        value = (red << 16) | (green << 8) | blue
    else:
        raise UsageError("no color given", hint=USAGE_HINT)

    channels = ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)
    hex_text = f"#{value:06X}"
    _render(out, value, hex_text, channels)

    return {
        "integer": value,
        "hex": hex_text,
        "rgb": {"r": channels[0], "g": channels[1], "b": channels[2]},
    }


def _render(out: Printer, value: int, hex_text: str, channels: tuple[int, int, int]) -> None:
    """Print the text output; every call is a no-op in ``--json`` mode."""
    red, green, blue = channels
    out.heading("Color")
    out.field("Integer", str(value))
    out.field("Hex", hex_text)
    out.field("RGB", f"{red}, {green}, {blue}")
    if out.color:
        out.field("Preview", f"\033[48;2;{red};{green};{blue}m      \033[0m")
    out.line()
    out.note("  Use the integer for the embed 'color' field.")


COMMAND = Command(
    name="color",
    help="convert a color between decimal, hex and RGB",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n  dkit color '#5865F2'\n  dkit color 5793266\n  dkit color --rgb 88,101,242\n"
    ),
)
