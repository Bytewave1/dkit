"""Tests for ``dkit mention``."""

from __future__ import annotations

import re

import pytest

from dkit.commands.mention import build_mention, formats
from dkit.core import data
from dkit.core.errors import UsageError

USER_ID = "80351110224678912"


def test_list_shows_every_documented_format(cli) -> None:
    payload = cli("--json", "mention", "--list").json
    assert payload["mode"] == "list"
    assert payload["count"] == len(formats()) == 13
    descriptions = [entry["description"] for entry in payload["formats"]]
    assert "User (deprecated)" in descriptions
    assert "Guild navigation" in descriptions
    assert payload["source"]["last_verified"] == "2026-11-11"


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("user", f"<@{USER_ID}>"),
        ("channel", "<#103735883630395392>"),
        ("role", "<@&165511591545143296>"),
    ],
)
def test_simple_id_formats(kind: str, expected: str, cli) -> None:
    arg = {
        "user": USER_ID,
        "channel": "103735883630395392",
        "role": "165511591545143296",
    }[kind]
    payload = cli("--json", "mention", kind, arg).json
    assert payload["mention"] == expected
    assert payload["type"] == kind


def test_user_and_role_mark_notify_channel_does_not() -> None:
    assert build_mention("user", [USER_ID])["notify"] is True
    assert build_mention("role", ["165511591545143296"])["notify"] is True
    assert build_mention("channel", ["103735883630395392"])["notify"] is False


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["airhorn", "816437322781949972"], "</airhorn:816437322781949972>"),
        (["foo bar", "123456789012345678"], "</foo bar:123456789012345678>"),
        (["foo group bar", "123456789012345678"], "</foo group bar:123456789012345678>"),
        # unquoted multi-word names join to the same path
        (["foo", "bar", "123456789012345678"], "</foo bar:123456789012345678>"),
    ],
)
def test_command_formats(values: list[str], expected: str) -> None:
    assert build_mention("command", values)["mention"] == expected


def test_emoji_static_and_animated() -> None:
    static = build_mention("emoji", ["mmLol", "216154654256398347"])
    assert static["mention"] == "<:mmLol:216154654256398347>"
    assert static["type"] == "emoji"
    animated = build_mention("emoji", ["b1nzy", "392938283556143104"], animated=True)
    assert animated["mention"] == "<a:b1nzy:392938283556143104>"
    assert animated["type"] == "animated-emoji"


def test_animated_flag_only_applies_to_emoji(cli) -> None:
    result = cli("mention", "user", USER_ID, "--animated")
    assert result.exit_code == 2


def test_navigation_types() -> None:
    for nav_type in ("customize", "browse", "guide"):
        payload = build_mention("navigation", [nav_type])
        assert payload["mention"] == f"<id:{nav_type}>"
        assert payload["description"]
    payload = build_mention("navigation", ["linked-roles", "123456789012345678"])
    assert payload["mention"] == "<id:linked-roles:123456789012345678>"


def test_navigation_rejects_unknown_types_and_role_ids() -> None:
    with pytest.raises(UsageError, match="unknown navigation type"):
        build_mention("navigation", ["onboarding"])
    with pytest.raises(UsageError, match="only linked-roles"):
        build_mention("navigation", ["guide", "123456789012345678"])


def test_ids_go_through_snowflake_parsing() -> None:
    with pytest.raises(UsageError, match="snowflake"):
        build_mention("user", ["not-a-number"])


def test_names_reject_brackets_and_empty() -> None:
    with pytest.raises(UsageError, match="angle brackets"):
        build_mention("emoji", ["mm<Lol", "216154654256398347"])
    with pytest.raises(UsageError, match="empty"):
        build_mention("emoji", ["", "216154654256398347"])


def test_command_name_rejects_a_colon() -> None:
    with pytest.raises(UsageError, match="colon"):
        build_mention("command", ["air:horn", "816437322781949972"])


def test_command_requires_two_arguments() -> None:
    with pytest.raises(UsageError, match="takes 2 arguments"):
        build_mention("command", ["airhorn"])


def test_unknown_type_suggests_the_closest_name(cli) -> None:
    result = cli("mention", "usr", USER_ID)
    assert result.exit_code == 2
    assert "user" in result.stdout + result.stderr


def test_list_cannot_be_combined_with_a_type(cli) -> None:
    result = cli("mention", "--list", "user")
    assert result.exit_code == 2


def test_no_type_given_is_a_usage_error(cli) -> None:
    result = cli("mention")
    assert result.exit_code == 2


def test_json_payload_carries_provenance(cli) -> None:
    payload = cli("--json", "mention", "user", USER_ID).json
    assert payload["source"]["last_verified"] == "2026-11-11"
    assert payload["source"]["source_rendered"] == (
        "https://discord.com/developers/docs/reference#message-formatting"
    )


def test_text_output_prints_the_mention_and_the_notify_note(cli) -> None:
    result = cli("mention", "user", USER_ID)
    assert result.exit_code == 0
    assert f"<@{USER_ID}>" in result.stdout
    assert "allowed_mentions" in result.stdout


def test_roundtrip_through_dkit_snowflake(cli) -> None:
    """user/channel/role mentions decode back to the same ID."""
    for kind, arg in (
        ("user", USER_ID),
        ("channel", "103735883630395392"),
        ("role", "165511591545143296"),
    ):
        mention = build_mention(kind, [arg])["mention"]
        decoded = cli("--json", "snowflake", mention).json
        assert decoded["id"] == arg
        assert decoded["label"] == kind


def test_deprecated_form_is_documented_but_not_built() -> None:
    table = formats()
    deprecated = next(entry for entry in table if entry["description"] == "User (deprecated)")
    assert deprecated["syntax"] == "<@!USER_ID>"
    with pytest.raises(UsageError):
        build_mention("user-deprecated", [USER_ID])


def test_message_formats_json_is_wellformed() -> None:
    fmt = data.load("message_formats")
    for entry in fmt["table"]:
        assert entry["description"] and entry["syntax"] and entry["example"]
        assert re.search(r"\{[a-z_]+\}", str(entry["example"])) is None
    for kind, template in fmt["templates"].items():
        assert re.search(r"\{[a-z_]+\}", template) or kind == "navigation", kind
    for nav in fmt["navigation_types"]:
        assert nav in ("customize", "browse", "guide", "linked-roles")


def test_wrong_argument_counts_are_usage_errors() -> None:
    with pytest.raises(UsageError, match="takes 1 argument"):
        build_mention("user", [])
    with pytest.raises(UsageError, match="takes 2 arguments"):
        build_mention("emoji", ["mmLol"])
    with pytest.raises(UsageError, match=r"takes 1 argument .* or 2"):
        build_mention("navigation", ["guide", "123456789012345678", "extra"])


def test_emoji_name_rejects_a_colon() -> None:
    with pytest.raises(UsageError, match="colon"):
        build_mention("emoji", ["mm:Lol", "216154654256398347"])


def test_text_output_shows_the_navigation_target(cli) -> None:
    result = cli("mention", "navigation", "browse")
    assert result.exit_code == 0
    assert "<id:browse>" in result.stdout
    assert "Browse Channels tab" in result.stdout
