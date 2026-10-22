"""``dkit invite`` - build or decode an OAuth2 bot invite URL."""

from __future__ import annotations

import argparse
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

from dkit.commands.perms import permission_flags
from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import looks_like_int, parse_int, split_names
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
Build an OAuth2 authorization URL that adds your application to a server, or
decode an existing invite URL back into its parts with --decode.
Permissions may be given as names or as an integer; query parameters are
URL-encoded, with scopes separated by %20 as the official documentation shows.
"""


def _oauth2() -> dict[str, Any]:
    return data.load("oauth2")


def validate_client_id(raw: str) -> str:
    """Check that the client ID is a plain numeric snowflake."""
    candidate = raw.strip()
    if not candidate:
        raise UsageError("--client-id is empty")
    if not candidate.isdigit():
        raise UsageError(
            f"--client-id must be numeric: {raw!r}",
            hint=("an application (client) ID is a Discord snowflake, e.g. 157730590492196864"),
        )
    return candidate


def validate_scopes(raw: str | None) -> list[str]:
    """Split and validate the requested OAuth2 scopes."""
    known = [entry["name"] for entry in _oauth2()["scopes"]]
    scopes = split_names(raw) if raw is not None else list(_oauth2()["default_scopes"])
    if not scopes:
        raise UsageError(
            "--scopes did not contain any scope names",
            hint="example: --scopes bot,applications.commands",
        )

    for scope in scopes:
        if scope not in known:
            raise UsageError(
                f"unknown OAuth2 scope: {scope!r}",
                hint=suggestion_hint(scope, known),
            )

    # De-duplicate while preserving the order the user asked for.
    return list(dict.fromkeys(scopes))


def resolve_permissions(raw: str | None) -> tuple[int | None, list[str]]:
    """Return the permissions integer and the names it covers.

    ``raw`` may be an integer or a comma-separated list of permission names.
    ``None`` means the caller did not request any permissions.
    """
    if raw is None:
        return None, []

    flags = permission_flags()
    if looks_like_int(raw):
        value = parse_int(raw, what="--perms value")
    else:
        names = split_names(raw)
        if not names:
            raise UsageError(
                "--perms did not contain any permission names",
                hint="example: --perms SEND_MESSAGES,EMBED_LINKS",
            )
        value = flags.value_of(names)
    return value, [flag.name for flag in flags.flags_in(value)]


def build_url(client_id: str, scopes: list[str], permissions: int | None) -> str:
    """Assemble the authorization URL with properly encoded query parameters."""
    params: list[tuple[str, str]] = [
        ("client_id", client_id),
        ("scope", " ".join(scopes)),
    ]
    if permissions is not None:
        params.append(("permissions", str(permissions)))
    query = urlencode(params, quote_via=quote, safe="")
    return f"{_oauth2()['authorize_url']}?{query}"


def decode_url(raw: str) -> dict[str, Any]:
    """Parse an OAuth2 authorization URL into its client ID, scopes and permissions.

    No network access: only the URL text is inspected. Scope separators encoded
    as ``%20`` or ``+`` are both accepted.
    """
    candidate = raw.strip()
    if not candidate:
        raise UsageError(
            "URL is empty",
            hint=(
                "pass an OAuth2 authorization URL, e.g. "
                "https://discord.com/oauth2/authorize?client_id=..."
            ),
        )

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise UsageError(
            f"not a URL: {raw!r}",
            hint=(
                "pass an OAuth2 authorization URL, e.g. "
                "https://discord.com/oauth2/authorize?client_id=..."
            ),
        )

    # parse_qs turns both %20 and + into spaces in the scope value.
    query = parse_qs(parsed.query, keep_blank_values=True)

    if "client_id" not in query or not query["client_id"][0]:
        raise UsageError(
            "URL is missing client_id",
            hint="the authorize URL must include a numeric client_id query parameter",
        )

    client_id_raw = query["client_id"][0]
    if not client_id_raw.isdigit():
        raise UsageError(
            f"client_id must be numeric: {client_id_raw!r}",
            hint=("an application (client) ID is a Discord snowflake, e.g. 157730590492196864"),
        )
    client_id = client_id_raw

    scopes: list[str] = []
    if "scope" in query and query["scope"][0]:
        scopes = query["scope"][0].split()

    permissions: int | None = None
    permission_names: list[str] = []
    unknown_bits: list[int] = []
    warnings: list[str] = []

    if "permissions" in query:
        perms_raw = query["permissions"][0]
        if not looks_like_int(perms_raw):
            raise UsageError(
                f"permissions is not an integer: {perms_raw!r}",
                hint="permissions must be a non-negative decimal integer",
            )
        permissions = parse_int(perms_raw, what="permissions")
        flags = permission_flags()
        permission_names = [flag.name for flag in flags.flags_in(permissions)]
        unknown_bits = flags.unknown_bits(permissions)
        if unknown_bits:
            warnings.append(
                "value contains bits dkit has no name for: "
                + ", ".join(str(bit) for bit in unknown_bits)
                + f" (data last verified {data.provenance('permissions')['last_verified']})"
            )

    return {
        "url": candidate,
        "client_id": client_id,
        "scopes": scopes,
        "permissions": None if permissions is None else str(permissions),
        "permission_names": permission_names,
        "unknown_bits": unknown_bits,
        "warnings": warnings,
        "source": data.provenance("oauth2"),
    }


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit invite``."""
    parser.add_argument(
        "--decode",
        metavar="URL",
        help="read an existing OAuth2 invite URL back into its parts",
    )
    parser.add_argument(
        "--client-id",
        metavar="ID",
        help="your application's client ID (a numeric snowflake)",
    )
    parser.add_argument(
        "--perms",
        metavar="NAMES|NUMBER",
        help="permissions to request, as names or an integer",
    )
    parser.add_argument(
        "--scopes",
        metavar="SCOPES",
        help="comma-separated OAuth2 scopes (default: bot,applications.commands)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit invite``."""
    if args.decode is not None:
        conflicts = [
            name
            for name, value in (
                ("--client-id", args.client_id),
                ("--perms", args.perms),
                ("--scopes", args.scopes),
            )
            if value is not None
        ]
        if conflicts:
            joined = ", ".join(conflicts)
            raise UsageError(
                f"--decode cannot be combined with {joined}",
                hint="decode an existing URL, or build a new one, but not both at once",
            )
        return _run_decode(args.decode, out)

    if args.client_id is None:
        raise UsageError(
            "--client-id is required (or pass --decode URL)",
            hint="example: dkit invite --client-id 157730590492196864",
        )

    client_id = validate_client_id(args.client_id)
    scopes = validate_scopes(args.scopes)
    permissions, permission_names = resolve_permissions(args.perms)

    url = build_url(client_id, scopes, permissions)
    warnings: list[str] = []
    if permissions is not None and "bot" not in scopes:
        warnings.append(
            "permissions only take effect together with the 'bot' scope, which is not in --scopes"
        )
    if "ADMINISTRATOR" in permission_names:
        warnings.append(
            "the requested permissions include ADMINISTRATOR, which grants "
            "every permission and bypasses channel overwrites"
        )

    out.heading("Invite URL")
    out.line(f"  {out.style(url, 'blue', 'bold')}")
    out.line()
    out.field("Client ID", client_id)
    out.field("Scopes", ", ".join(scopes))
    if permissions is None:
        out.field("Permissions", out.style("(none requested)", "dim"))
    else:
        out.field("Permissions", str(permissions))
        for name in permission_names:
            out.line(f"    {out.style('-', 'dim')} {name}")
    out.warnings(warnings)

    return {
        "url": url,
        "client_id": client_id,
        "scopes": scopes,
        "permissions": None if permissions is None else str(permissions),
        "permission_names": permission_names,
        "warnings": warnings,
        "source": data.provenance("oauth2"),
    }


def _run_decode(raw_url: str, out: Printer) -> dict[str, Any]:
    payload = decode_url(raw_url)

    out.heading("Decoded invite")
    out.line(f"  {out.style(payload['url'], 'blue', 'bold')}")
    out.line()
    out.field("Client ID", payload["client_id"])
    scopes = payload["scopes"]
    out.field("Scopes", ", ".join(scopes) if scopes else out.style("(none)", "dim"))
    if payload["permissions"] is None:
        out.field("Permissions", out.style("none", "dim"))
    else:
        out.field("Permissions", payload["permissions"])
        for name in payload["permission_names"]:
            out.line(f"    {out.style('-', 'dim')} {name}")
        unknown = payload["unknown_bits"]
        if unknown:
            out.line(f"  unknown bits: {', '.join(str(bit) for bit in unknown)}")
    out.warnings(payload["warnings"])
    return payload


COMMAND = Command(
    name="invite",
    help="build or decode an OAuth2 invite URL for your bot",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit invite --client-id 157730590492196864\n"
        "  dkit invite --client-id 157730590492196864 --perms SEND_MESSAGES,EMBED_LINKS\n"
        "  dkit invite --client-id 157730590492196864 --perms 68608 --scopes bot\n"
        "  dkit invite --decode "
        "'https://discord.com/oauth2/authorize?client_id=157730590492196864"
        "&scope=bot%20applications.commands&permissions=2048'\n"
    ),
)
