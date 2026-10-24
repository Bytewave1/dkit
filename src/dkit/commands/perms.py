"""``dkit perms`` - translate between Discord permission integers and names."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.bits import Flag, FlagSet
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import parse_int, split_names
from dkit.core.registry import Command

DESCRIPTION = """\
Decode a Discord permissions integer into permission names, or calculate the
integer for a list of names, or compare two permissions integers with --diff,
or modify an existing integer with --add / --remove.
Permission values exceed 32 bits, so every value is handled as an
arbitrary-precision Python integer.

When both --add and --remove are given, --add is applied first, then --remove.
Adding and removing the same name in one call ends up removed.
"""


def permission_flags() -> FlagSet:
    """The permission flags from ``dkit/data/permissions.json``."""
    entries = data.load("permissions")["permissions"]
    return FlagSet(
        (
            Flag(
                name=entry["name"],
                bit=entry["bit"],
                description=entry["description"],
                requires_2fa=entry.get("requires_2fa", False),
                channel_types=tuple(entry.get("channel_types", ())),
            )
            for entry in entries
        ),
        label="permission",
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit perms``."""
    parser.add_argument(
        "value",
        metavar="NUMBER",
        nargs="?",
        help="a permissions integer to decode, e.g. 2048 or 0x800",
    )
    parser.add_argument(
        "--names",
        metavar="NAMES",
        help="comma-separated permission names to combine into an integer",
    )
    parser.add_argument(
        "--diff",
        metavar="OTHER",
        help="compare NUMBER with a second permissions integer, e.g. 274878286912 or 0x800",
    )
    parser.add_argument(
        "--add",
        metavar="NAMES",
        help="comma-separated permission names to set on NUMBER (applied before --remove)",
    )
    parser.add_argument(
        "--remove",
        metavar="NAMES",
        help="comma-separated permission names to clear from NUMBER (applied after --add)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list every known permission with its bit value",
    )
    parser.add_argument(
        "--channel-type",
        metavar="TYPE",
        help="filter --list by channel type: T (text), V (voice), or S (stage)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit perms``."""
    modifying = args.add is not None or args.remove is not None
    channel_type = args.channel_type
    if channel_type is not None:
        channel_type = channel_type.upper()
        if channel_type not in ("T", "V", "S"):
            raise UsageError(
                f"unknown channel type: {args.channel_type!r}",
                hint="valid values: T (text), V (voice), S (stage)",
            )
        if not args.list:
            raise UsageError(
                "--channel-type can only be used with --list",
                hint="example: dkit perms --list --channel-type S",
            )

    if args.list:
        if args.value is not None:
            raise UsageError(
                "--list cannot be combined with a permissions number",
                hint="list every permission, or decode a number, but not both",
            )
        if args.names is not None:
            raise UsageError(
                "--list cannot be combined with --names",
                hint="list every permission, or encode names, but not both",
            )
        if args.diff is not None:
            raise UsageError(
                "--list cannot be combined with --diff",
                hint="list every permission, or compare two numbers, but not both",
            )
        if modifying:
            raise UsageError(
                "--list cannot be combined with --add or --remove",
                hint="list every permission, or modify a number, but not both",
            )
        return _list(permission_flags(), out, channel_type)

    if modifying and args.names is not None:
        raise UsageError(
            "--add/--remove cannot be combined with --names",
            hint="modify a number, or encode names, but not both at once",
        )
    if modifying and args.diff is not None:
        raise UsageError(
            "--add/--remove cannot be combined with --diff",
            hint="modify a number, or compare two numbers, but not both at once",
        )
    if modifying and args.value is None:
        raise UsageError(
            "--add/--remove need a permissions number to modify",
            hint="example: dkit perms 2048 --add MANAGE_ROLES,KICK_MEMBERS",
        )

    if args.diff is not None and args.names is not None:
        raise UsageError(
            "--diff cannot be combined with --names",
            hint="compare two numbers, or encode names, but not both at once",
        )
    if args.diff is not None and args.value is None:
        raise UsageError(
            "--diff needs a permissions number to compare against",
            hint="example: dkit perms 268437504 --diff 274878286912",
        )
    if args.names and args.value is not None:
        raise UsageError(
            "--names cannot be combined with a permissions number",
            hint="decode a number, or encode names, but not both at once",
        )
    if not args.names and args.value is None:
        raise UsageError(
            "no permissions value given",
            hint=(
                "examples: dkit perms 2048 | dkit perms --names SEND_MESSAGES | dkit perms --list"
            ),
        )

    flags = permission_flags()
    if modifying:
        return _modify(args.value, args.add, args.remove, flags, out)
    if args.diff is not None:
        return _diff(args.value, args.diff, flags, out)
    if args.names:
        return _encode(args.names, flags, out)
    return _decode(args.value, flags, out)


def _render(flag: Flag, out: Printer) -> None:
    marks = []
    if flag.requires_2fa:
        marks.append("2FA")
    if flag.channel_types:
        marks.append("/".join(flag.channel_types))
    suffix = f"  {out.style('[' + ', '.join(marks) + ']', 'dim')}" if marks else ""
    out.line(f"  {out.style(flag.name.ljust(36), 'green')} {flag.hex}{suffix}")


def _summary(value: int, flags: FlagSet) -> list[str]:
    warnings: list[str] = []
    unknown = flags.unknown_bits(value)
    if unknown:
        warnings.append(
            "value contains bits dkit has no name for: "
            + ", ".join(str(bit) for bit in unknown)
            + f" (data last verified {data.provenance('permissions')['last_verified']})"
        )
    if value & flags.resolve("ADMINISTRATOR").value:
        warnings.append("ADMINISTRATOR grants every permission and bypasses channel overwrites")
    return warnings


def _payload(
    value: int, matched: list[Flag], warnings: list[str], flags: FlagSet
) -> dict[str, Any]:
    return {
        "value": str(value),
        "hex": f"0x{value:016x}",
        "bit_count": len(matched),
        "permissions": [flag.as_dict() for flag in matched],
        "names": [flag.name for flag in matched],
        "unknown_bits": flags.unknown_bits(value),
        "warnings": warnings,
        "source": data.provenance("permissions"),
    }


def _decode(raw: str, flags: FlagSet, out: Printer) -> dict[str, Any]:
    value = parse_int(raw, what="permissions value")
    matched = flags.flags_in(value)
    warnings = _summary(value, flags)

    out.heading(f"Permissions {value}")
    out.note(f"  hex {value:#018x}  ({len(matched)} of {len(flags)} known permissions)")
    out.line()
    if matched:
        for flag in matched:
            _render(flag, out)
    else:
        out.note("  (no permissions set)")
    out.warnings(warnings)
    return _payload(value, matched, warnings, flags)


def _encode(raw: str, flags: FlagSet, out: Printer) -> dict[str, Any]:
    names = split_names(raw)
    if not names:
        raise UsageError(
            "--names did not contain any permission names",
            hint="example: dkit perms --names SEND_MESSAGES,MANAGE_ROLES",
        )

    matched = [flags.resolve(name) for name in names]
    value = 0
    for flag in matched:
        value |= flag.value
    # De-duplicate while keeping bit order stable.
    matched = flags.flags_in(value)
    warnings = _summary(value, flags)

    out.heading(f"Permissions {out.style(str(value), 'green', 'bold')}")
    out.note(f"  hex {value:#018x}")
    out.line()
    for flag in matched:
        _render(flag, out)
    out.warnings(warnings)
    return _payload(value, matched, warnings, flags)


def _names_from_option(raw: str, *, option: str) -> list[str]:
    names = split_names(raw)
    if not names:
        raise UsageError(
            f"{option} did not contain any permission names",
            hint=f"example: dkit perms 2048 {option} SEND_MESSAGES,MANAGE_ROLES",
        )
    return names


def _modify(
    raw: str,
    add: str | None,
    remove: str | None,
    flags: FlagSet,
    out: Printer,
) -> dict[str, Any]:
    """Apply ``--add`` then ``--remove`` to NUMBER; unknown bits are preserved."""
    value = parse_int(raw, what="permissions value")

    # Order of operations: add first, then remove. A name present in both ends
    # up cleared.
    if add is not None:
        for name in _names_from_option(add, option="--add"):
            value |= flags.resolve(name).value
    if remove is not None:
        for name in _names_from_option(remove, option="--remove"):
            value &= ~flags.resolve(name).value

    matched = flags.flags_in(value)
    warnings = _summary(value, flags)

    out.heading(f"Permissions {value}")
    out.note(f"  hex {value:#018x}  ({len(matched)} of {len(flags)} known permissions)")
    out.line()
    if matched:
        for flag in matched:
            _render(flag, out)
    else:
        out.note("  (no permissions set)")
    out.warnings(warnings)
    return _payload(value, matched, warnings, flags)


def _group_payload(value: int, flags: FlagSet) -> dict[str, Any]:
    matched = flags.flags_in(value)
    return {
        "value": str(value),
        "hex": f"0x{value:016x}",
        "bit_count": len(matched),
        "permissions": [flag.as_dict() for flag in matched],
        "names": [flag.name for flag in matched],
        "unknown_bits": flags.unknown_bits(value),
    }


def _render_group(
    title: str, value: int, flags: FlagSet, out: Printer, *, color: str, list_flags: bool = True
) -> None:
    matched = flags.flags_in(value)
    unknown = flags.unknown_bits(value)
    out.line()
    out.line(out.style(f"{title} ({len(matched)})", color, "bold"))
    if list_flags:
        for flag in matched:
            _render(flag, out)
        if not matched and not unknown:
            out.note("  (none)")
    if unknown:
        out.line(f"  unknown bits: {', '.join(str(bit) for bit in unknown)}")


def _diff(raw_first: str, raw_second: str, flags: FlagSet, out: Printer) -> dict[str, Any]:
    first = parse_int(raw_first, what="permissions value")
    second = parse_int(raw_second, what="--diff value")

    removed = first & ~second  # only in the first value
    added = second & ~first  # only in the second value
    unchanged = first & second  # in both values

    warnings: list[str] = []
    for label, value in (("removed", removed), ("added", added), ("unchanged", unchanged)):
        unknown = flags.unknown_bits(value)
        if unknown:
            warnings.append(
                f"{label} part contains bits dkit has no name for: "
                + ", ".join(str(bit) for bit in unknown)
                + f" (data last verified {data.provenance('permissions')['last_verified']})"
            )

    out.heading(f"Permissions {first} -> {second}")
    out.note(f"  hex {first:#018x} -> {second:#018x}")
    if first == second:
        out.note("  (identical values, no differences)")
    _render_group("Removed", removed, flags, out, color="red")
    _render_group("Added", added, flags, out, color="green")
    _render_group("Unchanged", unchanged, flags, out, color="dim", list_flags=False)
    out.warnings(warnings)

    return {
        "first": {"value": str(first), "hex": f"0x{first:016x}"},
        "second": {"value": str(second), "hex": f"0x{second:016x}"},
        "identical": first == second,
        "removed": _group_payload(removed, flags),
        "added": _group_payload(added, flags),
        "unchanged": _group_payload(unchanged, flags),
        "warnings": warnings,
        "source": data.provenance("permissions"),
    }


def _list(flags: FlagSet, out: Printer, channel_type: str | None = None) -> dict[str, Any]:
    sorted_flags = sorted(
        (flag for flag in flags if channel_type is None or channel_type in flag.channel_types),
        key=lambda f: f.bit,
    )

    out.heading(f"Permissions ({len(sorted_flags)})")
    out.line()
    for flag in sorted_flags:
        marks = []
        if flag.requires_2fa:
            marks.append("2FA")
        if flag.channel_types:
            marks.append("/".join(flag.channel_types))
        suffix = f"  {out.style('[' + ', '.join(marks) + ']', 'dim')}" if marks else ""
        bit_str = out.style(f"bit {flag.bit:>2}", "dim")
        out.line(
            f"  {bit_str}  {out.style(flag.name.ljust(36), 'green')} {flag.hex}"
            f"  {flag.value}{suffix}"
        )
    out.line()
    out.note("  Markers: [T/V/S] = channel scope (Text/Voice/Stage), [2FA] = requires 2FA.")
    verified = data.provenance("permissions")["last_verified"]
    out.note(f"  Data from the official table (verified {verified}).")

    payload: dict[str, Any] = {
        "permissions": [flag.as_dict() for flag in sorted_flags],
        "total": len(sorted_flags),
        "source": data.provenance("permissions"),
    }
    if channel_type is not None:
        payload["channel_type"] = channel_type
    return payload


COMMAND = Command(
    name="perms",
    help="decode a permissions integer, or build one from names",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit perms 2048\n"
        "  dkit perms 0x800\n"
        "  dkit perms --names SEND_MESSAGES,MANAGE_ROLES\n"
        "  dkit perms 268437504 --diff 274878286912\n"
        "  dkit perms 2048 --add MANAGE_ROLES,KICK_MEMBERS\n"
        "  dkit perms 268437504 --remove MANAGE_ROLES\n"
        "  dkit perms 2048 --add VIEW_CHANNEL --remove SEND_MESSAGES\n"
        "  dkit perms --list\n"
    ),
)
