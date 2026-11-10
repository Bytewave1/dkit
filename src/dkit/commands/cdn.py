"""``dkit cdn`` - build Discord CDN image URLs offline from an ID and a hash."""

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
Build a Discord CDN image URL offline from an ID and a hash. Every endpoint
type from the Image Formatting docs is supported; run 'dkit cdn --list' for
the full table. The hash comes from API responses such as Get User; a hash
that starts with a_ is available in an animated format.
"""

LIST_HINT = "run 'dkit cdn --list' for every endpoint type and its arguments"

#: The image formats of the docs, fixed here so building the parser never
#: needs to load data; per-endpoint support is checked against cdn.json.
FORMAT_CHOICES = ("gif", "jpeg", "lottie", "png", "webp")


def endpoints() -> list[dict[str, Any]]:
    """The CDN endpoint table from ``dkit/data/cdn.json``."""
    return list(data.load("cdn")["endpoints"])


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit cdn``."""
    parser.add_argument(
        "type",
        metavar="TYPE",
        nargs="?",
        help="an endpoint type, e.g. avatar or guild-icon ('dkit cdn --list' for all)",
    )
    parser.add_argument(
        "values",
        metavar="ARG",
        nargs="*",
        help="the IDs and hash the type needs, in path order (IDs first, hash last)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list every endpoint type with its path template",
    )
    parser.add_argument(
        "--format",
        metavar="FORMAT",
        choices=FORMAT_CHOICES,
        help="image format: png (default), jpeg, webp, gif or lottie",
    )
    parser.add_argument(
        "--size",
        metavar="N",
        help="appended as ?size=N; must be a power of two between 16 and 4096",
    )
    parser.add_argument(
        "--discriminator",
        metavar="N",
        help="with default-avatar: compute the index from a legacy discriminator",
    )
    parser.add_argument(
        "--animated",
        action="store_true",
        help="with --format webp: add ?animated=true (needs a hash starting with a_)",
    )


def _endpoint(type_name: str) -> dict[str, Any]:
    """Return the endpoint entry for ``type_name``."""
    for entry in endpoints():
        if entry["type"] == type_name:
            return entry
    raise UsageError(
        f"unknown CDN endpoint type: {type_name!r}",
        hint=suggestion_hint(type_name, [entry["type"] for entry in endpoints()]) or LIST_HINT,
    )


def _format_extension(format_name: str) -> str:
    """The URL extension of an image format."""
    return str(data.load("cdn")["formats"][format_name])


def _size(value: str | None) -> int | None:
    """Validate the requested size: a power of two between 16 and 4096."""
    if value is None:
        return None
    sizes = data.load("cdn")["sizes"]
    try:
        number = int(value)
    except ValueError:
        raise UsageError(f"size is not an integer: {value!r}", hint=sizes["rule"]) from None
    if number < sizes["min"] or number > sizes["max"] or number & (number - 1):
        raise UsageError(
            f"size must be a power of two between {sizes['min']} and {sizes['max']}: {number}",
            hint=sizes["rule"],
        )
    return number


def _query(params: list[tuple[str, str]]) -> str:
    """The querystring for the URL, or ``""`` when there is nothing to append."""
    if not params:
        return ""
    return "?" + "&".join(f"{key}={value}" for key, value in params)


def _check_hash(raw: str) -> str:
    """Check the hash argument is present."""
    value = raw.strip()
    if not value:
        raise UsageError(
            "hash is empty",
            hint="the hash comes from API responses such as Get User",
        )
    return value


def _parse_values(endpoint: dict[str, Any], values: list[str]) -> dict[str, str]:
    """Parse the positional arguments of an endpoint, IDs as snowflakes."""
    expected = endpoint["args"]
    if len(values) != len(expected):
        raise UsageError(
            f"{endpoint['type']} takes {len(expected)} argument"
            f"{'s' if len(expected) != 1 else ''} ({', '.join(expected)}), got {len(values)}",
            hint="example: dkit cdn {type} {args}".format(
                type=endpoint["type"], args=" ".join(f"<{name}>" for name in expected)
            ),
        )
    parsed: dict[str, str] = {}
    for name, raw in zip(expected, values, strict=True):
        parsed[name] = str(parse_snowflake(raw)) if name.endswith("_id") else _check_hash(raw)
    return parsed


def _animated_check(
    endpoint: dict[str, Any], values: list[str], animated: bool, chosen: str
) -> None:
    """Reject --animated where the docs do not allow it."""
    if not animated:
        return
    if endpoint["type"] == "sticker":
        raise UsageError(
            "--animated does not apply to stickers",
            hint="sticker GIFs are served from media.discordapp.net and need no animated flag",
        )
    if chosen != "webp":
        raise UsageError(
            "--animated only applies to --format webp",
            hint="animated WebP is documented as .webp plus ?animated=true",
        )
    if not endpoint["gif"]:
        raise UsageError(
            f"{endpoint['type']} is never animated per the docs, so --animated does not apply",
            hint="only endpoints whose hash may start with a_ support animated images",
        )
    if not values[-1].strip().startswith("a_"):
        raise UsageError(
            "--animated needs a hash that starts with a_",
            hint="animated images are the ones whose hash begins with a_",
        )


def build_url(
    type_name: str,
    values: list[str],
    *,
    format_name: str | None = None,
    size: str | None = None,
    discriminator: str | None = None,
    animated: bool = False,
) -> dict[str, Any]:
    """Build the URL payload for one endpoint invocation."""
    endpoint = _endpoint(type_name)
    cdn = data.load("cdn")

    if type_name == "default-avatar":
        return _default_avatar_payload(endpoint, values, size=size, discriminator=discriminator)

    chosen = format_name or "png"
    if chosen not in endpoint["formats"]:
        raise UsageError(
            f"{type_name} does not support {chosen}: "
            f"supported formats are {', '.join(endpoint['formats'])}",
            hint="run 'dkit cdn --list' for the endpoint table",
        )
    _animated_check(endpoint, values, animated, chosen)

    path = endpoint["path"].format(**_parse_values(endpoint, values))
    if not endpoint.get("no_extension"):
        path = path[: -len(".png")] + _format_extension(chosen)

    base = cdn["base_url"]
    if type_name == "sticker" and chosen == "gif":
        base = cdn["sticker_gif_base_url"]
    url = base + path

    params: list[tuple[str, str]] = []
    requested_size = _size(size)
    if not endpoint.get("size_ignored") and requested_size is not None:
        params.append(("size", str(requested_size)))
    if chosen == "webp" and animated:
        params.append(("animated", "true"))
    url += _query(params)

    payload: dict[str, Any] = {
        "mode": "url",
        "type": type_name,
        "url": url,
        "format": chosen,
        "size": requested_size,
        "endpoint": {"path": endpoint["path"], "formats": endpoint["formats"]},
    }
    if endpoint.get("size_ignored"):
        payload["size_ignored"] = True
    if endpoint.get("notes"):
        payload["notes"] = endpoint["notes"]
    return payload


def _default_avatar_payload(
    endpoint: dict[str, Any],
    values: list[str],
    *,
    size: str | None,
    discriminator: str | None,
) -> dict[str, Any]:
    """Build the default avatar URL; the index comes from the user ID or discriminator."""
    if len(values) != 1:
        raise UsageError(
            f"default-avatar takes 1 argument (user_id), got {len(values)}",
            hint="example: dkit cdn default-avatar 80351110224678912",
        )
    if discriminator is not None:
        if not discriminator.isdigit():
            raise UsageError(
                f"discriminator is not a number: {discriminator!r}",
                hint="legacy discriminators are four digits, 0001-9999",
            )
        legacy = int(discriminator)
        if legacy == 0:
            raise UsageError(
                "discriminator 0 means the user is on the new username system",
                hint="omit --discriminator to use (user_id >> 22) % 6",
            )
        index = legacy % 5
        index_rule = f"discriminator {legacy} % 5"
    else:
        user_id = parse_snowflake(values[0])
        index = (user_id >> 22) % 6
        index_rule = "(user_id >> 22) % 6"

    url = data.load("cdn")["base_url"] + endpoint["path"].format(index=index)
    requested_size = _size(size)
    if requested_size is not None:
        url += _query([("size", str(requested_size))])
    return {
        "mode": "url",
        "type": "default-avatar",
        "url": url,
        "format": "png",
        "size": requested_size,
        "size_ignored": True,
        "index": index,
        "index_rule": index_rule,
        "endpoint": {"path": endpoint["path"], "formats": endpoint["formats"]},
        "notes": endpoint.get("notes", []),
    }


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit cdn``."""
    if args.list:
        if args.type is not None or args.values:
            raise UsageError(
                "--list cannot be combined with a type",
                hint="list every type, or build one URL, but not both",
            )
        entries = endpoints()
        _render_list(out, entries)
        return {
            "mode": "list",
            "count": len(entries),
            "endpoints": [
                {"type": entry["type"], "path": entry["path"], "args": entry["args"]}
                for entry in entries
            ],
            "source": data.provenance("cdn"),
        }

    if args.type is None:
        raise UsageError("no endpoint type given", hint=LIST_HINT)

    payload = build_url(
        args.type,
        args.values,
        format_name=args.format,
        size=args.size,
        discriminator=args.discriminator,
        animated=args.animated,
    )
    _render_url(out, payload)
    payload["source"] = data.provenance("cdn")
    return payload


def _render_list(out: Printer, entries: list[dict[str, Any]]) -> None:
    """Print the endpoint table; a no-op in ``--json`` mode."""
    out.heading(f"CDN endpoints ({len(entries)})")
    for entry in entries:
        out.line(f"  {out.style(entry['type'], 'green')}  {entry['path']}")
    out.line()
    out.note("  Build one: dkit cdn <type> <ARG ...> [--format FORMAT] [--size N]")
    out.note(f"  Data comes from the official Image Formatting docs (verified {_verified()}).")


def _render_url(out: Printer, payload: dict[str, Any]) -> None:
    """Print one built URL; a no-op in ``--json`` mode."""
    out.heading("CDN URL")
    out.field("Type", payload["type"])
    out.field("URL", out.style(payload["url"], "green"))
    if payload.get("index_rule"):
        out.field("Index", f"{payload['index']}  ({payload['index_rule']})")
    for note in payload.get("notes", []):
        out.note(f"  {note}")


def _verified() -> str:
    return str(data.provenance("cdn")["last_verified"])


COMMAND = Command(
    name="cdn",
    help="build Discord CDN image URLs offline",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit cdn avatar 80351110224678912 \\\n"
        "      a_1269e74af4df7417b13759eae50c83dc --format webp --size 256\n"
        "  dkit cdn default-avatar 80351110224678912\n"
        "  dkit cdn sticker 813248342119698674 --format gif\n"
        "  dkit --json cdn guild-icon GUILD_ID HASH\n"
    ),
)
