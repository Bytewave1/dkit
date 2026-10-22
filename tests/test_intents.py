"""Tests for ``dkit intents``."""

from __future__ import annotations

import pytest

from dkit.commands.intents import intent_flags
from dkit.core.errors import UsageError

#: GUILDS | GUILD_MESSAGES | MESSAGE_CONTENT, the common "message bot" value.
MESSAGE_BOT = 1 | 1 << 9 | 1 << 15


def test_encode_from_names() -> None:
    flags = intent_flags()
    value = flags.value_of(["GUILDS", "GUILD_MESSAGES", "MESSAGE_CONTENT"])
    assert value == MESSAGE_BOT == 33281


def test_decode_to_names() -> None:
    flags = intent_flags()
    assert [flag.name for flag in flags.flags_in(MESSAGE_BOT)] == [
        "GUILDS",
        "GUILD_MESSAGES",
        "MESSAGE_CONTENT",
    ]


def test_round_trip_every_intent_individually() -> None:
    """name -> number -> name must hold for every known intent."""
    flags = intent_flags()
    for flag in flags:
        value = flags.value_of([flag.name])
        assert [found.name for found in flags.flags_in(value)] == [flag.name]


def test_round_trip_all_intents_at_once() -> None:
    flags = intent_flags()
    names = list(flags.names)
    assert flags.value_of(names) == flags.mask
    assert [flag.name for flag in flags.flags_in(flags.mask)] == names


def test_unassigned_bits_are_reported_as_unknown() -> None:
    flags = intent_flags()
    # Bits 17-19 and 22-23 are not assigned by Discord.
    assert flags.unknown_bits(1 << 18) == [18]
    assert flags.unknown_bits(1 << 22 | 1 << 23) == [22, 23]


def test_unknown_name_raises_with_a_suggestion() -> None:
    with pytest.raises(UsageError) as excinfo:
        intent_flags().resolve("GUILD_MEMBER")
    assert "unknown intent name" in str(excinfo.value)
    assert "GUILD_MEMBERS" in (excinfo.value.hint or "")


# --- CLI behaviour ------------------------------------------------------


def test_cli_names_to_number(cli) -> None:
    payload = cli("--json", "intents", "GUILDS,GUILD_MESSAGES,MESSAGE_CONTENT").json
    assert payload["value"] == "33281"
    assert payload["value_int"] == 33281
    assert payload["direction"] == "names-to-number"


def test_cli_number_to_names(cli) -> None:
    payload = cli("--json", "intents", "33281").json
    assert payload["names"] == ["GUILDS", "GUILD_MESSAGES", "MESSAGE_CONTENT"]
    assert payload["direction"] == "number-to-names"


def test_cli_round_trip(cli) -> None:
    """names -> number -> names through the CLI."""
    encoded = cli("--json", "intents", "GUILDS,GUILD_VOICE_STATES").json
    decoded = cli("--json", "intents", encoded["value"]).json
    assert decoded["names"] == ["GUILDS", "GUILD_VOICE_STATES"]


def test_cli_accepts_hexadecimal(cli) -> None:
    assert cli("--json", "intents", "0x8201").json["value"] == "33281"


def test_cli_reports_privileged_intents(cli) -> None:
    payload = cli("--json", "intents", "GUILD_MEMBERS,GUILD_PRESENCES,GUILDS").json
    assert payload["privileged"] == ["GUILD_MEMBERS", "GUILD_PRESENCES"]


def test_cli_warns_about_privileged_intents(cli) -> None:
    result = cli("intents", "MESSAGE_CONTENT")
    assert result.exit_code == 0
    assert "Developer Portal" in result.stdout
    assert "4014" in result.stdout
    assert "privileged intent" in result.stderr


def test_cli_does_not_warn_without_privileged_intents(cli) -> None:
    result = cli("intents", "GUILDS")
    assert result.exit_code == 0
    assert result.stderr == ""


def test_cli_zero_reports_nothing_set(cli) -> None:
    result = cli("intents", "0")
    assert result.exit_code == 0
    assert "no intents set" in result.stdout


def test_cli_warns_about_unassigned_bits(cli) -> None:
    result = cli("intents", str(1 << 18))
    assert result.exit_code == 0
    assert "no name for" in result.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ("intents", "GUILD_MEMBER"),
        ("intents", "NOPE_NOT_REAL"),
        ("intents", ""),
        ("intents", "-1"),
    ],
)
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


def test_cli_requires_an_argument(cli) -> None:
    result = cli("intents")
    assert result.exit_code == 2
    assert "no intents given" in result.stderr


def test_cli_list_returns_every_intent_in_bit_order(cli) -> None:
    payload = cli("--json", "intents", "--list").json
    intents = payload["intents"]
    assert payload["total"] == len(intents) == len(intent_flags())

    bits = [item["bit"] for item in intents]
    assert bits == sorted(bits)

    # Stable schema checks
    assert "source" in payload
    assert payload["source"]["source"].endswith("gateway.mdx")
    for intent in intents:
        assert isinstance(intent["name"], str)
        assert isinstance(intent["bit"], int)
        assert isinstance(intent["value"], str)
        assert isinstance(intent["hex"], str)
        assert intent["value"] == str(1 << intent["bit"])
        assert intent["hex"] == f"0x{1 << intent['bit']:016x}"

    privileged = [item for item in intents if item.get("privileged")]
    assert {item["name"] for item in privileged} == {
        "GUILD_MEMBERS",
        "GUILD_PRESENCES",
        "MESSAGE_CONTENT",
    }
    for item in intents:
        if item["name"] not in {"GUILD_MEMBERS", "GUILD_PRESENCES", "MESSAGE_CONTENT"}:
            assert "privileged" not in item


def test_cli_list_text_output(cli) -> None:
    result = cli("intents", "--list")
    assert result.exit_code == 0
    assert f"Intents ({len(intent_flags())})" in result.stdout
    assert "Markers: [privileged]" in result.stdout
    assert "0x0000000000008000" in result.stdout

    def line_for(name: str) -> str:
        matches = [line for line in result.stdout.splitlines() if name in line.split()]
        assert len(matches) == 1
        return matches[0]

    assert "[privileged]" in line_for("MESSAGE_CONTENT")
    assert "[privileged]" not in line_for("GUILDS")


def test_cli_list_conflicting_argument_exits_with_code_2(cli) -> None:
    result = cli("intents", "--list", "GUILDS")
    assert result.exit_code == 2
    assert "--list cannot be combined with NAMES|NUMBER" in result.stderr


def test_cli_list_sorts_unsorted_flags(cli, monkeypatch) -> None:
    flags = list(intent_flags())

    class UnsortedFlagSet:
        def __iter__(self):
            return iter(reversed(flags))

    monkeypatch.setattr("dkit.commands.intents.intent_flags", lambda: UnsortedFlagSet())

    payload = cli("--json", "intents", "--list").json
    bits = [item["bit"] for item in payload["intents"]]
    assert bits == sorted(bits)
    assert bits[0] == 0
    assert bits[-1] == max(f.bit for f in flags)
