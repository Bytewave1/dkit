"""``dkit mention`` - build Discord mention and formatting strings."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.commands.snowflake import parse_snowflake
from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
Build a Discord mention or formatting string: <@ID> for users, <#ID> for
channels, <@&ID> for roles, </name:ID> for slash commands, <:name:ID> for
emoji and <id:...> for guild navigation. Run 'dkit mention --list' for the
whole table. The deprecated <@!ID> form is not generated; the docs say it
should be handled like any other user mention.
"""

LIST_HINT = "run 'dkit mention --list' for every format"

_TYPES = ("user", "channel", "role", "command", "emoji", "navigation")


def formats() -> list[dict[str, Any]]:
    """The message formats table from ``dkit/data/message_formats.json``."""
    return list(data.load("message_formats")["table"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit mention``."""
    parser.add_argument(
        "type",
        metavar="TYPE",
        nargs="?",
        help="user, channel, role, command, emoji or navigation ('--list' for all)",
    )
    parser.add_argument(
        "values",
        metavar="ARG",
        nargs="*",
        help="the IDs, names and types the format needs; 'dkit mention --list' shows them",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list every message format with its syntax",
    )
    parser.add_argument(
        "--animated",
        action="store_true",
        help="with emoji: build the animated form <a:NAME:ID>",
    )


def _template(kind: str) -> str:
    """The machine-usable template of one format."""
    return str(data.load("message_formats")["templates"][kind])


def _notify_note() -> str:
    return str(data.load("message_formats")["notify_note"])


def _check_name(raw: str, *, what: str) -> str:
    """Check a name that is embedded verbatim into the format."""
    value = raw.strip()
    if not value:
        raise UsageError(f"{what} is empty", hint=LIST_HINT)
    if ">" in value or "<" in value:
        raise UsageError(
            f"{what} must not contain angle brackets: {raw!r}",
            hint="the brackets are added by the format itself",
        )
    return value


def _command_name(values: list[str]) -> str:
    """The slash command path: every argument but the last, joined by spaces."""
    name = _check_name(" ".join(values), what="command name")
    if ":" in name:
        raise UsageError(
            f"command name must not contain a colon: {name!r}",
            hint="the colon before the command ID is added by the format itself",
        )
    return name


def build_mention(kind: str, values: list[str], *, animated: bool = False) -> dict[str, Any]:
    """Build the mention payload for one format invocation."""
    fmt = data.load("message_formats")

    if kind in ("user", "channel", "role"):
        if len(values) != 1:
            raise UsageError(
                f"{kind} takes 1 argument ({kind}_id), got {len(values)}",
                hint=f"example: dkit mention {kind} 123456789012345678",
            )
        mention = _template(kind).format(**{f"{kind}_id": parse_snowflake(values[0])})
        return {
            "mode": "mention",
            "type": kind,
            "mention": mention,
            "notify": kind in ("user", "role"),
        }

    if kind == "command":
        if len(values) < 2:
            raise UsageError(
                "command takes 2 arguments (name, command_id); the name may "
                "contain spaces for subcommands",
                hint='example: dkit mention command "foo bar" 123456789012345678',
            )
        name = _command_name(values[:-1])
        mention = _template("command").format(name=name, command_id=parse_snowflake(values[-1]))
        return {"mode": "mention", "type": "command", "mention": mention, "notify": False}

    if kind == "emoji":
        if len(values) != 2:
            raise UsageError(
                f"emoji takes 2 arguments (name, emoji_id), got {len(values)}",
                hint="example: dkit mention emoji mmLol 216154654256398347",
            )
        name = _check_name(values[0], what="emoji name")
        if ":" in name:
            raise UsageError(
                f"emoji name must not contain a colon: {name!r}",
                hint="the colons around the name are added by the format itself",
            )
        template = _template("animated-emoji" if animated else "emoji")
        mention = template.format(name=name, emoji_id=parse_snowflake(values[1]))
        return {
            "mode": "mention",
            "type": "animated-emoji" if animated else "emoji",
            "mention": mention,
            "notify": False,
        }

    if kind == "navigation":
        navigation_types = fmt["navigation_types"]
        if len(values) not in (1, 2):
            raise UsageError(
                f"navigation takes 1 argument (type) or 2 (type, role_id), got {len(values)}",
                hint=f"types: {', '.join(navigation_types)}",
            )
        nav_type = _check_name(values[0], what="navigation type")
        if nav_type not in navigation_types:
            raise UsageError(
                f"unknown navigation type: {nav_type!r}",
                hint=suggestion_hint(nav_type, list(navigation_types))
                or f"types: {', '.join(navigation_types)}",
            )
        if len(values) == 2:
            if nav_type != "linked-roles":
                raise UsageError(
                    f"only linked-roles takes a role id, not {nav_type}",
                    hint="example: dkit mention navigation linked-roles 123456789012345678",
                )
            mention = _template("linked-roles").format(role_id=parse_snowflake(values[1]))
        else:
            mention = _template("navigation").format(navigation_type=nav_type)
        return {
            "mode": "mention",
            "type": f"navigation-{nav_type}",
            "mention": mention,
            "description": navigation_types[nav_type],
            "notify": False,
        }

    raise UsageError(
        f"unknown mention type: {kind!r}",
        hint=suggestion_hint(kind, list(_TYPES)) or LIST_HINT,
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit mention``."""
    if args.list:
        if args.type is not None or args.values:
            raise UsageError(
                "--list cannot be combined with a type",
                hint="list every format, or build one mention, but not both",
            )
        entries = formats()
        _render_list(out, entries)
        return {
            "mode": "list",
            "count": len(entries),
            "formats": [dict(entry) for entry in entries],
            "source": data.provenance("message_formats"),
        }

    if args.type is None:
        raise UsageError("no mention type given", hint=LIST_HINT)
    if args.animated and args.type != "emoji":
        raise UsageError(
            "--animated only applies to emoji",
            hint="animated emoji are the ones built as <a:NAME:ID>",
        )

    payload = build_mention(args.type, args.values, animated=args.animated)
    _render_mention(out, payload)
    payload["source"] = data.provenance("message_formats")
    return payload


def _render_list(out: Printer, entries: list[dict[str, Any]]) -> None:
    """Print the formats table; a no-op in ``--json`` mode."""
    out.heading(f"Message formats ({len(entries)})")
    for entry in entries:
        out.line(f"  {out.style(entry['syntax'], 'green')}  {entry['description']}")
        for note in entry.get("notes", []):
            out.note(f"    {note}")
    out.line()
    out.note("  Build one: dkit mention <type> <ARG ...>")
    out.note(f"  Data comes from the official Message Formatting docs (verified {_verified()}).")


def _render_mention(out: Printer, payload: dict[str, Any]) -> None:
    """Print one built mention; a no-op in ``--json`` mode."""
    out.heading("Mention")
    out.field("Type", payload["type"])
    out.field("Mention", out.style(payload["mention"], "green"))
    if payload.get("description"):
        out.field("Target", payload["description"])
    if payload.get("notify"):
        out.note(f"  {_notify_note()}")


def _verified() -> str:
    return str(data.provenance("message_formats")["last_verified"])


COMMAND = Command(
    name="mention",
    help="build Discord mention and formatting strings",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit mention user 80351110224678912\n"
        '  dkit mention command "foo bar" 123456789012345678\n'
        "  dkit mention emoji b1nzy 392938283556143104 --animated\n"
        "  dkit mention navigation linked-roles 123456789012345678\n"
        "  dkit mention --list\n"
    ),
)
