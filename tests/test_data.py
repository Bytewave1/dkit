"""Integrity checks for the bundled JSON data files."""

from __future__ import annotations

import datetime as dt
from importlib import resources

import pytest

from dkit.commands.intents import intent_flags
from dkit.commands.perms import permission_flags
from dkit.core import data


def test_datasets_has_no_duplicates() -> None:
    assert len(set(data.DATASETS)) == len(data.DATASETS)


def test_every_data_file_is_registered() -> None:
    files = {
        entry.name.removesuffix(".json")
        for entry in resources.files(data.DATA_PACKAGE).iterdir()
        if entry.name.endswith(".json")
    }
    registered = set(data.DATASETS)
    assert files == registered, (
        f"files not in DATASETS: {sorted(files - registered)}; "
        f"names in DATASETS without a file: {sorted(registered - files)}"
    )


@pytest.mark.parametrize("name", data.DATASETS)
def test_every_dataset_loads(name: str) -> None:
    assert isinstance(data.load(name), dict)


@pytest.mark.parametrize("name", data.DATASETS)
def test_every_dataset_declares_provenance(name: str) -> None:
    meta = data.provenance(name)
    assert meta["source"].startswith("https://github.com/discord/discord-api-docs")
    # last_verified must be a real ISO date, not a placeholder.
    assert dt.date.fromisoformat(meta["last_verified"]) <= dt.date.today()


@pytest.mark.parametrize("flags", [permission_flags(), intent_flags()])
def test_flag_names_and_bits_are_unique(flags) -> None:
    names = [flag.name for flag in flags]
    bits = [flag.bit for flag in flags]
    assert len(set(names)) == len(names)
    assert len(set(bits)) == len(bits)


@pytest.mark.parametrize("flags", [permission_flags(), intent_flags()])
def test_flag_values_match_their_bit(flags) -> None:
    for flag in flags:
        assert flag.value == 1 << flag.bit


def test_permission_hex_matches_bit() -> None:
    """The ``hex`` field in the data file must agree with ``bit``."""
    for entry in data.load("permissions")["permissions"]:
        assert int(entry["hex"], 16) == 1 << entry["bit"]


def test_known_permission_values() -> None:
    """Spot-check values documented by Discord."""
    flags = permission_flags()
    expected = {
        "CREATE_INSTANT_INVITE": 1 << 0,
        "ADMINISTRATOR": 1 << 3,
        "VIEW_CHANNEL": 1 << 10,
        "SEND_MESSAGES": 1 << 11,
        "MANAGE_ROLES": 1 << 28,
        "USE_APPLICATION_COMMANDS": 1 << 31,
        "MODERATE_MEMBERS": 1 << 40,
        "BYPASS_SLOWMODE": 1 << 52,
    }
    for name, value in expected.items():
        assert flags.resolve(name).value == value


def test_permission_bit_47_is_absent() -> None:
    """Bit 47 is not assigned in the official table."""
    assert 47 not in {flag.bit for flag in permission_flags()}


def test_permissions_exceed_32_and_64_bit_ranges() -> None:
    """Permissions are big integers; nothing may be truncated."""
    flags = permission_flags()
    # Bit 32 is already outside the range of a 32-bit unsigned integer.
    assert flags.resolve("REQUEST_TO_SPEAK").value >= 2**32
    assert flags.mask > 2**32
    assert flags.resolve("BYPASS_SLOWMODE").value == 0x10000000000000
    # The full mask of every known permission still fits in 64 bits.
    assert flags.mask < 2**64


def test_known_intent_values() -> None:
    flags = intent_flags()
    expected = {
        "GUILDS": 1 << 0,
        "GUILD_MEMBERS": 1 << 1,
        "GUILD_PRESENCES": 1 << 8,
        "GUILD_MESSAGES": 1 << 9,
        "MESSAGE_CONTENT": 1 << 15,
        "DIRECT_MESSAGE_POLLS": 1 << 25,
    }
    for name, value in expected.items():
        assert flags.resolve(name).value == value


def test_privileged_intents_are_exactly_the_documented_three() -> None:
    privileged = {flag.name for flag in intent_flags() if flag.privileged}
    assert privileged == {"GUILD_MEMBERS", "GUILD_PRESENCES", "MESSAGE_CONTENT"}


def test_discord_epoch() -> None:
    assert data.load("snowflake")["epoch_ms"] == 1420070400000


def test_oauth2_authorize_url_and_scopes() -> None:
    oauth2 = data.load("oauth2")
    assert oauth2["authorize_url"] == "https://discord.com/oauth2/authorize"
    names = [entry["name"] for entry in oauth2["scopes"]]
    assert "bot" in names
    assert "applications.commands" in names
    assert oauth2["default_scopes"] == ["bot", "applications.commands"]
