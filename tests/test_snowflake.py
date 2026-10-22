"""Tests for ``dkit snowflake``."""

from __future__ import annotations

import io

import pytest

from dkit.commands.snowflake import MAX_SNOWFLAKE, _is_terminal, decode, encode
from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.parse import parse_datetime


def test_official_docs_example() -> None:
    """The example from the official documentation must decode exactly.

    https://discord.com/developers/docs/reference#snowflakes
    """
    result = decode(175928847299117063)
    assert result["created_at"] == "2016-04-30T11:18:25.796Z"
    assert result["unix_ms"] == 1462015105796
    assert result["worker_id"] == 1
    assert result["process_id"] == 0
    assert result["increment"] == 7


def test_decode_zero_is_the_discord_epoch() -> None:
    result = decode(0)
    assert result["created_at"] == "2015-01-01T00:00:00.000Z"
    assert result["unix_ms"] == 1420070400000
    assert result["worker_id"] == 0
    assert result["process_id"] == 0
    assert result["increment"] == 0


def test_decode_extracts_each_field_independently() -> None:
    """A snowflake with every component set must split cleanly."""
    snowflake = (123 << 22) | (31 << 17) | (17 << 12) | 4095
    result = decode(snowflake)
    assert result["discord_ms"] == 123
    assert result["worker_id"] == 31
    assert result["process_id"] == 17
    assert result["increment"] == 4095


def test_decode_handles_the_largest_possible_snowflake() -> None:
    """64-bit values must not be truncated."""
    result = decode(MAX_SNOWFLAKE)
    assert result["worker_id"] == 31
    assert result["process_id"] == 31
    assert result["increment"] == 4095
    assert result["discord_ms"] == (1 << 42) - 1


def test_cli_accepts_zero_and_maximum_snowflake_ids(cli) -> None:
    assert cli("snowflake", "0").exit_code == 0
    assert cli("snowflake", str(MAX_SNOWFLAKE)).exit_code == 0


@pytest.mark.parametrize(
    "value, message",
    [
        (str(MAX_SNOWFLAKE + 1), "too large to be a 64-bit value"),
        ("-1", "must not be negative"),
    ],
)
def test_cli_reports_snowflake_boundary_errors(cli, value: str, message: str) -> None:
    result = cli("snowflake", value)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert message in result.stderr


def test_encode_matches_the_documented_formula() -> None:
    moment = parse_datetime("2016-04-30T11:18:25.796Z")
    assert encode(moment) == (1462015105796 - 1420070400000) << 22


@pytest.mark.parametrize(
    "timestamp",
    [
        "2015-01-01T00:00:00.000Z",
        "2016-04-30T11:18:25.796Z",
        "2024-12-31T23:59:59.999Z",
        "2026-10-20T08:30:00.001Z",
    ],
)
def test_round_trip_date_to_snowflake_to_date(timestamp: str) -> None:
    """date -> snowflake -> date must return the original instant."""
    assert decode(encode(parse_datetime(timestamp)))["created_at"] == timestamp


def test_encode_rejects_dates_before_the_discord_epoch() -> None:
    with pytest.raises(UsageError, match="before the Discord epoch"):
        encode(parse_datetime("2014-12-31T23:59:59Z"))


def test_encode_accepts_a_naive_timestamp_as_utc() -> None:
    assert encode(parse_datetime("2016-04-30T11:18:25.796")) == encode(
        parse_datetime("2016-04-30T11:18:25.796Z")
    )


def test_encode_respects_a_non_utc_offset() -> None:
    assert encode(parse_datetime("2016-04-30T13:18:25.796+02:00")) == encode(
        parse_datetime("2016-04-30T11:18:25.796Z")
    )


# --- CLI behaviour ------------------------------------------------------


def test_cli_decodes_a_single_id(cli) -> None:
    result = cli("snowflake", "175928847299117063")
    assert result.exit_code == 0
    assert "2016-04-30T11:18:25.796Z" in result.stdout


def test_cli_decodes_multiple_ids_into_a_list(cli) -> None:
    result = cli("--json", "snowflake", "175928847299117063", "80351110224678912")
    assert result.exit_code == 0
    payload = result.json
    assert [item["id"] for item in payload["snowflakes"]] == [
        "175928847299117063",
        "80351110224678912",
    ]


def test_cli_json_for_one_id_is_a_flat_object(cli) -> None:
    payload = cli("--json", "snowflake", "175928847299117063").json
    assert payload["id"] == "175928847299117063"
    assert payload["worker_id"] == 1
    assert payload["source"]["last_verified"]


def test_cli_from_date(cli) -> None:
    payload = cli("--json", "snowflake", "--from-date", "2016-04-30T11:18:25Z").json
    assert payload["snowflake"] == "175928843960320000"
    assert payload["unix_ms"] == 1462015105000


def test_cli_hex_input_is_accepted(cli) -> None:
    payload = cli("--json", "snowflake", "0x2710AF04B000007").json
    assert payload["id"] == str(0x2710AF04B000007)


@pytest.mark.parametrize(
    "argv",
    [
        ("snowflake",),
        ("snowflake", "notanumber"),
        ("snowflake", "-5"),
        ("snowflake", "99999999999999999999999999"),
        ("snowflake", "--from-date", "yesterday"),
        ("snowflake", "--from-date", "2014-01-01T00:00:00Z"),
        ("snowflake", "123", "--from-date", "2016-01-01T00:00:00Z"),
    ],
)
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")
    assert result.stdout == ""


def test_cli_snowflake_reads_from_stdin_when_piped(cli, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("175928847299117063\n"))
    result = cli("snowflake")
    assert result.exit_code == 0
    assert "2016-04-30T11:18:25.796Z" in result.stdout


def test_cli_snowflake_reads_from_dash(cli, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("175928847299117063\n80351110224678912\n"))
    payload = cli("--json", "snowflake", "-").json
    assert [item["id"] for item in payload["snowflakes"]] == [
        "175928847299117063",
        "80351110224678912",
    ]


def test_cli_snowflake_stdin_ignores_blank_lines_and_whitespace(cli, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("\n  175928847299117063  \n\n\n"))
    payload = cli("--json", "snowflake").json
    assert payload["id"] == "175928847299117063"


def test_cli_snowflake_arguments_take_priority_over_stdin(cli, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("80351110224678912\n"))
    payload = cli("--json", "snowflake", "175928847299117063").json
    assert payload["id"] == "175928847299117063"


def test_cli_snowflake_stdin_invalid_line_exits_with_code_2(cli, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("175928847299117063\nnotanumber\n"))
    result = cli("snowflake")
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


def test_cli_snowflake_terminal_without_args_exits_with_code_2(cli, monkeypatch) -> None:
    monkeypatch.setattr("dkit.commands.snowflake._is_terminal", lambda: True)
    monkeypatch.setattr("sys.stdin", io.StringIO("175928847299117063\n"))
    result = cli("snowflake")
    assert result.exit_code == 2
    assert "no snowflake ID given" in result.stderr


def test_cli_snowflake_stdin_empty_exits_with_code_2(cli, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("\n   \n"))
    result = cli("snowflake")
    assert result.exit_code == 2
    assert "no snowflake ID given" in result.stderr


def test_stdin_that_cannot_be_probed_is_not_a_terminal(monkeypatch) -> None:
    closed = io.StringIO()
    closed.close()
    for stdin in (None, closed):
        monkeypatch.setattr("sys.stdin", stdin)
        assert _is_terminal() is False


# --- mentions and message links (issue #42) --------------------------------

#: IDs the official documentation uses in its own examples.
USER_ID = "80351110224678912"
CHANNEL_ID = "103735883630395392"
ROLE_ID = "165511591545143296"
GUILD_ID = "175928847299117063"
MESSAGE_ID = "175928847299117064"


@pytest.mark.parametrize(
    ("mention", "expected_id", "label"),
    [
        (f"<@{USER_ID}>", USER_ID, "user"),
        (f"<@!{USER_ID}>", USER_ID, "user"),
        (f"<#{CHANNEL_ID}>", CHANNEL_ID, "channel"),
        (f"<@&{ROLE_ID}>", ROLE_ID, "role"),
    ],
)
def test_cli_accepts_every_mention_form(cli, mention: str, expected_id: str, label: str) -> None:
    payload = cli("--json", "snowflake", mention).json
    assert payload["id"] == expected_id
    assert payload["label"] == label


def test_cli_mention_payload_is_the_plain_payload_plus_a_label(cli) -> None:
    plain = cli("--json", "snowflake", USER_ID).json
    mention = cli("--json", "snowflake", f"<@{USER_ID}>").json
    assert mention == {**plain, "label": "user"}


def test_cli_text_output_labels_the_kind_of_each_id(cli) -> None:
    result = cli("snowflake", f"<@{USER_ID}>")
    assert result.exit_code == 0
    assert any(line.split() == ["Kind", "user"] for line in result.stdout.splitlines())


def test_cli_game_profile_mentions_are_refused_clearly(cli) -> None:
    result = cli("snowflake", "<@$1402418491272986635>")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "game profile mention" in result.stderr


@pytest.mark.parametrize("mention", ["<>", "<@>", "<@!>", "<#>", "<@&>"])
def test_cli_mention_without_an_id_is_rejected(cli, mention: str) -> None:
    result = cli("snowflake", mention)
    assert result.exit_code == 2
    assert result.stdout == ""


def test_cli_angle_brackets_around_plain_text_are_not_a_mention(cli) -> None:
    result = cli("snowflake", "<hello>")
    assert result.exit_code == 2
    assert "is not a Discord mention" in result.stderr


@pytest.mark.parametrize("text", ["<@123", "@123>", "<#123", "123>"])
def test_cli_unbalanced_angle_brackets_are_not_a_mention(cli, text: str) -> None:
    """A mention needs both brackets, so a half-open one stays an invalid ID."""
    result = cli("snowflake", text)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "not a valid integer" in result.stderr


def test_cli_message_link_labels_each_id_it_carries(cli) -> None:
    link = f"https://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}/{MESSAGE_ID}"
    payload = cli("--json", "snowflake", link).json
    assert [item["id"] for item in payload["snowflakes"]] == [GUILD_ID, CHANNEL_ID, MESSAGE_ID]
    assert [item["label"] for item in payload["snowflakes"]] == ["guild", "channel", "message"]
    # A link that is not a direct message has nothing to warn about.
    assert "warnings" not in payload


@pytest.mark.parametrize(
    "host",
    [
        "discord.com",
        "www.discord.com",
        "canary.discord.com",
        "ptb.discord.com",
        "discordapp.com",
        "www.discordapp.com",
        "canary.discordapp.com",
    ],
)
def test_cli_accepts_every_discord_host(cli, host: str) -> None:
    link = f"https://{host}/channels/{GUILD_ID}/{CHANNEL_ID}/{MESSAGE_ID}"
    assert len(cli("--json", "snowflake", link).json["snowflakes"]) == 3


def test_cli_accepts_plain_http_and_a_trailing_slash(cli) -> None:
    link = f"http://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}/{MESSAGE_ID}/"
    assert len(cli("--json", "snowflake", link).json["snowflakes"]) == 3


@pytest.mark.parametrize(
    "link",
    [
        "ftp://discord.com/channels/1/2/3",
        "file://discord.com/channels/1/2/3",
    ],
)
def test_cli_only_http_links_to_discord_are_decoded(cli, link: str) -> None:
    """Any other scheme stays a plain, invalid ID even on a Discord host."""
    result = cli("snowflake", link)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "not a valid integer" in result.stderr


def test_cli_accepts_a_channel_link_without_a_message_id(cli) -> None:
    link = f"https://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}"
    payload = cli("--json", "snowflake", link).json
    assert [item["label"] for item in payload["snowflakes"]] == ["guild", "channel"]


def test_cli_direct_message_link_skips_the_guild_slot(cli) -> None:
    link = f"https://discord.com/channels/@me/{CHANNEL_ID}/{MESSAGE_ID}"
    payload = cli("--json", "snowflake", link).json
    assert [item["id"] for item in payload["snowflakes"]] == [CHANNEL_ID, MESSAGE_ID]
    assert [item["label"] for item in payload["snowflakes"]] == ["channel", "message"]
    assert "@me" in payload["warnings"][0]


def test_cli_direct_message_link_warning_goes_to_stderr(cli) -> None:
    link = f"https://discord.com/channels/@me/{CHANNEL_ID}/{MESSAGE_ID}"
    result = cli("snowflake", link)
    assert result.exit_code == 0
    assert result.stdout
    assert result.stderr.startswith("warning:")


@pytest.mark.parametrize(
    "link",
    [
        f"https://discord.com/channels/{GUILD_ID}/@me/{MESSAGE_ID}",
        f"https://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}/@me",
    ],
)
def test_cli_direct_message_marker_only_stands_in_for_the_guild_id(cli, link: str) -> None:
    """``@me`` is only meaningful where the guild ID goes."""
    result = cli("snowflake", link)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "not a valid integer" in result.stderr


@pytest.mark.parametrize(
    "link",
    [
        "https://discord.com/",
        "https://discord.com/channels",
        "https://discord.com/channels/1",
        "https://discord.com/channels/1/2/3/4",
        "https://discord.com/foo/1/2",
    ],
)
def test_cli_malformed_message_link_is_reported_as_such(cli, link: str) -> None:
    result = cli("snowflake", link)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "is not a Discord message link" in result.stderr


@pytest.mark.parametrize(
    "text",
    [
        "https://example.com/channels/1/2/3",
        "https://evil-discord.com/channels/1/2/3",
        "https://discord.com.evil.com/channels/1/2/3",
        "https:///channels/1/2/3",
        "https://[oops/channels/1/2/3",
        "discord.com/channels/1/2/3",
    ],
)
def test_cli_text_that_is_not_a_discord_link_falls_back_to_the_integer_error(
    cli, text: str
) -> None:
    """Anything that is not a link to Discord stays a plain, invalid ID."""
    result = cli("snowflake", text)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "not a valid integer" in result.stderr


def test_cli_json_for_a_plain_id_keeps_its_exact_shape(cli) -> None:
    payload = cli("--json", "snowflake", "175928847299117063").json
    assert list(payload) == [
        "id",
        "created_at",
        "unix_ms",
        "discord_ms",
        "worker_id",
        "process_id",
        "increment",
        "source",
    ]


def test_cli_mixes_plain_ids_and_labelled_forms(cli) -> None:
    payload = cli("--json", "snowflake", USER_ID, f"<#{CHANNEL_ID}>").json
    assert payload["snowflakes"][0].get("label") is None
    assert payload["snowflakes"][1]["label"] == "channel"


def test_cli_stdin_accepts_mentions_and_links(cli, monkeypatch) -> None:
    lines = "\n".join(
        [
            f"<@{USER_ID}>",
            f"https://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}/{MESSAGE_ID}",
            "",
        ]
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(lines))
    payload = cli("--json", "snowflake", "-").json
    assert [item["label"] for item in payload["snowflakes"]] == [
        "user",
        "guild",
        "channel",
        "message",
    ]


def test_message_link_data_declares_where_it_comes_from() -> None:
    links = data.load("snowflake")["message_links"]
    assert links["domains"] == ["discord.com", "discordapp.com"]
    assert links["path_prefix"] == "channels"
    assert links["dm_marker"] == "@me"
    assert links["source"].startswith("https://github.com/discord/discord-api-docs")
    assert links["last_verified"]
