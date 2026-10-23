"""Tests for ``dkit scopes``."""

from __future__ import annotations

from dkit.commands.scopes import scopes
from dkit.core import data
from dkit.core.errors import UsageError

APPROVED_PARTNERS_SCOPES = {
    "applications.builds.upload",
    "dm_channels.read",
    "identify.premium",
    "relationships.read",
    "rpc",
    "rpc.activities.write",
    "rpc.notifications.read",
    "rpc.voice.read",
    "rpc.voice.write",
    "voice",
}


def test_list_size_equals_dataset_size() -> None:
    entries = scopes()
    assert len(entries) == len(data.load("oauth2")["scopes"]) == 29


def test_every_scope_has_a_description() -> None:
    for entry in scopes():
        assert entry["name"]
        assert entry["description"]
        assert isinstance(entry["approval_required"], bool)


def test_approval_gated_scopes_are_marked() -> None:
    marked = {entry["name"] for entry in scopes() if entry["approval_required"]}
    assert marked == APPROVED_PARTNERS_SCOPES


def test_exact_lookup() -> None:
    entry = next(e for e in scopes() if e["name"] == "identify")
    assert "without `email`" in entry["description"]


def test_unknown_scope_name_gives_a_suggestion() -> None:
    from dkit.commands.scopes import _lookup

    try:
        _lookup("identify.prem", scopes())
    except UsageError as err:
        assert "unknown OAuth2 scope" in str(err)
        assert "identify.premium" in (err.hint or "")
    else:
        raise AssertionError("expected UsageError")


# --- CLI behaviour ------------------------------------------------------


def test_cli_lists_every_scope(cli) -> None:
    payload = cli("--json", "scopes").json
    assert payload["mode"] == "all"
    assert payload["count"] == 29
    assert [entry["name"] for entry in payload["scopes"]][:2] == [
        "activities.read",
        "activities.write",
    ]


def test_cli_exact_lookup(cli) -> None:
    payload = cli("--json", "scopes", "identify").json
    assert payload["mode"] == "lookup"
    assert payload["scopes"][0]["name"] == "identify"
    assert payload["query"] == "identify"


def test_cli_unknown_name_is_a_usage_error_with_suggestion(cli) -> None:
    result = cli("scopes", "identify.prem")
    assert result.exit_code == 2
    assert "unknown OAuth2 scope" in result.stderr
    assert "identify.premium" in result.stderr


def test_cli_search_matches_name_and_description(cli) -> None:
    payload = cli("--json", "scopes", "--search", "voice").json
    names = [entry["name"] for entry in payload["scopes"]]
    assert "rpc.voice.read" in names
    assert "voice" in names
    assert payload["mode"] == "search"


def test_cli_search_is_case_insensitive(cli) -> None:
    payload = cli("--json", "scopes", "--search", "BEARER").json
    assert any("client credentials" in entry["description"] for entry in payload["scopes"])


def test_cli_lookup_cannot_be_combined_with_search(cli) -> None:
    result = cli("scopes", "identify", "--search", "voice")
    assert result.exit_code == 2
    assert "cannot be combined" in result.stderr


def test_cli_marks_approval_scopes(cli) -> None:
    result = cli("scopes", "rpc.voice.write")
    assert result.exit_code == 0
    assert "required from Discord" in result.stdout
    assert "approved partners" in result.stdout


def test_cli_marks_approval_scopes_in_list_mode(cli) -> None:
    result = cli("scopes", "--search", "voice")
    assert result.exit_code == 0
    # three marked rows plus the legend line at the bottom
    assert result.stdout.count("[approval]") == 4


def test_cli_provenance_in_json(cli) -> None:
    payload = cli("--json", "scopes").json
    assert payload["source"]["source"].startswith("https://github.com/discord/discord-api-docs")
    assert payload["source"]["last_verified"] == "2026-10-22"


def test_search_empty_text_raises_usage_error() -> None:
    from dkit.commands.scopes import _search

    try:
        _search("", scopes())
    except UsageError as err:
        assert "no search text given" in str(err)
        assert "dkit scopes --search" in (err.hint or "")
    else:
        raise AssertionError("expected UsageError")


def test_cli_search_no_matches(cli) -> None:
    result = cli("scopes", "--search", "xyznonexistent")
    assert result.exit_code == 0
    assert "(no scopes match)" in result.stdout


def test_cli_lookup_is_exact_not_casefolded(cli) -> None:
    """`Identify` is not `identify`: lookup stays exact (case-sensitive)."""
    result = cli("scopes", "Identify")
    assert result.exit_code == 2
    assert "unknown OAuth2 scope" in result.stderr


def test_cli_search_matches_a_description_only_term(cli) -> None:
    """`nitro` appears in no scope name, only in `identify.premium`'s description."""
    payload = cli("--json", "scopes", "--search", "nitro").json
    names = [entry["name"] for entry in payload["scopes"]]
    assert "identify.premium" in names
    assert all("nitro" not in name.casefold() for name in names)


def test_cli_search_matches_a_name_only_term(cli) -> None:
    """`identify` appears in no description, so it can only match via the name."""
    payload = cli("--json", "scopes", "--search", "identify").json
    names = [entry["name"] for entry in payload["scopes"]]
    assert "identify" in names


def test_cli_search_matches_a_name_only_term_case_insensitively(cli) -> None:
    """The name branch of the search casefolds, e.g. `IDENTIFY` finds `identify`."""
    payload = cli("--json", "scopes", "--search", "IDENTIFY").json
    names = [entry["name"] for entry in payload["scopes"]]
    assert "identify" in names
