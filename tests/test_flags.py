"""Tests for ``dkit flags``."""

from __future__ import annotations

import pytest

from dkit.commands.flags import user_flags
from dkit.core import data
from dkit.core.errors import UsageError

#: VERIFIED_BOT | BOT_HTTP_INTERACTIONS - a value a typical bot user carries.
VERIFIED_HTTP_BOT = 1 << 16 | 1 << 19  # 589824


def test_encode_from_names() -> None:
    flags = user_flags()
    value = flags.value_of(["VERIFIED_BOT", "BOT_HTTP_INTERACTIONS"])
    assert value == VERIFIED_HTTP_BOT == 589824


def test_decode_to_names() -> None:
    flags = user_flags()
    assert [flag.name for flag in flags.flags_in(VERIFIED_HTTP_BOT)] == [
        "VERIFIED_BOT",
        "BOT_HTTP_INTERACTIONS",
    ]


def test_round_trip_every_flag_individually() -> None:
    """name -> number -> name must hold for every known user flag."""
    flags = user_flags()
    for flag in flags:
        value = flags.value_of([flag.name])
        assert [found.name for found in flags.flags_in(value)] == [flag.name]


def test_round_trip_all_flags_at_once() -> None:
    flags = user_flags()
    names = list(flags.names)
    assert flags.value_of(names) == flags.mask
    assert [found.name for found in flags.flags_in(flags.mask)] == names


def test_unassigned_bits_are_reported_as_unknown() -> None:
    flags = user_flags()
    # Bits 4-5, 11-13, 15 and 20-21 are not assigned in the official table.
    assert flags.unknown_bits(1 << 4) == [4]
    assert flags.unknown_bits(1 << 22 | 1 << 23) == [22, 23]


def test_values_above_32_bits_are_handled() -> None:
    flags = user_flags()
    big = 1 << 33 | 1 << 16
    matched = flags.flags_in(big)
    assert [flag.name for flag in matched] == ["VERIFIED_BOT"]
    assert flags.unknown_bits(big) == [33]


def test_unknown_name_raises_with_a_suggestion() -> None:
    with pytest.raises(UsageError) as excinfo:
        user_flags().resolve("ACTIVE_DEVELOPER")
    assert "unknown user flag name" in str(excinfo.value)
    assert "VERIFIED_DEVELOPER" in (excinfo.value.hint or "")


def test_dataset_has_provenance() -> None:
    meta = data.provenance("user_flags")
    assert meta["source"].startswith(
        "https://github.com/discord/discord-api-docs"
    )
    assert meta["source_rendered"].startswith("https://discord.com/developers/docs/")
    assert meta["last_verified"] <= "2026-10-22"


def test_flag_names_and_bits_are_unique() -> None:
    flags = user_flags()
    names = [flag.name for flag in flags]
    bits = [flag.bit for flag in flags]
    assert len(set(names)) == len(names)
    assert len(set(bits)) == len(bits)


# --- CLI behaviour ------------------------------------------------------


def test_cli_number_to_names(cli) -> None:
    payload = cli("--json", "flags", "65536").json
    assert payload["names"] == ["VERIFIED_BOT"]
    assert payload["direction"] == "number-to-names"
    assert payload["value"] == "65536"
    assert payload["value_int"] == 65536


def test_cli_names_to_number(cli) -> None:
    payload = cli("--json", "flags", "--names", "VERIFIED_BOT,STAFF").json
    assert payload["value"] == str(1 << 16 | 1)
    assert payload["direction"] == "names-to-number"


def test_cli_round_trip(cli) -> None:
    encoded = cli("--json", "flags", "--names", "VERIFIED_BOT,TEAM_PSEUDO_USER").json
    decoded = cli("--json", "flags", encoded["value"]).json
    assert decoded["names"] == ["TEAM_PSEUDO_USER", "VERIFIED_BOT"]


def test_cli_accepts_hexadecimal(cli) -> None:
    assert cli("--json", "flags", "0x20000").json["names"] == ["VERIFIED_DEVELOPER"]


def test_cli_reports_unknown_bits_with_a_warning(cli) -> None:
    # 1 << 22 is the community-known Active Developer bit, absent from the
    # official table; it must be reported, not dropped.
    result = cli("flags", str(1 << 22))
    assert result.exit_code == 0
    assert "dkit has no name for" in result.stderr


def test_cli_zero_reports_nothing_set(cli) -> None:
    result = cli("flags", "0")
    assert result.exit_code == 0
    assert "no user flags set" in result.stdout


def test_cli_no_input_is_a_usage_error(cli) -> None:
    result = cli("flags")
    assert result.exit_code == 2
    assert "no user flags given" in result.stderr
    assert "dkit flags 4194304" in result.stderr


def test_cli_names_and_number_cannot_be_combined(cli) -> None:
    result = cli("flags", "131072", "--names", "STAFF")
    assert result.exit_code == 2
    assert "cannot be combined" in result.stderr


def test_cli_non_integer_positional_is_a_usage_error(cli) -> None:
    result = cli("flags", "VERIFIED_BOT")
    assert result.exit_code == 2
    assert "not a valid integer" in result.stderr
    assert "--names" in result.stderr


def test_cli_empty_names_option_is_a_usage_error(cli) -> None:
    result = cli("flags", "--names", ",")
    assert result.exit_code == 2
    assert "did not contain any user flag names" in result.stderr


def test_cli_unknown_name_gives_a_suggestion(cli) -> None:
    result = cli("flags", "--names", "ACTIVE_DEVELOPER")
    assert result.exit_code == 2
    assert "unknown user flag name" in result.stderr
    assert "VERIFIED_DEVELOPER" in result.stderr
