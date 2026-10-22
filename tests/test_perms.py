"""Tests for ``dkit perms``."""

from __future__ import annotations

import pytest

from dkit.commands.perms import permission_flags
from dkit.core.errors import UsageError


def test_decode_single_bit() -> None:
    flags = permission_flags()
    assert [flag.name for flag in flags.flags_in(2048)] == ["SEND_MESSAGES"]


def test_decode_combination() -> None:
    flags = permission_flags()
    value = 1 << 11 | 1 << 14 | 1 << 28
    assert [flag.name for flag in flags.flags_in(value)] == [
        "SEND_MESSAGES",
        "EMBED_LINKS",
        "MANAGE_ROLES",
    ]


def test_decode_zero_is_empty() -> None:
    assert permission_flags().flags_in(0) == []


def test_encode_from_names() -> None:
    flags = permission_flags()
    assert flags.value_of(["SEND_MESSAGES", "MANAGE_ROLES"]) == 268437504


def test_encode_is_order_independent_and_idempotent() -> None:
    flags = permission_flags()
    assert flags.value_of(["MANAGE_ROLES", "SEND_MESSAGES"]) == flags.value_of(
        ["SEND_MESSAGES", "MANAGE_ROLES"]
    )
    assert flags.value_of(["SEND_MESSAGES", "SEND_MESSAGES"]) == 2048


def test_names_are_case_and_separator_insensitive() -> None:
    flags = permission_flags()
    assert flags.resolve("send_messages").name == "SEND_MESSAGES"
    assert flags.resolve("Send-Messages").name == "SEND_MESSAGES"
    assert flags.resolve("  send messages  ").name == "SEND_MESSAGES"


def test_round_trip_every_permission_individually() -> None:
    """name -> number -> name must hold for every known permission."""
    flags = permission_flags()
    for flag in flags:
        value = flags.value_of([flag.name])
        assert [found.name for found in flags.flags_in(value)] == [flag.name]


def test_round_trip_all_permissions_at_once() -> None:
    flags = permission_flags()
    names = list(flags.names)
    value = flags.value_of(names)
    assert value == flags.mask
    assert [flag.name for flag in flags.flags_in(value)] == names


def test_unknown_bits_are_reported() -> None:
    flags = permission_flags()
    # Bit 47 is unassigned, bit 63 is far beyond anything documented.
    value = flags.mask | 1 << 47 | 1 << 63
    assert flags.unknown_bits(value) == [47, 63]


def test_unknown_name_raises_with_a_suggestion() -> None:
    with pytest.raises(UsageError) as excinfo:
        permission_flags().resolve("SEND_MESSAGE")
    assert "unknown permission name" in str(excinfo.value)
    assert "SEND_MESSAGES" in (excinfo.value.hint or "")


# --- CLI behaviour ------------------------------------------------------


def test_cli_decode(cli) -> None:
    result = cli("perms", "2048")
    assert result.exit_code == 0
    assert "SEND_MESSAGES" in result.stdout


def test_cli_decode_json(cli) -> None:
    payload = cli("--json", "perms", "268437504").json
    assert payload["names"] == ["SEND_MESSAGES", "MANAGE_ROLES"]
    assert payload["value"] == "268437504"
    assert payload["hex"] == "0x0000000010000800"
    assert payload["unknown_bits"] == []


def test_cli_encode_json(cli) -> None:
    payload = cli("--json", "perms", "--names", "SEND_MESSAGES,MANAGE_ROLES").json
    assert payload["value"] == "268437504"
    assert payload["names"] == ["SEND_MESSAGES", "MANAGE_ROLES"]


def test_cli_round_trip_through_the_cli(cli) -> None:
    """names -> number -> names, both directions through the CLI."""
    encoded = cli("--json", "perms", "--names", "VIEW_CHANNEL,SEND_MESSAGES").json
    decoded = cli("--json", "perms", encoded["value"]).json
    assert decoded["names"] == ["VIEW_CHANNEL", "SEND_MESSAGES"]


def test_cli_accepts_hexadecimal(cli) -> None:
    assert cli("--json", "perms", "0x800").json["names"] == ["SEND_MESSAGES"]


def test_cli_value_is_a_string_for_big_integers(cli) -> None:
    """Permissions are emitted as strings, as the Discord API itself does."""
    payload = cli("--json", "perms", "--names", "BYPASS_SLOWMODE").json
    assert payload["value"] == "4503599627370496"
    assert isinstance(payload["value"], str)


def test_cli_warns_about_administrator(cli) -> None:
    result = cli("perms", "8")
    assert result.exit_code == 0
    assert "ADMINISTRATOR" in result.stderr


def test_cli_warns_about_unknown_bits(cli) -> None:
    result = cli("perms", str(1 << 47))
    assert result.exit_code == 0
    assert "no name for" in result.stderr


def test_cli_zero_reports_nothing_set(cli) -> None:
    result = cli("perms", "0")
    assert result.exit_code == 0
    assert "no permissions set" in result.stdout


@pytest.mark.parametrize(
    "argv",
    [
        ("perms",),
        ("perms", "--names", "SEND_MESSAGE"),
        ("perms", "--names", "NOPE_NOT_REAL"),
        ("perms", "--names", ""),
        ("perms", "--names", ",,,"),
        ("perms", "abc"),
        ("perms", "-1"),
        ("perms", "8", "--names", "ADMINISTRATOR"),
    ],
)
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


# --- dkit perms --diff --------------------------------------------------


def test_cli_diff_overlapping_values_from_the_issue(cli) -> None:
    payload = cli("--json", "perms", "268437504", "--diff", "274878286912").json
    assert payload["identical"] is False
    assert payload["removed"]["names"] == ["MANAGE_ROLES"]
    assert payload["added"]["names"] == [
        "ADD_REACTIONS",
        "VIEW_CHANNEL",
        "EMBED_LINKS",
        "ATTACH_FILES",
        "READ_MESSAGE_HISTORY",
        "USE_EXTERNAL_EMOJIS",
        "SEND_MESSAGES_IN_THREADS",
    ]
    assert payload["unchanged"]["names"] == ["SEND_MESSAGES"]
    assert payload["unchanged"]["bit_count"] == 1


def test_cli_diff_text_prints_all_three_groups(cli) -> None:
    result = cli("perms", "268437504", "--diff", "274878286912")
    assert result.exit_code == 0
    assert "Removed (1)" in result.stdout
    assert "Added (7)" in result.stdout
    assert "Unchanged (1)" in result.stdout
    assert "MANAGE_ROLES" in result.stdout
    assert "SEND_MESSAGES_IN_THREADS" in result.stdout


def test_cli_diff_identical_values(cli) -> None:
    payload = cli("--json", "perms", "2048", "--diff", "2048").json
    assert payload["identical"] is True
    assert payload["removed"]["names"] == []
    assert payload["added"]["names"] == []
    assert payload["unchanged"]["names"] == ["SEND_MESSAGES"]
    assert "identical values" in cli("perms", "2048", "--diff", "2048").stdout


def test_cli_diff_disjoint_values(cli) -> None:
    payload = cli("--json", "perms", "2048", "--diff", "1024").json
    assert payload["removed"]["names"] == ["SEND_MESSAGES"]
    assert payload["added"]["names"] == ["VIEW_CHANNEL"]
    assert payload["unchanged"]["names"] == []
    assert payload["unchanged"]["bit_count"] == 0


def test_cli_diff_is_symmetric(cli) -> None:
    forward = cli("--json", "perms", "5", "--diff", "6").json
    backward = cli("--json", "perms", "6", "--diff", "5").json
    assert forward["removed"]["names"] == backward["added"]["names"]
    assert forward["added"]["names"] == backward["removed"]["names"]
    assert forward["unchanged"]["names"] == backward["unchanged"]["names"]


def test_cli_diff_reports_unknown_bits_that_are_removed(cli) -> None:
    result = cli("--json", "perms", str(2048 | 1 << 47), "--diff", "2048")
    payload = result.json
    assert payload["removed"]["unknown_bits"] == [47]
    assert payload["added"]["unknown_bits"] == []
    assert payload["unchanged"]["unknown_bits"] == []
    text = cli("perms", str(2048 | 1 << 47), "--diff", "2048")
    assert "unknown bits: 47" in text.stdout
    assert "removed part contains bits dkit has no name for: 47" in text.stderr


def test_cli_diff_reports_unknown_bits_present_in_both(cli) -> None:
    value = str(1 << 47)
    payload = cli("--json", "perms", value, "--diff", value).json
    assert payload["unchanged"]["unknown_bits"] == [47]
    assert payload["removed"]["unknown_bits"] == []
    assert payload["added"]["unknown_bits"] == []
    assert (
        "unchanged part contains bits dkit has no name for: 47"
        in cli("perms", value, "--diff", value).stderr
    )


def test_cli_diff_accepts_hexadecimal_for_both_values(cli) -> None:
    payload = cli("--json", "perms", "0x800", "--diff", "0x400").json
    assert payload["removed"]["names"] == ["SEND_MESSAGES"]
    assert payload["added"]["names"] == ["VIEW_CHANNEL"]
    assert payload["first"]["value"] == "2048"
    assert payload["second"]["value"] == "1024"


def test_cli_diff_json_values_are_strings(cli) -> None:
    big = str(1 << 52)
    payload = cli("--json", "perms", "0", "--diff", big).json
    assert payload["second"]["value"] == big
    assert payload["added"]["value"] == big
    for key in ("first", "second", "removed", "added", "unchanged"):
        assert isinstance(payload[key]["value"], str)


def test_cli_diff_accepts_json_flag_after_the_command(cli) -> None:
    payload = cli("perms", "5", "--diff", "6", "--json").json
    assert payload["removed"]["names"] == ["CREATE_INSTANT_INVITE"]
    assert payload["added"]["names"] == ["KICK_MEMBERS"]
    assert payload["unchanged"]["names"] == ["BAN_MEMBERS"]


@pytest.mark.parametrize(
    "argv",
    [
        ("perms", "5", "--diff", "abc"),
        ("perms", "5", "--diff", "-1"),
        ("perms", "5", "--diff", ""),
        ("perms", "abc", "--diff", "6"),
        ("perms", "--diff", "6"),
        ("perms", "5", "--diff", "6", "--names", "SEND_MESSAGES"),
    ],
)
def test_cli_diff_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


def test_cli_list_returns_every_permission_in_bit_order(cli) -> None:
    payload = cli("--json", "perms", "--list").json
    permissions = payload["permissions"]
    assert payload["total"] == len(permissions) == len(permission_flags())

    bits = [item["bit"] for item in permissions]
    assert bits == sorted(bits)

    # Check a permission with value exceeding 32 bits (2**32 = 4294967296)
    high_bit_perm = next(p for p in permissions if p["bit"] > 32)
    assert int(high_bit_perm["value"]) > 2**32
    assert high_bit_perm["value"] == str(1 << high_bit_perm["bit"])
    assert high_bit_perm["hex"] == f"0x{1 << high_bit_perm['bit']:016x}"

    # Stable schema checks
    assert "source" in payload
    assert payload["source"]["source"].endswith("permissions.mdx")
    for perm in permissions:
        assert isinstance(perm["name"], str)
        assert isinstance(perm["bit"], int)
        assert isinstance(perm["value"], str)
        assert isinstance(perm["hex"], str)
        assert isinstance(perm["description"], str)


def test_cli_list_text_output(cli) -> None:
    result = cli("perms", "--list")
    assert result.exit_code == 0
    assert f"Permissions ({len(permission_flags())})" in result.stdout
    assert "Markers: [T/V/S] = channel scope" in result.stdout
    assert "SEND_MESSAGES" in result.stdout
    assert "0x0000000000000800" in result.stdout
    assert "CREATE_INSTANT_INVITE" in result.stdout


@pytest.mark.parametrize(
    "argv, message",
    [
        (("perms", "--list", "2048"), "--list cannot be combined with a permissions number"),
        (("perms", "--list", "--names", "SEND_MESSAGES"), "--list cannot be combined with --names"),
        (("perms", "--list", "--diff", "2048"), "--list cannot be combined with --diff"),
    ],
)
def test_cli_list_conflicting_options_exit_code_2(cli, argv: tuple[str, ...], message: str) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert message in result.stderr


def test_cli_list_sorts_unsorted_flags(cli, monkeypatch) -> None:
    flags = list(permission_flags())

    class UnsortedFlagSet:
        def __iter__(self):
            return iter(reversed(flags))

    monkeypatch.setattr("dkit.commands.perms.permission_flags", lambda: UnsortedFlagSet())

    payload = cli("--json", "perms", "--list").json
    bits = [item["bit"] for item in payload["permissions"]]
    assert bits == sorted(bits)
    assert bits[0] == 0
    assert bits[-1] == max(f.bit for f in flags)


# --- dkit perms --add / --remove ----------------------------------------


def test_cli_add_from_the_issue(cli) -> None:
    payload = cli("--json", "perms", "2048", "--add", "MANAGE_ROLES,KICK_MEMBERS").json
    assert payload["value"] == "268437506"
    assert payload["names"] == ["KICK_MEMBERS", "SEND_MESSAGES", "MANAGE_ROLES"]
    assert payload["unknown_bits"] == []
    assert "source" in payload


def test_cli_remove_from_the_issue(cli) -> None:
    payload = cli("--json", "perms", "268437504", "--remove", "MANAGE_ROLES").json
    assert payload["value"] == "2048"
    assert payload["names"] == ["SEND_MESSAGES"]


def test_cli_add_and_remove_together(cli) -> None:
    payload = cli(
        "--json", "perms", "2048", "--add", "VIEW_CHANNEL", "--remove", "SEND_MESSAGES"
    ).json
    assert payload["value"] == "1024"
    assert payload["names"] == ["VIEW_CHANNEL"]


def test_cli_same_name_in_add_and_remove_ends_up_removed(cli) -> None:
    payload = cli(
        "--json", "perms", "0", "--add", "SEND_MESSAGES", "--remove", "SEND_MESSAGES"
    ).json
    assert payload["value"] == "0"
    assert payload["names"] == []


def test_cli_add_preserves_unknown_bits(cli) -> None:
    value = str(2048 | (1 << 47))
    payload = cli("--json", "perms", value, "--add", "VIEW_CHANNEL").json
    assert payload["value"] == str(2048 | 1024 | (1 << 47))
    assert payload["names"] == ["VIEW_CHANNEL", "SEND_MESSAGES"]
    assert payload["unknown_bits"] == [47]
    text = cli("perms", value, "--add", "VIEW_CHANNEL")
    assert "no name for" in text.stderr


def test_cli_remove_preserves_unknown_bits(cli) -> None:
    value = str(2048 | (1 << 47))
    payload = cli("--json", "perms", value, "--remove", "SEND_MESSAGES").json
    assert payload["value"] == str(1 << 47)
    assert payload["names"] == []
    assert payload["unknown_bits"] == [47]


def test_cli_add_above_2_pow_32(cli) -> None:
    # BYPASS_SLOWMODE is bit 52 (value 4503599627370496).
    payload = cli("--json", "perms", "2048", "--add", "BYPASS_SLOWMODE").json
    assert int(payload["value"]) > 2**32
    assert payload["value"] == str(2048 | (1 << 52))
    assert payload["names"] == ["SEND_MESSAGES", "BYPASS_SLOWMODE"]
    assert isinstance(payload["value"], str)


def test_cli_add_normalises_names(cli) -> None:
    payload = cli("--json", "perms", "0", "--add", "send-messages, View Channel").json
    assert payload["names"] == ["VIEW_CHANNEL", "SEND_MESSAGES"]


def test_cli_add_text_matches_decode_format(cli) -> None:
    result = cli("perms", "2048", "--add", "MANAGE_ROLES,KICK_MEMBERS")
    assert result.exit_code == 0
    assert "Permissions 268437506" in result.stdout
    assert "KICK_MEMBERS" in result.stdout
    assert "SEND_MESSAGES" in result.stdout
    assert "MANAGE_ROLES" in result.stdout


def test_cli_add_unknown_name_suggests(cli) -> None:
    result = cli("perms", "2048", "--add", "SEND_MESSAGE")
    assert result.exit_code == 2
    assert "unknown permission name" in result.stderr
    assert "SEND_MESSAGES" in result.stderr


def test_cli_remove_unknown_name_suggests(cli) -> None:
    result = cli("perms", "2048", "--remove", "NOPE_NOT_REAL")
    assert result.exit_code == 2
    assert "unknown permission name" in result.stderr


@pytest.mark.parametrize(
    "argv, message",
    [
        (("perms", "--add", "SEND_MESSAGES"), "--add/--remove need a permissions number"),
        (("perms", "--remove", "SEND_MESSAGES"), "--add/--remove need a permissions number"),
        (
            ("perms", "2048", "--add", "SEND_MESSAGES", "--names", "VIEW_CHANNEL"),
            "--add/--remove cannot be combined with --names",
        ),
        (
            ("perms", "2048", "--remove", "SEND_MESSAGES", "--diff", "0"),
            "--add/--remove cannot be combined with --diff",
        ),
        (("perms", "2048", "--add", ""), "--add did not contain any permission names"),
        (("perms", "2048", "--remove", ",,,"), "--remove did not contain any permission names"),
        (
            ("perms", "--list", "--add", "SEND_MESSAGES"),
            "--list cannot be combined with --add or --remove",
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
