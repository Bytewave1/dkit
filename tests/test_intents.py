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


# --- dkit intents --add / --remove ----------------------------------------


def test_cli_add_from_the_issue(cli) -> None:
    # 33280 = GUILD_MESSAGES | MESSAGE_CONTENT; adding MESSAGE_CONTENT is a no-op
    # for the bit, but adding GUILD_MEMBERS changes the value.
    payload = cli("--json", "intents", "33280", "--add", "GUILD_MEMBERS").json
    assert payload["value"] == "33282"
    assert payload["value_int"] == 33282
    assert payload["names"] == ["GUILD_MEMBERS", "GUILD_MESSAGES", "MESSAGE_CONTENT"]
    assert payload["direction"] == "number-to-names"
    assert payload["unknown_bits"] == []
    assert "source" in payload


def test_cli_remove_from_the_issue(cli) -> None:
    payload = cli("--json", "intents", "33280", "--remove", "GUILD_MESSAGES").json
    assert payload["value"] == "32768"
    assert payload["names"] == ["MESSAGE_CONTENT"]


def test_cli_add_and_remove_together(cli) -> None:
    payload = cli(
        "--json",
        "intents",
        "33280",
        "--add",
        "GUILD_MEMBERS",
        "--remove",
        "GUILD_MESSAGES",
    ).json
    assert payload["value"] == "32770"
    assert payload["names"] == ["GUILD_MEMBERS", "MESSAGE_CONTENT"]


def test_cli_same_name_in_add_and_remove_ends_up_removed(cli) -> None:
    payload = cli("--json", "intents", "0", "--add", "GUILDS", "--remove", "GUILDS").json
    assert payload["value"] == "0"
    assert payload["names"] == []


def test_cli_add_of_already_set_intent_leaves_value_unchanged(cli) -> None:
    payload = cli("--json", "intents", "33280", "--add", "MESSAGE_CONTENT").json
    assert payload["value"] == "33280"
    assert payload["names"] == ["GUILD_MESSAGES", "MESSAGE_CONTENT"]


def test_cli_remove_of_absent_intent_leaves_value_unchanged(cli) -> None:
    payload = cli("--json", "intents", "33280", "--remove", "GUILDS").json
    assert payload["value"] == "33280"
    assert payload["names"] == ["GUILD_MESSAGES", "MESSAGE_CONTENT"]


def test_cli_add_preserves_unknown_bits(cli) -> None:
    value = str(33280 | (1 << 18))
    payload = cli("--json", "intents", value, "--add", "GUILDS").json
    assert payload["value"] == str(33280 | 1 | (1 << 18))
    assert payload["names"] == ["GUILDS", "GUILD_MESSAGES", "MESSAGE_CONTENT"]
    assert payload["unknown_bits"] == [18]
    text = cli("intents", value, "--add", "GUILDS")
    assert "no name for" in text.stderr


def test_cli_remove_preserves_unknown_bits(cli) -> None:
    value = str(33280 | (1 << 18))
    payload = cli("--json", "intents", value, "--remove", "GUILD_MESSAGES").json
    assert payload["value"] == str(32768 | (1 << 18))
    assert payload["names"] == ["MESSAGE_CONTENT"]
    assert payload["unknown_bits"] == [18]


def test_cli_add_unknown_name_suggests(cli) -> None:
    result = cli("intents", "33280", "--add", "GUILD_MEMBER")
    assert result.exit_code == 2
    assert "unknown intent name" in result.stderr
    assert "GUILD_MEMBERS" in result.stderr


def test_cli_remove_unknown_name_suggests(cli) -> None:
    result = cli("intents", "33280", "--remove", "NOPE_NOT_REAL")
    assert result.exit_code == 2
    assert "unknown intent name" in result.stderr


def test_cli_add_text_matches_decode_format(cli) -> None:
    result = cli("intents", "33280", "--add", "GUILD_MEMBERS")
    assert result.exit_code == 0
    assert "Intents 33282" in result.stdout
    assert "GUILD_MEMBERS" in result.stdout
    assert "GUILD_MESSAGES" in result.stdout
    assert "MESSAGE_CONTENT" in result.stdout
    assert "[privileged]" in result.stdout


def test_cli_add_json_stable_keys(cli) -> None:
    payload = cli("--json", "intents", "33280", "--add", "GUILDS").json
    for key in (
        "direction",
        "value",
        "value_int",
        "hex",
        "bit_count",
        "intents",
        "names",
        "privileged",
        "unknown_bits",
        "warnings",
        "source",
    ):
        assert key in payload


@pytest.mark.parametrize(
    "argv, message",
    [
        (
            ("intents", "GUILDS,GUILD_MESSAGES", "--add", "MESSAGE_CONTENT"),
            "--add/--remove need an intents number, not intent names",
        ),
        (
            ("intents", "GUILDS", "--remove", "GUILD_MESSAGES"),
            "--add/--remove need an intents number, not intent names",
        ),
        (
            ("intents", "", "--add", "MESSAGE_CONTENT"),
            "--add/--remove need an intents number to modify",
        ),
        (("intents", "--add", "MESSAGE_CONTENT"), "no intents given"),
        (("intents", "33280", "--add", ""), "--add did not contain any intent names"),
        (
            ("intents", "33280", "--remove", ",,,"),
            "--remove did not contain any intent names",
        ),
    ],
)
def test_cli_add_remove_invalid_input_exits_with_code_2(
    cli, argv: tuple[str, ...], message: str
) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")
    assert message in result.stderr
