"""Tests for ``dkit locales``."""

from __future__ import annotations

import datetime as dt
import re

import pytest

from dkit.commands.locales import locales
from dkit.core import data


def codes(payload: dict) -> list[str]:
    return [entry["code"] for entry in payload["locales"]]


def test_full_listing_returns_every_locale(cli) -> None:
    payload = cli("--json", "locales").json
    assert payload["mode"] == "all"
    assert payload["query"] is None
    assert payload["count"] == len(locales()) == len(payload["locales"])
    by_code = {entry["code"]: entry["name"] for entry in payload["locales"]}
    assert by_code["en-US"] == "English, US"
    assert by_code["es-419"] == "Spanish, LATAM"
    assert by_code["pt-BR"] == "Portuguese, Brazilian"
    assert payload["source"]["last_verified"] == "2026-10-21"


def test_full_listing_text_has_one_row_per_locale(cli) -> None:
    result = cli("locales")
    assert result.exit_code == 0
    for entry in locales():
        row = next(
            line
            for line in result.stdout.splitlines()
            if line.startswith("  " + entry["code"] + " ")
        )
        assert row.endswith(entry["name"])


def test_known_code_returns_its_entry(cli) -> None:
    payload = cli("--json", "locales", "de").json
    assert payload["mode"] == "lookup"
    assert payload["query"] == "de"
    assert payload["count"] == 1
    assert payload["locales"] == [{"code": "de", "name": "German"}]


def test_known_code_text_output(cli) -> None:
    result = cli("locales", "en-US")
    assert result.exit_code == 0
    assert "en-US" in result.stdout
    assert "English, US" in result.stdout


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("en_US", "did you mean en-US?"),
        ("EN-US", "did you mean en-US"),
        ("en", "did you mean en-GB or en-US?"),
        ("pt", "did you mean pt-BR?"),
    ],
)
def test_unknown_code_suggests_the_exact_one(cli, typed: str, expected: str) -> None:
    result = cli("locales", typed)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error: unknown locale:")
    assert expected in result.stderr


def test_unknown_code_without_a_close_match_points_at_search(cli) -> None:
    result = cli("locales", "xx")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error: unknown locale: 'xx'")
    assert "dkit locales --search" in result.stderr


def test_search_matches_language_name_case_insensitively(cli) -> None:
    for text in ("portug", "PORTUG", " Portug "):
        payload = cli("--json", "locales", "--search", text).json
        assert payload["mode"] == "search"
        assert payload["query"] == text.strip()
        assert payload["locales"] == [{"code": "pt-BR", "name": "Portuguese, Brazilian"}]


def test_search_can_match_several_locales(cli) -> None:
    assert codes(cli("--json", "locales", "--search", "chinese").json) == ["zh-CN", "zh-TW"]
    assert codes(cli("--json", "locales", "--search", "english").json) == ["en-GB", "en-US"]


def test_search_with_no_match_is_empty_not_an_error(cli) -> None:
    result = cli("--json", "locales", "--search", "klingon")
    assert result.exit_code == 0
    assert result.json["count"] == 0
    assert result.json["locales"] == []
    text = cli("locales", "--search", "klingon")
    assert text.exit_code == 0
    assert "(no locales match)" in text.stdout


@pytest.mark.parametrize(
    "argv",
    [
        ("locales", "de", "--search", "german"),
        ("locales", "--search", ""),
        ("locales", "--search", "   "),
    ],
)
def test_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error:")


def test_locale_data_is_well_formed() -> None:
    entries = locales()
    seen = [entry["code"] for entry in entries]
    assert len(set(seen)) == len(seen)
    for entry in entries:
        assert set(entry) == {"code", "name"}
        assert entry["name"].strip() == entry["name"] != ""
        # Catches typos such as en_US or EN-us in the data file.
        assert re.fullmatch(r"[a-z]{2}(-([A-Z]{2}|\d{3}))?", entry["code"])
    meta = data.provenance("locales")
    assert meta["source"].endswith("developers/reference.mdx")
    assert dt.date.fromisoformat(meta["last_verified"]) <= dt.date.today()
