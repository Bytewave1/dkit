"""Tests for ``dkit channels``."""

from __future__ import annotations

import pytest

from dkit.commands.channels import channel_types


def test_channel_types_loads() -> None:
    types = channel_types()
    assert len(types) >= 13
    assert any(t["name"] == "GUILD_FORUM" and t["value"] == 15 for t in types)


def test_cli_channels_list_all(cli) -> None:
    result = cli("channels")
    assert result.exit_code == 0
    assert "GUILD_TEXT" in result.stdout
    assert "GUILD_FORUM" in result.stdout
    assert "GUILD_STAGE_VOICE" in result.stdout


def test_cli_channels_json_all(cli) -> None:
    payload = cli("--json", "channels").json
    assert payload["mode"] == "all"
    assert payload["count"] == 13
    assert len(payload["channel_types"]) == 13
    assert payload["source"]["source"].startswith("https://github.com/discord/discord-api-docs")
    assert any(c["name"] == "GUILD_FORUM" and c["value"] == 15 for c in payload["channel_types"])


def test_cli_lookup_by_integer(cli) -> None:
    result = cli("channels", "15")
    assert result.exit_code == 0
    assert "GUILD_FORUM" in result.stdout
    assert "15" in result.stdout
    assert "Channel that can only contain threads" in result.stdout


def test_cli_lookup_by_name(cli) -> None:
    result = cli("channels", "GUILD_FORUM")
    assert result.exit_code == 0
    assert "GUILD_FORUM" in result.stdout
    assert "15" in result.stdout


def test_cli_lookup_normalises_name(cli) -> None:
    result = cli("channels", "guild-forum")
    assert result.exit_code == 0
    assert "GUILD_FORUM" in result.stdout
    assert "15" in result.stdout


def test_cli_json_lookup(cli) -> None:
    payload = cli("--json", "channels", "15").json
    assert payload["mode"] == "lookup"
    assert payload["name"] == "GUILD_FORUM"
    assert payload["value"] == 15
    assert payload["description"] == "Channel that can only contain threads"
    assert payload["source"]["last_verified"]


def test_cli_unknown_integer_exits_with_code_2(cli) -> None:
    result = cli("channels", "99")
    assert result.exit_code == 2
    assert "unknown channel type integer: '99'" in result.stderr
    assert "run 'dkit channels' to list every known channel type" in result.stderr


def test_cli_unknown_name_with_suggestion(cli) -> None:
    result = cli("channels", "GUILD_FORU")
    assert result.exit_code == 2
    assert "unknown channel type: 'GUILD_FORU'" in result.stderr
    assert "did you mean GUILD_FORUM" in result.stderr


@pytest.mark.parametrize("argv", [("channels", "-1"), ("channels", "99999999999999999999")])
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


def test_cli_strips_whitespace_on_input(cli) -> None:
    res_int = cli("channels", "  15  ")
    assert res_int.exit_code == 0
    assert "GUILD_FORUM" in res_int.stdout

    res_name = cli("channels", "  GUILD_FORUM  ")
    assert res_name.exit_code == 0
    assert "15" in res_name.stdout
