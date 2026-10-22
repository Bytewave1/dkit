"""``dkit snowflake`` - decode Discord snowflake IDs, or build one from a date."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import format_datetime, parse_datetime, parse_int
from dkit.core.registry import Command

#: A snowflake is documented as being up to 64 bits wide.
MAX_SNOWFLAKE = (1 << 64) - 1

DESCRIPTION = """\
Decode one or more Discord snowflake IDs into their creation timestamp,
internal worker ID, internal process ID and increment. A mention such as
<@ID> or <#ID>, or a Discord message link, is accepted as well: the IDs inside
are pulled out and labelled. With --from-date, build the lowest snowflake ID
for a given point in time instead.
"""

#: The mention forms the documentation describes, longest prefix first so that
#: ``<@!ID>`` and ``<@&ID>`` are never read as a plain ``<@ID>``. ``<@!ID>`` is
#: deprecated but still turns up in old messages, so it is decoded the same way.
#: This is grammar rather than a value that goes stale, which is why it lives in
#: code; the hosts a message link may sit on live in ``data/snowflake.json``.
_MENTION_LABELS: tuple[tuple[str, str], ...] = (
    ("@!", "user"),
    ("@&", "role"),
    ("@", "user"),
    ("#", "channel"),
)

#: The IDs a Discord message link carries, in the order they appear in its path.
_LINK_LABELS = ("guild", "channel", "message")


def _layout() -> dict[str, Any]:
    return data.load("snowflake")


def _epoch_ms() -> int:
    return int(_layout()["epoch_ms"])


def _field(key: str) -> dict[str, Any]:
    for entry in _layout()["fields"]:
        if entry["key"] == key:
            return entry
    raise KeyError(key)  # pragma: no cover - guarded by the data file tests


def _message_links() -> dict[str, Any]:
    return _layout()["message_links"]


def _extract(snowflake: int, key: str) -> int:
    """Pull one field out of a snowflake using the documented mask and shift."""
    spec = _field(key)
    return (snowflake & int(spec["mask"], 16)) >> int(spec["shift"])


def decode(snowflake: int) -> dict[str, Any]:
    """Decode a snowflake into its documented components."""
    epoch = _epoch_ms()
    discord_ms = _extract(snowflake, "timestamp_ms")
    unix_ms = discord_ms + epoch
    created = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=unix_ms)
    return {
        "id": str(snowflake),
        "created_at": format_datetime(created),
        "unix_ms": unix_ms,
        "discord_ms": discord_ms,
        "worker_id": _extract(snowflake, "worker_id"),
        "process_id": _extract(snowflake, "process_id"),
        "increment": _extract(snowflake, "increment"),
    }


def encode(moment: datetime) -> int:
    """Return the lowest snowflake ID that could have been created at ``moment``."""
    epoch = _epoch_ms()
    unix_ms = int(moment.timestamp() * 1000)
    if unix_ms < epoch:
        raise UsageError(
            f"{format_datetime(moment)} is before the Discord epoch "
            f"({format_datetime(datetime.fromtimestamp(epoch / 1000, timezone.utc))})",
            hint="Discord snowflakes cannot represent a time before 2015-01-01T00:00:00Z",
        )
    return (unix_ms - epoch) << int(_field("timestamp_ms")["shift"])


def parse_snowflake(text: str) -> int:
    """Parse and range-check a snowflake ID given on the command line."""
    value = parse_int(text, what="snowflake ID")
    if value > MAX_SNOWFLAKE:
        raise UsageError(
            f"snowflake ID is too large to be a 64-bit value: {text!r}",
            hint=f"the largest possible snowflake is {MAX_SNOWFLAKE}",
        )
    return value


def _parse_mention(raw: str) -> tuple[str, int] | None:
    """Return the ``(label, id)`` a Discord mention refers to.

    ``None`` means the text is not wrapped in angle brackets at all, so the
    caller should keep trying the other input forms.
    """
    if not raw.startswith("<") or not raw.endswith(">"):
        return None
    inner = raw[1:-1]
    if inner.startswith("@$"):
        raise UsageError(
            f"{raw!r} is a game profile mention, which dkit does not decode",
            hint="user, channel and role mentions are the ones that are decoded",
        )
    for prefix, label in _MENTION_LABELS:
        if inner.startswith(prefix):
            return label, parse_snowflake(inner[len(prefix) :])
    raise UsageError(
        f"{raw!r} is not a Discord mention",
        hint="expected one of <@ID>, <@!ID>, <#ID> or <@&ID>",
    )


def _is_discord_link_host(hostname: str | None) -> bool:
    """Whether ``hostname`` belongs to one of Discord's own domains."""
    if not hostname:
        return False
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in _message_links()["domains"]
    )


def _parse_message_link(raw: str) -> tuple[list[tuple[str, int]], list[str]] | None:
    """Return the ``(label, id)`` pairs a Discord message link carries.

    ``None`` means the text is not an ``http(s)`` link to Discord, so the
    caller should keep trying the other input forms. A direct-message link puts
    ``@me`` where the guild ID would be; that slot holds no snowflake, so it is
    skipped and reported instead of being decoded.
    """
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not _is_discord_link_host(parts.hostname):
        return None

    prefix = _message_links()["path_prefix"]
    segments = [part for part in parts.path.split("/") if part]
    ids = segments[1:]
    if not segments or segments[0] != prefix or not 2 <= len(ids) <= len(_LINK_LABELS):
        raise UsageError(
            f"{raw!r} is not a Discord message link",
            hint=f"expected /{prefix}/GUILD_ID/CHANNEL_ID[/MESSAGE_ID]",
        )

    entries: list[tuple[str, int]] = []
    warnings: list[str] = []
    for label, segment in zip(_LINK_LABELS, ids, strict=False):
        if label == "guild" and segment == _message_links()["dm_marker"]:
            warnings.append(
                f"the guild ID is {segment!r}, so this link points into a direct "
                "message and carries no guild snowflake"
            )
            continue
        entries.append((label, parse_snowflake(segment)))
    return entries, warnings


def _collect(raw: str) -> tuple[list[tuple[str | None, int]], list[str]]:
    """Interpret one piece of input and return the IDs it stands for.

    A plain snowflake gives one unlabelled pair, a mention gives one labelled
    pair, and a message link gives one pair per ID it contains.
    """
    mention = _parse_mention(raw)
    if mention is not None:
        return [mention], []

    link = _parse_message_link(raw)
    if link is not None:
        return link

    return [(None, parse_snowflake(raw))], []


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit snowflake``."""
    parser.add_argument(
        "ids",
        metavar="ID",
        nargs="*",
        help="snowflake IDs, mentions (<@ID>, <#ID>, ...) or message links",
    )
    parser.add_argument(
        "--from-date",
        metavar="TIMESTAMP",
        help="build a snowflake from an ISO-8601 timestamp, e.g. 2016-04-30T11:18:25Z",
    )


def _is_terminal() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _read_stdin() -> list[str]:
    lines: list[str] = []
    try:
        for line in sys.stdin:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
    except OSError:
        pass
    return lines


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit snowflake``."""
    if args.from_date and args.ids:
        raise UsageError(
            "--from-date cannot be combined with snowflake IDs",
            hint="decode IDs, or build one from a date, but not both at once",
        )

    if args.from_date:
        return _run_encode(args.from_date, out)

    ids = list(args.ids)
    if ids == ["-"] or (not ids and not _is_terminal()):
        ids = _read_stdin()

    if not ids:
        raise UsageError(
            "no snowflake ID given",
            hint="example: dkit snowflake 175928847299117063",
        )

    return _run_decode(ids, out)


def _run_encode(text: str, out: Printer) -> dict[str, Any]:
    moment = parse_datetime(text, what="--from-date")
    snowflake = encode(moment)
    payload = {
        "from_date": format_datetime(moment),
        "unix_ms": int(moment.timestamp() * 1000),
        "discord_ms": snowflake >> int(_field("timestamp_ms")["shift"]),
        "snowflake": str(snowflake),
        "note": "lowest snowflake for this millisecond (worker, process and "
        "increment are all zero)",
        "source": data.provenance("snowflake"),
    }

    out.heading(format_datetime(moment))
    out.field("Snowflake", out.style(str(snowflake), "green", "bold"))
    out.field("Unix ms", str(payload["unix_ms"]))
    out.field("Discord ms", str(payload["discord_ms"]))
    out.line()
    out.note(f"  {payload['note']}")
    return payload


def _run_decode(ids: list[str], out: Printer) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw in ids:
        entries, notes = _collect(raw)
        warnings.extend(notes)
        for label, value in entries:
            result = decode(value)
            if label is not None:
                result["label"] = label
            results.append(result)

    for index, result in enumerate(results):
        if index:
            out.line()
        out.heading(result["id"])
        if "label" in result:
            out.field("Kind", result["label"])
        out.field("Created", out.style(result["created_at"], "green", "bold"))
        out.field("Unix ms", str(result["unix_ms"]))
        out.field("Discord ms", str(result["discord_ms"]))
        out.field("Worker ID", str(result["worker_id"]))
        out.field("Process ID", str(result["process_id"]))
        out.field("Increment", str(result["increment"]))

    out.warnings(warnings)

    # A label is only added when the input named one, so the payload of a plain
    # ID stays byte-for-byte what it has always been.
    payload: dict[str, Any] = dict(results[0]) if len(results) == 1 else {"snowflakes": results}
    if warnings:
        payload["warnings"] = warnings
    payload["source"] = data.provenance("snowflake")
    return payload


COMMAND = Command(
    name="snowflake",
    help="decode snowflake IDs, or build one from a date",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit snowflake 175928847299117063\n"
        "  dkit snowflake 175928847299117063 80351110224678912\n"
        '  dkit snowflake "<@80351110224678912>"\n'
        '  dkit snowflake "<#103735883630395392>"\n'
        '  dkit snowflake "https://discord.com/channels/1/2/3"\n'
        "  dkit snowflake --from-date 2016-04-30T11:18:25Z\n"
        "  cat ids.txt | dkit snowflake\n"
        "  dkit snowflake - < ids.txt\n"
    ),
)
