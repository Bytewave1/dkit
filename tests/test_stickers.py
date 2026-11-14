"""Tests for ``dkit stickers``."""

from __future__ import annotations

import pytest

from dkit.commands.stickers import groups

EXPECTED = {
    "type": {"STANDARD": 1, "GUILD": 2},
    "format": {"PNG": 1, "APNG": 2, "LOTTIE": 3, "GIF": 4},
}


def test_groups_match_the_documented_values() -> None:
    loaded = groups()
    assert set(loaded) == set(EXPECTED)
    for key, expected in EXPECTED.items():
        assert {e["name"]: e["value"] for e in loaded[key]["values"]} == expected


def test_data_values_are_unique_within_a_group() -> None:
    for group in groups().values():
        names = [e["name"] for e in group["values"]]
        numbers = [e["value"] for e in group["values"]]
        assert len(set(names)) == len(names)
        assert len(set(numbers)) == len(numbers)


def test_cli_lists_every_group(cli) -> None:
    result = cli("stickers")
    assert result.exit_code == 0
    assert "Sticker type (2)" in result.stdout
    assert "Sticker format type (4)" in result.stdout
    assert "STANDARD" in result.stdout
    assert "GUILD" in result.stdout
    assert "PNG" in result.stdout
    assert "LOTTIE" in result.stdout
    assert "a sticker uploaded to a guild for the guild's members" in result.stdout


def test_cli_json_all(cli) -> None:
    payload = cli("--json", "stickers").json
    assert payload["mode"] == "all"
    assert set(payload["groups"]) == {"type", "format"}
    assert payload["groups"]["type"]["title"] == "Sticker type"
    assert len(payload["groups"]["format"]["values"]) == 4
    assert payload["source"]["source"].startswith("https://github.com/discord/discord-api-docs")


def test_cli_lists_one_group(cli) -> None:
    result = cli("stickers", "type")
    assert result.exit_code == 0
    assert "Sticker type (2)" in result.stdout
    assert "STANDARD" in result.stdout
    assert "PNG" not in result.stdout


def test_cli_json_group(cli) -> None:
    payload = cli("--json", "stickers", "format").json
    assert payload["mode"] == "group"
    assert payload["group"] == "format"
    assert payload["count"] == 4
    assert [v["name"] for v in payload["values"]] == list(EXPECTED["format"])


@pytest.mark.parametrize(
    ("group", "value", "name", "number"),
    [
        ("type", "STANDARD", "STANDARD", 1),
        ("type", "1", "STANDARD", 1),
        ("type", "GUILD", "GUILD", 2),
        ("type", "2", "GUILD", 2),
        ("format", "PNG", "PNG", 1),
        ("format", "1", "PNG", 1),
        ("format", "3", "LOTTIE", 3),
        ("format", "lottie", "LOTTIE", 3),
        ("format", "STANDARD", None, None),
    ],
)
def test_cli_lookup(cli, group: str, value: str, name: str | None, number: int | None) -> None:
    result = cli("stickers", group, value)
    if name is None:
        assert result.exit_code == 2
        return
    assert result.exit_code == 0
    assert f"Name         {name}" in result.stdout
    assert f"Value        {number}" in result.stdout


def test_numbers_overlap_so_the_group_decides(cli) -> None:
    assert "STANDARD" in cli("stickers", "type", "1").stdout
    assert "PNG" in cli("stickers", "format", "1").stdout
    assert "GUILD" in cli("stickers", "type", "2").stdout
    assert "APNG" in cli("stickers", "format", "2").stdout


def test_group_is_case_insensitive(cli) -> None:
    assert cli("stickers", "TYPE", "1").exit_code == 0
    assert cli("stickers", "FORMAT", "png").exit_code == 0


def test_cli_lookup_normalises_names(cli) -> None:
    result = cli("stickers", "type", "standard")
    assert result.exit_code == 0
    assert "STANDARD" in result.stdout


def test_description_is_shown_only_when_documented(cli) -> None:
    assert "Description" in cli("stickers", "type", "GUILD").stdout
    assert "Description" not in cli("stickers", "format", "PNG").stdout


def test_cli_json_lookup(cli) -> None:
    payload = cli("--json", "stickers", "format", "3").json
    assert payload["mode"] == "lookup"
    assert payload["group"] == "format"
    assert payload["name"] == "LOTTIE"
    assert payload["value"] == 3
    assert payload["source"]["last_verified"]


def test_cli_search_matches_name_case_insensitively(cli) -> None:
    result = cli("stickers", "format", "--search", "png")
    assert result.exit_code == 0
    assert "Sticker format type values matching 'png' (2)" in result.stdout
    assert "PNG" in result.stdout
    assert "APNG" in result.stdout
    assert "LOTTIE" not in result.stdout


def test_cli_search_matches_description(cli) -> None:
    result = cli("stickers", "type", "--search", "members")
    assert result.exit_code == 0
    assert "GUILD" in result.stdout


def test_cli_search_without_match(cli) -> None:
    result = cli("stickers", "format", "--search", "zzz")
    assert result.exit_code == 0
    assert "(0)" in result.stdout


def test_cli_search_strips_text(cli) -> None:
    payload = cli("--json", "stickers", "format", "--search", "  png  ").json
    assert payload["query"] == "png"
    assert payload["mode"] == "search"
    assert payload["group"] == "format"
    assert payload["count"] == 2
    assert [v["name"] for v in payload["values"]] == ["PNG", "APNG"]


def test_cli_search_is_limited_to_the_group(cli) -> None:
    payload = cli("--json", "stickers", "format", "--search", "guild").json
    assert payload["count"] == 0
    payload = cli("--json", "stickers", "type", "--search", "guild").json
    assert payload["count"] == 1
    assert payload["values"][0]["name"] == "GUILD"


def test_value_and_search_cannot_be_combined(cli) -> None:
    result = cli("stickers", "format", "1", "--search", "png")
    assert result.exit_code == 2
    assert "cannot be combined with --search" in result.stderr


def test_search_needs_a_group(cli) -> None:
    result = cli("stickers", "--search", "png")
    assert result.exit_code == 2
    assert "--search needs a group" in result.stderr


@pytest.mark.parametrize("text", ["", "   "])
def test_search_needs_text(cli, text: str) -> None:
    result = cli("stickers", "format", "--search", text)
    assert result.exit_code == 2
    assert "no search text given" in result.stderr


def test_unknown_group_suggests_a_close_name(cli) -> None:
    result = cli("stickers", "typ")
    assert result.exit_code == 2
    assert "unknown sticker group: 'typ'" in result.stderr
    assert "did you mean type?" in result.stderr


def test_unknown_group_without_suggestion_points_to_the_list(cli) -> None:
    result = cli("stickers", "bogus")
    assert result.exit_code == 2
    assert "run 'dkit stickers' to list every group" in result.stderr


def test_unknown_integer(cli) -> None:
    result = cli("stickers", "format", "9")
    assert result.exit_code == 2
    assert "unknown sticker format type integer: '9'" in result.stderr
    assert "run 'dkit stickers format' to list" in result.stderr


def test_integer_of_another_group_is_unknown(cli) -> None:
    result = cli("stickers", "type", "4")
    assert result.exit_code == 2
    assert "unknown sticker type integer: '4'" in result.stderr


def test_unknown_name_suggests_a_close_name(cli) -> None:
    result = cli("stickers", "format", "PNNG")
    assert result.exit_code == 2
    assert "unknown sticker format type: 'PNNG'" in result.stderr
    assert "did you mean" in result.stderr
    assert "PNG" in result.stderr


def test_unknown_name_without_suggestion_points_to_the_group(cli) -> None:
    result = cli("stickers", "format", "XYZ")
    assert result.exit_code == 2
    assert "run 'dkit stickers format' to list" in result.stderr


def test_hex_value_is_parsed_as_a_number(cli) -> None:
    assert "LOTTIE" in cli("stickers", "format", "0x3").stdout


def test_group_name_is_stripped(cli) -> None:
    result = cli("stickers", " format ", "1")
    assert result.exit_code == 0
    assert "PNG" in result.stdout
