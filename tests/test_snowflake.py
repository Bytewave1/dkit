"""Tests for ``dkit snowflake``."""

from __future__ import annotations

import io

import pytest

from dkit.commands.snowflake import MAX_SNOWFLAKE, decode, encode
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
