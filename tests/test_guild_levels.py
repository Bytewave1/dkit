"""Tests for ``dkit guild-levels``."""

from __future__ import annotations

import pytest

from dkit.commands.guild_levels import groups

EXPECTED = {
    "verification": {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4},
    "notifications": {"ALL_MESSAGES": 0, "ONLY_MENTIONS": 1},
    "content-filter": {"DISABLED": 0, "MEMBERS_WITHOUT_ROLES": 1, "ALL_MEMBERS": 2},
    "mfa": {"NONE": 0, "ELEVATED": 1},
    "premium-tier": {"NONE": 0, "TIER_1": 1, "TIER_2": 2, "TIER_3": 3},
    "age-restriction": {"DEFAULT": 0, "EXPLICIT": 1, "SAFE": 2, "AGE_RESTRICTED": 3},
}


def test_groups_match_the_documented_values() -> None:
    loaded = groups()
    assert set(loaded) == set(EXPECTED)
    for key, expected in EXPECTED.items():
        assert {entry["name"]: entry["value"] for entry in loaded[key]["values"]} == expected


def test_data_values_are_unique_within_each_group() -> None:
    for group in groups().values():
        names = [entry["name"] for entry in group["values"]]
        numbers = [entry["value"] for entry in group["values"]]
        assert len(set(names)) == len(names)
        assert len(set(numbers)) == len(numbers)


def test_cli_lists_every_group(cli) -> None:
    result = cli("guild-levels")
    assert result.exit_code == 0
    for key in EXPECTED:
        assert groups()[key]["title"] in result.stdout
    assert "must have a verified phone number" in result.stdout
    assert "media content sent by members without roles will be scanned" in result.stdout
    assert "Guild Age-Restriction Level (4)" in result.stdout


def test_cli_json_all(cli) -> None:
    payload = cli("--json", "guild-levels").json
    assert payload["mode"] == "all"
    assert set(payload["groups"]) == set(EXPECTED)
    assert payload["groups"]["verification"]["values"][3]["name"] == "HIGH"
    assert payload["source"]["source"].endswith("developers/resources/guild.mdx")
    assert payload["source"]["last_verified"] == "2026-11-08"


@pytest.mark.parametrize(
    ("group", "value", "name", "number"),
    [
        (group, name, name, number)
        for group, values in EXPECTED.items()
        for name, number in values.items()
    ],
)
def test_lookup_by_name_and_number(cli, group: str, value: str, name: str, number: int) -> None:
    by_name = cli("guild-levels", group, value)
    assert by_name.exit_code == 0
    assert f"Name         {name}" in by_name.stdout
    assert f"Value        {number}" in by_name.stdout
    by_number = cli("--json", "guild-levels", group, str(number)).json
    assert by_number["mode"] == "lookup"
    assert by_number["group"] == group
    assert by_number["name"] == name
    assert by_number["value"] == number


def test_cli_lists_one_group_and_json(cli) -> None:
    result = cli("guild-levels", "mfa")
    assert result.exit_code == 0
    assert "MFA Level (2)" in result.stdout
    assert "ELEVATED" in result.stdout
    payload = cli("--json", "guild-levels", "mfa").json
    assert payload["mode"] == "group"
    assert payload["group"] == "mfa"
    assert payload["count"] == 2


def test_group_and_value_names_are_case_and_separator_insensitive(cli) -> None:
    assert "HIGH" in cli("guild-levels", "VERIFICATION", "high").stdout
    assert "TIER_2" in cli("guild-levels", "premium_tier", "tier-2").stdout
    assert "AGE_RESTRICTED" in cli("guild-levels", "age_restriction", "age-restricted").stdout
    assert (
        "MEMBERS_WITHOUT_ROLES"
        in cli("guild-levels", "content_filter", "members-without-roles").stdout
    )


def test_numbers_overlap_between_groups(cli) -> None:
    assert "HIGH" in cli("guild-levels", "verification", "3").stdout
    assert "TIER_3" in cli("guild-levels", "premium-tier", "3").stdout
    assert "AGE_RESTRICTED" in cli("guild-levels", "age-restriction", "3").stdout
    assert "NONE" in cli("guild-levels", "mfa", "0").stdout
    assert "NONE" in cli("guild-levels", "premium-tier", "0").stdout


def test_search_matches_names_and_descriptions_case_insensitively(cli) -> None:
    result = cli("guild-levels", "verification", "--search", "PHONE")
    assert result.exit_code == 0
    assert "VERY_HIGH" in result.stdout
    payload = cli("--json", "guild-levels", "content-filter", "--search", "without roles").json
    assert payload["mode"] == "search"
    assert payload["group"] == "content-filter"
    assert payload["query"] == "without roles"
    assert payload["count"] == 1
    assert payload["values"][0]["name"] == "MEMBERS_WITHOUT_ROLES"


def test_search_matches_names_and_empty_results(cli) -> None:
    payload = cli("--json", "guild-levels", "mfa", "--search", "elev").json
    assert payload["count"] == 1
    assert payload["values"][0]["name"] == "ELEVATED"
    result = cli("guild-levels", "mfa", "--search", "missing")
    assert result.exit_code == 0
    assert "(0)" in result.stdout


def test_search_ignores_entries_without_descriptions(cli) -> None:
    result = cli("guild-levels", "age-restriction", "--search", "missing")
    assert result.exit_code == 0
    assert "(0)" in result.stdout
    assert "DEFAULT" not in result.stdout


def test_unknown_group_suggests_a_close_name(cli) -> None:
    result = cli("guild-levels", "verificatoin")
    assert result.exit_code == 2
    assert "unknown guild level group" in result.stderr
    assert "did you mean verification?" in result.stderr


def test_unknown_group_without_suggestion_lists_groups(cli) -> None:
    result = cli("guild-levels", "xyz")
    assert result.exit_code == 2
    assert "run 'dkit guild-levels' to list every group" in result.stderr


def test_unknown_integer_and_invalid_integer(cli) -> None:
    result = cli("guild-levels", "verification", "9")
    assert result.exit_code == 2
    assert "unknown verification level integer" in result.stderr
    assert "run 'dkit guild-levels verification'" in result.stderr
    invalid = cli("guild-levels", "verification", "0xZZ")
    assert invalid.exit_code == 2
    assert "not a valid integer" in invalid.stderr


def test_unknown_name_suggestion_and_fallback(cli) -> None:
    suggested = cli("guild-levels", "verification", "HIG")
    assert suggested.exit_code == 2
    assert "did you mean HIGH?" in suggested.stderr
    fallback = cli("guild-levels", "verification", "ZZZZZZ")
    assert fallback.exit_code == 2
    assert "run 'dkit guild-levels verification' to list" in fallback.stderr


def test_invalid_argument_combinations(cli) -> None:
    combined = cli("guild-levels", "verification", "3", "--search", "phone")
    assert combined.exit_code == 2
    assert "cannot be combined with --search" in combined.stderr
    missing_group = cli("guild-levels", "--search", "phone")
    assert missing_group.exit_code == 2
    assert "--search needs a group" in missing_group.stderr
    empty = cli("guild-levels", "verification", "--search", "   ")
    assert empty.exit_code == 2
    assert "no search text given" in empty.stderr


def test_unknown_value_name_is_not_found_in_another_group(cli) -> None:
    result = cli("guild-levels", "verification", "TIER_2")
    assert result.exit_code == 2
    assert "unknown verification level" in result.stderr


def test_age_restriction_has_no_invented_descriptions(cli) -> None:
    payload = cli("--json", "guild-levels", "age-restriction", "EXPLICIT").json
    assert payload["description"] is None
    text = cli("guild-levels", "age-restriction", "EXPLICIT").stdout
    assert "Description" not in text
