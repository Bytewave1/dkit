"""Tests for the input parsing functions in ``dkit.core.parse``."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dkit.core.errors import UsageError
from dkit.core.parse import (
    format_datetime,
    looks_like_int,
    normalise_name,
    parse_datetime,
    parse_int,
    split_names,
)


def test_parse_int_valid() -> None:
    assert parse_int("42") == 42
    assert parse_int("  1_000_000  ") == 1000000
    assert parse_int("0x2a") == 42
    assert parse_int("0X2A") == 42
    assert parse_int("0b101010") == 42
    assert parse_int("0o52") == 42


@pytest.mark.parametrize("raw", ["", "   ", "__"])
def test_parse_int_empty_raises(raw: str) -> None:
    with pytest.raises(UsageError, match="value is empty"):
        parse_int(raw)


def test_parse_int_negative_raises() -> None:
    with pytest.raises(UsageError, match="must not be negative"):
        parse_int("-5")


@pytest.mark.parametrize("raw", ["abc", "0xG", "12a", "foo_bar"])
def test_parse_int_invalid_format_raises(raw: str) -> None:
    with pytest.raises(UsageError, match="is not a valid integer"):
        parse_int(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("42", True),
        ("0", True),
        ("0x1a", True),
        ("0b101", True),
        ("0o77", True),
        ("", False),
        ("   ", False),
        ("__", False),
        ("0x", False),
        ("SEND_MESSAGES", False),
        ("abc", False),
    ],
)
def test_looks_like_int(raw: str, expected: bool) -> None:
    assert looks_like_int(raw) is expected


def test_normalise_name() -> None:
    assert normalise_name("send-messages") == "SEND_MESSAGES"
    assert normalise_name("  manage roles  ") == "MANAGE_ROLES"
    assert normalise_name("ADMINISTRATOR") == "ADMINISTRATOR"


def test_split_names() -> None:
    assert split_names("SEND_MESSAGES, MANAGE_ROLES; VIEW_CHANNEL") == [
        "SEND_MESSAGES",
        "MANAGE_ROLES",
        "VIEW_CHANNEL",
    ]
    assert split_names(" , ; ") == []


def test_parse_datetime_valid() -> None:
    dt = parse_datetime("2026-10-20T08:30:00Z")
    assert dt == datetime(2026, 10, 20, 8, 30, 0, tzinfo=timezone.utc)

    # Naive timestamp assumes UTC
    dt_naive = parse_datetime("2026-10-20T08:30:00")
    assert dt_naive == datetime(2026, 10, 20, 8, 30, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("raw", ["", "   "])
def test_parse_datetime_empty_raises(raw: str) -> None:
    with pytest.raises(UsageError, match="date is empty"):
        parse_datetime(raw)


def test_parse_datetime_invalid_raises() -> None:
    with pytest.raises(UsageError, match="is not a valid ISO-8601 timestamp"):
        parse_datetime("not-a-date")


def test_format_datetime() -> None:
    dt = datetime(2026, 10, 20, 8, 30, 0, 123456, tzinfo=timezone.utc)
    assert format_datetime(dt) == "2026-10-20T08:30:00.123Z"


def test_parse_datetime_converts_non_utc_offset_to_utc() -> None:
    dt = parse_datetime("2026-10-20T10:30:00+02:00")
    assert dt.hour == 8
    assert dt.utcoffset() is not None
    assert dt.utcoffset().total_seconds() == 0
    assert dt.tzinfo == timezone.utc
    assert dt == datetime(2026, 10, 20, 8, 30, 0, tzinfo=timezone.utc)
