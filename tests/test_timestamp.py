"""Tests for ``dkit timestamp``."""

from __future__ import annotations

import re

import pytest

from dkit.commands.timestamp import timestamp_styles
from dkit.core import data

KNOWN_TIMESTAMP = "2026-10-20T08:30:00Z"
KNOWN_UNIX = 1792485000


def test_known_instant_renders_every_documented_style(cli) -> None:
    payload = cli("--json", "timestamp", KNOWN_TIMESTAMP).json
    assert payload["timestamp"] == "2026-10-20T08:30:00.000Z"
    assert payload["unix"] == KNOWN_UNIX
    assert [entry["style"] for entry in payload["styles"]] == [
        "t",
        "T",
        "d",
        "D",
        "f",
        "F",
        "s",
        "S",
        "R",
    ]
    for entry in payload["styles"]:
        assert entry["tag"] == f"<t:{KNOWN_UNIX}:{entry['style']}>"


def test_style_filter_returns_a_single_tag(cli) -> None:
    payload = cli("--json", "timestamp", KNOWN_TIMESTAMP, "--style", "R").json
    assert payload["styles"] == [
        {
            "style": "R",
            "name": "Relative Time",
            "tag": f"<t:{KNOWN_UNIX}:R>",
            "example": "4 years ago",
        }
    ]


def test_snowflake_path_uses_the_ids_creation_time(cli) -> None:
    payload = cli("--json", "timestamp", "--from-snowflake", "175928847299117063").json
    assert payload["timestamp"] == "2016-04-30T11:18:25.796Z"
    assert payload["unix"] == 1462015105
    assert payload["styles"][0]["tag"] == "<t:1462015105:t>"


def test_tags_always_use_seconds_not_milliseconds(cli) -> None:
    payload = cli("--json", "timestamp", "2026-10-20T08:30:00.123Z").json
    for entry in payload["styles"]:
        assert re.fullmatch(r"<t:\d{10}:[tTdDfFsSR]>", entry["tag"])


def test_non_utc_offsets_name_the_same_instant(cli) -> None:
    payload = cli("--json", "timestamp", "2026-10-20T10:30:00+02:00").json
    assert payload["unix"] == KNOWN_UNIX


def test_text_output_lists_the_tags(cli) -> None:
    result = cli("timestamp", KNOWN_TIMESTAMP, "--style", "f")
    assert result.exit_code == 0
    assert f"<t:{KNOWN_UNIX}:f>" in result.stdout
    assert str(KNOWN_UNIX) in result.stdout


def test_unknown_style_suggests_a_known_one(cli) -> None:
    result = cli("timestamp", KNOWN_TIMESTAMP, "--style", "r")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error:")
    assert "did you mean R?" in result.stderr


def test_unknown_style_without_a_close_match_lists_the_valid_ones(cli) -> None:
    result = cli("timestamp", KNOWN_TIMESTAMP, "--style", "q")
    assert result.exit_code == 2
    assert "valid styles: t, T, d, D, f, F, s, S, R" in result.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ("timestamp",),
        ("timestamp", "not-a-date"),
        ("timestamp", "--style", "R"),
        ("timestamp", KNOWN_TIMESTAMP, "--from-snowflake", "175928847299117063"),
        ("timestamp", "--from-snowflake", "notanumber"),
        ("timestamp", "--from-snowflake", "99999999999999999999999999"),
    ],
)
def test_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")
    assert result.stdout == ""


def test_styles_are_single_case_sensitive_characters() -> None:
    styles = timestamp_styles()
    characters = [entry["style"] for entry in styles]
    assert len(set(characters)) == len(characters)
    assert all(re.fullmatch(r"[tTdDfFsSR]", character) for character in characters)
    assert "f" in characters  # the documented default
    payload = data.provenance("timestamp_styles")
    assert payload["source"].endswith("developers/reference.mdx")
    assert payload["last_verified"] == "2026-10-21"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_timestamp_is_rejected(cli, value: str) -> None:
    result = cli("timestamp", value)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error: timestamp is empty")
