"""Tests for ``dkit invite``."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from dkit.commands.invite import build_url, resolve_permissions, validate_client_id
from dkit.core.errors import UsageError

CLIENT_ID = "157730590492196864"


def test_default_scopes_and_no_permissions() -> None:
    url = build_url(CLIENT_ID, ["bot", "applications.commands"], None)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://discord.com/oauth2/authorize"
    )
    assert query["client_id"] == [CLIENT_ID]
    assert query["scope"] == ["bot applications.commands"]
    assert "permissions" not in query


def test_scopes_are_space_separated_and_percent_encoded() -> None:
    """The official docs encode the scope separator as %20, not '+'."""
    url = build_url(CLIENT_ID, ["bot", "applications.commands"], None)
    assert "scope=bot%20applications.commands" in url
    assert "+" not in url


def test_permissions_are_included_when_requested() -> None:
    url = build_url(CLIENT_ID, ["bot"], 18432)
    assert parse_qs(urlparse(url).query)["permissions"] == ["18432"]


def test_large_permission_values_survive_intact() -> None:
    """A value above 2**53 must not be mangled."""
    value = 1 << 52
    url = build_url(CLIENT_ID, ["bot"], value)
    assert parse_qs(urlparse(url).query)["permissions"] == [str(value)]


def test_parameter_order_is_deterministic() -> None:
    url = build_url(CLIENT_ID, ["bot"], 8)
    assert urlparse(url).query == f"client_id={CLIENT_ID}&scope=bot&permissions=8"


@pytest.mark.parametrize("raw", ["abc", "123abc", "", "  ", "-1", "12.5", "1 2"])
def test_non_numeric_client_ids_are_rejected(raw: str) -> None:
    with pytest.raises(UsageError):
        validate_client_id(raw)


def test_client_id_is_trimmed() -> None:
    assert validate_client_id(f"  {CLIENT_ID} ") == CLIENT_ID


def test_resolve_permissions_from_names_and_numbers() -> None:
    assert resolve_permissions("SEND_MESSAGES,EMBED_LINKS") == (
        18432,
        ["SEND_MESSAGES", "EMBED_LINKS"],
    )
    assert resolve_permissions("18432") == (18432, ["SEND_MESSAGES", "EMBED_LINKS"])
    assert resolve_permissions(None) == (None, [])


def test_resolve_permissions_empty_string_raises() -> None:
    with pytest.raises(UsageError, match="--perms did not contain any permission names"):
        resolve_permissions(" , ")


# --- CLI behaviour ------------------------------------------------------


def test_cli_builds_a_url(cli) -> None:
    result = cli("invite", "--client-id", CLIENT_ID)
    assert result.exit_code == 0
    assert "https://discord.com/oauth2/authorize?client_id=" in result.stdout


def test_cli_json_payload(cli) -> None:
    payload = cli("--json", "invite", "--client-id", CLIENT_ID, "--perms", "SEND_MESSAGES").json
    assert payload["client_id"] == CLIENT_ID
    assert payload["scopes"] == ["bot", "applications.commands"]
    assert payload["permissions"] == "2048"
    assert payload["permission_names"] == ["SEND_MESSAGES"]


def test_cli_custom_scopes(cli) -> None:
    payload = cli("--json", "invite", "--client-id", CLIENT_ID, "--scopes", "bot").json
    assert payload["scopes"] == ["bot"]
    assert "scope=bot&" in payload["url"] or payload["url"].endswith("scope=bot")


def test_cli_duplicate_scopes_are_collapsed(cli) -> None:
    payload = cli("--json", "invite", "--client-id", CLIENT_ID, "--scopes", "bot,bot").json
    assert payload["scopes"] == ["bot"]


def test_cli_warns_when_permissions_lack_the_bot_scope(cli) -> None:
    result = cli("invite", "--client-id", CLIENT_ID, "--scopes", "identify", "--perms", "2048")
    assert result.exit_code == 0
    assert "'bot' scope" in result.stderr


def test_cli_warns_about_administrator(cli) -> None:
    result = cli("invite", "--client-id", CLIENT_ID, "--perms", "ADMINISTRATOR")
    assert result.exit_code == 0
    assert "ADMINISTRATOR" in result.stderr


def test_cli_accepts_a_numeric_perms_value(cli) -> None:
    payload = cli("--json", "invite", "--client-id", CLIENT_ID, "--perms", "0x800").json
    assert payload["permissions"] == "2048"


@pytest.mark.parametrize(
    "argv",
    [
        ("invite", "--client-id", "abc"),
        ("invite", "--client-id", ""),
        ("invite", "--client-id", CLIENT_ID, "--scopes", "application.command"),
        ("invite", "--client-id", CLIENT_ID, "--scopes", "nope_not_a_scope"),
        ("invite", "--client-id", CLIENT_ID, "--scopes", ""),
        ("invite", "--client-id", CLIENT_ID, "--perms", "NOT_A_PERMISSION"),
    ],
)
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


def test_cli_requires_client_id(cli) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli("invite")
    assert excinfo.value.code == 2
