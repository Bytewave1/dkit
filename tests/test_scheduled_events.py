"""Tests for ``dkit scheduled-events``."""

from __future__ import annotations

import pytest

from dkit.commands.scheduled_events import groups
from dkit.core import data

EXPECTED = {
    "entity": {"STAGE_INSTANCE": 1, "VOICE": 2, "EXTERNAL": 3},
    "privacy": {"GUILD_ONLY": 2},
    "status": {"SCHEDULED": 1, "ACTIVE": 2, "COMPLETED": 3, "CANCELED": 4},
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


def test_documented_transitions_use_known_statuses() -> None:
    pairs = [(t["from"], t["to"]) for t in data.load("scheduled_event_types")["status_transitions"]]
    assert pairs == [("SCHEDULED", "ACTIVE"), ("ACTIVE", "COMPLETED"), ("SCHEDULED", "CANCELED")]
    names = {e["name"] for e in groups()["status"]["values"]}
    assert {name for pair in pairs for name in pair} <= names


def test_terminal_statuses_never_start_a_transition() -> None:
    terminal = {e["name"] for e in groups()["status"]["values"] if e["terminal"]}
    assert terminal == {"COMPLETED", "CANCELED"}
    started = {t["from"] for t in data.load("scheduled_event_types")["status_transitions"]}
    assert not terminal & started


def test_cli_lists_every_group(cli) -> None:
    result = cli("scheduled-events")
    assert result.exit_code == 0
    assert "Entity type (3)" in result.stdout
    assert "Privacy level (1)" in result.stdout
    assert "Status (4)" in result.stdout
    assert "STAGE_INSTANCE" in result.stdout
    assert "GUILD_ONLY" in result.stdout
    assert "the scheduled event is only accessible to guild members" in result.stdout
    assert "CANCELED   (final)" in result.stdout


def test_cli_json_all(cli) -> None:
    payload = cli("--json", "scheduled-events").json
    assert payload["mode"] == "all"
    assert set(payload["groups"]) == {"entity", "privacy", "status"}
    assert payload["groups"]["entity"]["title"] == "Entity type"
    assert len(payload["groups"]["status"]["values"]) == 4
    assert payload["source"]["source"].startswith("https://github.com/discord/discord-api-docs")


def test_cli_lists_one_group(cli) -> None:
    result = cli("scheduled-events", "entity")
    assert result.exit_code == 0
    assert "Entity type (3)" in result.stdout
    assert "EXTERNAL" in result.stdout
    assert "GUILD_ONLY" not in result.stdout


def test_cli_json_group(cli) -> None:
    payload = cli("--json", "scheduled-events", "status").json
    assert payload["mode"] == "group"
    assert payload["group"] == "status"
    assert payload["count"] == 4
    assert [v["name"] for v in payload["values"]] == list(EXPECTED["status"])


@pytest.mark.parametrize(
    ("group", "value", "name", "number"),
    [
        ("entity", "EXTERNAL", "EXTERNAL", 3),
        ("entity", "3", "EXTERNAL", 3),
        ("privacy", "GUILD_ONLY", "GUILD_ONLY", 2),
        ("privacy", "2", "GUILD_ONLY", 2),
        ("status", "4", "CANCELED", 4),
        ("status", "canceled", "CANCELED", 4),
        ("status", "STAGE_INSTANCE", None, None),
    ],
)
def test_cli_lookup(cli, group: str, value: str, name: str | None, number: int | None) -> None:
    result = cli("scheduled-events", group, value)
    if name is None:
        assert result.exit_code == 2
        return
    assert result.exit_code == 0
    assert f"Name         {name}" in result.stdout
    assert f"Value        {number}" in result.stdout


def test_numbers_overlap_so_the_group_decides(cli) -> None:
    assert "VOICE" in cli("scheduled-events", "entity", "2").stdout
    assert "GUILD_ONLY" in cli("scheduled-events", "privacy", "2").stdout
    assert "ACTIVE" in cli("scheduled-events", "status", "2").stdout


def test_group_is_case_insensitive(cli) -> None:
    assert cli("scheduled-events", "STATUS", "4").exit_code == 0


def test_cli_lookup_normalises_names(cli) -> None:
    result = cli("scheduled-events", "entity", "stage-instance")
    assert result.exit_code == 0
    assert "STAGE_INSTANCE" in result.stdout


def test_terminal_status_is_marked(cli) -> None:
    final = cli("scheduled-events", "status", "COMPLETED").stdout
    assert "can no longer be updated" in final
    open_status = cli("scheduled-events", "status", "ACTIVE").stdout
    assert "can no longer be updated" not in open_status


def test_description_is_shown_only_when_documented(cli) -> None:
    assert "Description" in cli("scheduled-events", "privacy", "GUILD_ONLY").stdout
    assert "Description" not in cli("scheduled-events", "entity", "VOICE").stdout


def test_cli_json_lookup(cli) -> None:
    payload = cli("--json", "scheduled-events", "status", "4").json
    assert payload["mode"] == "lookup"
    assert payload["group"] == "status"
    assert payload["name"] == "CANCELED"
    assert payload["value"] == 4
    assert payload["terminal"] is True
    assert payload["source"]["last_verified"]


def test_cli_search_matches_name_case_insensitively(cli) -> None:
    result = cli("scheduled-events", "status", "--search", "ACT")
    assert result.exit_code == 0
    assert "Status values matching 'ACT' (1)" in result.stdout
    assert "ACTIVE" in result.stdout
    assert "CANCELED" not in result.stdout


def test_cli_search_matches_description(cli) -> None:
    result = cli("scheduled-events", "privacy", "--search", "MEMBERS")
    assert result.exit_code == 0
    assert "GUILD_ONLY" in result.stdout


def test_cli_search_without_match(cli) -> None:
    result = cli("scheduled-events", "status", "--search", "zzz")
    assert result.exit_code == 0
    assert "(0)" in result.stdout


def test_cli_search_strips_text(cli) -> None:
    payload = cli("--json", "scheduled-events", "status", "--search", "  act  ").json
    assert payload["query"] == "act"
    assert payload["mode"] == "search"
    assert payload["group"] == "status"
    assert payload["count"] == 1
    assert payload["values"][0]["name"] == "ACTIVE"


def test_cli_search_is_limited_to_the_group(cli) -> None:
    payload = cli("--json", "scheduled-events", "entity", "--search", "e").json
    assert {v["name"] for v in payload["values"]} == {"STAGE_INSTANCE", "VOICE", "EXTERNAL"}
    payload = cli("--json", "scheduled-events", "privacy", "--search", "voice").json
    assert payload["count"] == 0


def test_cli_transitions(cli) -> None:
    result = cli("scheduled-events", "--transitions")
    assert result.exit_code == 0
    assert "Valid status transitions (3)" in result.stdout
    assert "SCHEDULED -> ACTIVE" in result.stdout
    assert "ACTIVE -> COMPLETED" in result.stdout
    assert "SCHEDULED -> CANCELED" in result.stdout
    assert "can no longer be updated" in result.stdout


def test_cli_json_transitions(cli) -> None:
    payload = cli("--json", "scheduled-events", "--transitions").json
    assert payload["mode"] == "transitions"
    assert payload["count"] == 3
    assert payload["transitions"][0] == {"from": "SCHEDULED", "to": "ACTIVE"}
    assert payload["terminal"] == ["COMPLETED", "CANCELED"]
    assert "can no longer be updated" in payload["note"]


@pytest.mark.parametrize(
    "argv",
    [
        ("--transitions", "status"),
        ("status", "4", "--transitions"),
        ("status", "--search", "a", "--transitions"),
        ("--transitions", "--search", "a"),
    ],
)
def test_transitions_cannot_be_combined(cli, argv: tuple[str, ...]) -> None:
    result = cli("scheduled-events", *argv)
    assert result.exit_code == 2
    assert "--transitions cannot be combined" in result.stderr


def test_value_and_search_cannot_be_combined(cli) -> None:
    result = cli("scheduled-events", "status", "4", "--search", "a")
    assert result.exit_code == 2
    assert "cannot be combined with --search" in result.stderr


def test_search_needs_a_group(cli) -> None:
    result = cli("scheduled-events", "--search", "act")
    assert result.exit_code == 2
    assert "--search needs a group" in result.stderr


@pytest.mark.parametrize("text", ["", "   "])
def test_search_needs_text(cli, text: str) -> None:
    result = cli("scheduled-events", "status", "--search", text)
    assert result.exit_code == 2
    assert "no search text given" in result.stderr


def test_unknown_group_suggests_a_close_name(cli) -> None:
    result = cli("scheduled-events", "stat")
    assert result.exit_code == 2
    assert "unknown scheduled event group: 'stat'" in result.stderr
    assert "did you mean status?" in result.stderr


def test_unknown_group_without_suggestion_points_to_the_list(cli) -> None:
    result = cli("scheduled-events", "bogus")
    assert result.exit_code == 2
    assert "run 'dkit scheduled-events' to list every group" in result.stderr


def test_unknown_integer(cli) -> None:
    result = cli("scheduled-events", "status", "9")
    assert result.exit_code == 2
    assert "unknown status integer: '9'" in result.stderr
    assert "run 'dkit scheduled-events status' to list" in result.stderr


def test_integer_of_another_group_is_unknown(cli) -> None:
    result = cli("scheduled-events", "privacy", "1")
    assert result.exit_code == 2
    assert "unknown privacy level integer: '1'" in result.stderr


def test_unknown_name_suggests_a_close_name(cli) -> None:
    result = cli("scheduled-events", "status", "CANCELD")
    assert result.exit_code == 2
    assert "unknown status: 'CANCELD'" in result.stderr
    assert "did you mean CANCELED?" in result.stderr


def test_unknown_name_without_suggestion_points_to_the_group(cli) -> None:
    result = cli("scheduled-events", "status", "XYZ")
    assert result.exit_code == 2
    assert "run 'dkit scheduled-events status' to list" in result.stderr


def test_hex_value_is_parsed_as_a_number(cli) -> None:
    assert "CANCELED" in cli("scheduled-events", "status", "0x4").stdout


def test_group_name_is_stripped(cli) -> None:
    result = cli("scheduled-events", " status ", "4")
    assert result.exit_code == 0
    assert "CANCELED" in result.stdout


def test_only_terminal_statuses_are_marked_final_in_lists(cli) -> None:
    lines = cli("scheduled-events", "status").stdout.splitlines()
    marked = {line.split()[1] for line in lines if "(final)" in line}
    assert marked == {"COMPLETED", "CANCELED"}
