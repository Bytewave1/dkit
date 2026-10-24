"""Tests for ``dkit errors``."""

from __future__ import annotations

from dkit.commands.errors import error_codes


def test_error_codes_load_http_and_json_data() -> None:
    entries = error_codes()
    assert any(entry["type"] == "http" and entry["code"] == "404" for entry in entries)
    assert any(entry["type"] == "json" and entry["code"] == "50013" for entry in entries)


def test_cli_errors_lists_all_codes(cli) -> None:
    result = cli("errors")
    assert result.exit_code == 0
    assert "Discord error codes" in result.stdout
    assert "404" in result.stdout
    assert "50013" in result.stdout
    assert "HTTP" in result.stdout
    assert "JSON" in result.stdout


def test_cli_errors_json_lists_all_codes(cli) -> None:
    payload = cli("--json", "errors").json
    assert payload["mode"] == "all"
    assert payload["count"] == len(payload["error_codes"])
    assert payload["source"]["source"].startswith("https://github.com/discord/discord-api-docs")


def test_cli_errors_look_up_json_error_code(cli) -> None:
    result = cli("--json", "errors", "50013")
    assert result.exit_code == 0
    assert result.json["mode"] == "lookup"
    assert result.json["type"] == "json"
    assert result.json["code"] == "50013"
    assert result.json["description"] == "You lack permissions to perform that action"


def test_cli_errors_look_up_http_error_code(cli) -> None:
    result = cli("--json", "errors", "5XX")
    assert result.exit_code == 0
    assert result.json["type"] == "http"
    assert result.json["code"] == "5xx"


def test_cli_errors_search_is_case_sensitive(cli) -> None:
    result = cli("--json", "errors", "--search", "permissions")
    assert result.exit_code == 0
    payload = result.json
    assert payload["mode"] == "search"
    assert payload["query"] == "permissions"
    assert payload["count"] == len(payload["error_codes"])
    assert payload["count"] > 0
    assert all("permissions" in entry["description"] for entry in payload["error_codes"])

    uppercase = cli("--json", "errors", "--search", "Permissions")
    assert uppercase.exit_code == 0
    assert uppercase.json["count"] == 0


def test_cli_errors_search_empty_and_conflicting_inputs(cli) -> None:
    empty = cli("errors", "--search", "   ")
    assert empty.exit_code == 2
    assert "no search text given" in empty.stderr

    conflicting = cli("errors", "404", "--search", "permissions")
    assert conflicting.exit_code == 2
    assert "cannot be combined with --search" in conflicting.stderr


def test_cli_errors_unknown_code(cli) -> None:
    result = cli("errors", "123456")
    assert result.exit_code == 2
    assert "unknown Discord error code" in result.stderr
    assert "run 'dkit errors'" in result.stderr
