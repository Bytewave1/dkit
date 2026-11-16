"""Tests for ``dkit components``."""

from __future__ import annotations

import pytest

from dkit.commands.components import component_types


def test_component_types_loads() -> None:
    types = component_types()
    assert len(types) >= 20
    assert any(t["name"] == "Button" and t["type"] == "2" for t in types)


def test_component_types_have_required_keys() -> None:
    for entry in component_types():
        assert "type" in entry
        assert "name" in entry
        assert "description" in entry
        assert "style" in entry
        assert "usage" in entry


def test_cli_components_no_args_exits_with_code_2(cli) -> None:
    result = cli("components")
    assert result.exit_code == 2
    assert "no component type given" in result.stderr
    assert "run 'dkit components --list' to list every known component type" in result.stderr


def test_cli_components_json_all(cli) -> None:
    payload = cli("--json", "components", "--list").json
    assert payload["mode"] == "all"
    assert payload["count"] == 20
    assert len(payload["component_types"]) == 20
    assert payload["source"]["source"].startswith("https://github.com/discord/discord-api-docs")
    assert any(c["name"] == "Button" and c["type"] == "2" for c in payload["component_types"])


def test_cli_list_text_output_format(cli) -> None:
    result = cli("components", "--list")
    assert result.exit_code == 0
    assert "Component types (20)" in result.stdout
    assert (
        "  1  Action Row          Container to display a row of interactive components"
        in result.stdout
    )
    assert (
        " 18  Label               Container associating a label and description with a component"
        in result.stdout
    )


def test_cli_lookup_by_integer(cli) -> None:
    result = cli("components", "2")
    assert result.exit_code == 0
    assert "Button" in result.stdout
    assert "2" in result.stdout
    assert "Button object" in result.stdout


def test_cli_lookup_parse_int(cli) -> None:
    res_hex = cli("components", "0x2")
    assert res_hex.exit_code == 0
    assert "Button" in res_hex.stdout

    res_oct = cli("components", "02")
    assert res_oct.exit_code == 0
    assert "Button" in res_oct.stdout


def test_cli_lookup_by_integer_action_row(cli) -> None:
    result = cli("components", "1")
    assert result.exit_code == 0
    assert "Action Row" in result.stdout


def test_cli_lookup_by_name(cli) -> None:
    result = cli("components", "Button")
    assert result.exit_code == 0
    assert "Button" in result.stdout
    assert "2" in result.stdout


def test_cli_lookup_normalises_name(cli) -> None:
    result = cli("components", "action-row")
    assert result.exit_code == 0
    assert "Action Row" in result.stdout
    assert "1" in result.stdout


def test_cli_lookup_normalises_name_with_spaces(cli) -> None:
    result = cli("components", "string select")
    assert result.exit_code == 0
    assert "String Select" in result.stdout
    assert "3" in result.stdout


def test_cli_json_lookup(cli) -> None:
    payload = cli("--json", "components", "2").json
    assert payload["mode"] == "lookup"
    assert payload["name"] == "Button"
    assert payload["type"] == "2"
    assert payload["description"] == "Button object"
    assert payload["source"]["last_verified"]


def test_cli_json_lookup_includes_style_and_usage(cli) -> None:
    payload = cli("--json", "components", "2").json
    assert payload["style"] == "Interactive"
    assert payload["usage"] == "Message"


def test_cli_unknown_integer_exits_with_code_2(cli) -> None:
    result = cli("components", "99")
    assert result.exit_code == 2
    assert "unknown component type number: '99'" in result.stderr
    assert "run 'dkit components --list' to list every known component type" in result.stderr


def test_cli_unknown_name_with_suggestion(cli) -> None:
    result = cli("components", "Butto")
    assert result.exit_code == 2
    assert "unknown component type: 'Butto'" in result.stderr
    assert "did you mean Button?" in result.stderr


def test_cli_unknown_name_no_suggestion(cli) -> None:
    result = cli("components", "xyzzy")
    assert result.exit_code == 2
    assert "unknown component type: 'xyzzy'" in result.stderr


@pytest.mark.parametrize(
    "argv",
    [("components", "-1"), ("components", "99999999999999999999")],
)
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")


def test_cli_strips_whitespace_on_input(cli) -> None:
    res_int = cli("components", "  2  ")
    assert res_int.exit_code == 0
    assert "Button" in res_int.stdout

    res_name = cli("components", "  Button  ")
    assert res_name.exit_code == 0
    assert "2" in res_name.stdout


def test_cli_render_one_shows_style_and_usage_and_name(cli) -> None:
    result = cli("components", "3")
    assert result.exit_code == 0
    assert "Interactive" in result.stdout
    assert "Message, Modal" in result.stdout


def test_cli_render_one_shows_style_and_usage_name(cli) -> None:
    result = cli("components", "1")

    assert result.exit_code == 0
    assert "Layout" in result.stdout
    assert "Message" in result.stdout


def test_cli_search_finds_matches(cli) -> None:
    result = cli("components", "--search", "interactive")

    assert result.exit_code == 0
    assert "Action Row" in result.stdout


def test_cli_search_is_case_insensitive(cli) -> None:
    res_interactive = cli("components", "--search", "Interactive")
    assert res_interactive.exit_code == 0
    assert "Button" in res_interactive.stdout

    payload_button = cli("--json", "components", "--search", "BUTTON").json
    assert payload_button["mode"] == "search"
    assert any(c["name"] == "Button" for c in payload_button["types"])

    payload_lower = cli("--json", "components", "--search", "button").json
    assert payload_lower["mode"] == "search"
    assert any(c["name"] == "Button" for c in payload_lower["types"])


def test_cli_search_strips_query_and_includes_in_json(cli) -> None:
    payload = cli("--json", "components", "--search", " button ").json
    assert payload["mode"] == "search"
    assert payload["query"] == "button"
    assert payload["count"] > 0
    assert any(c["name"] == "Button" for c in payload["types"])


def test_cli_search_json_includes_source(cli) -> None:
    payload = cli("--json", "components", "--search", "Button").json
    assert "source" in payload
    assert payload["source"]["last_verified"]


def test_cli_search_empty_string(cli) -> None:
    result = cli("components", "--search", "")

    assert result.exit_code == 2
    assert "no search text given" in result.stderr


def test_cli_rejects_component_and_search_together(cli) -> None:
    result = cli(
        "components",
        "Button",
        "--search",
        "Interactive",
    )

    assert result.exit_code == 2
    assert "cannot be combined with --search" in result.stderr


def test_cli_rejects_list_with_value_or_search(cli) -> None:
    res_val = cli("components", "--list", "2")
    assert res_val.exit_code == 2
    assert "cannot be combined with --list" in res_val.stderr

    res_search = cli("components", "--list", "--search", "Interactive")
    assert res_search.exit_code == 2
    assert "cannot be combined with --search" in res_search.stderr


def test_search_matches_type(cli) -> None:
    payload = cli(
        "--json",
        "components",
        "--search",
        "18",
    ).json

    assert payload["mode"] == "search"
    assert payload["count"] == 1
    assert payload["types"][0]["type"] == "18"


def test_search_matches_name(cli) -> None:
    payload = cli(
        "--json",
        "components",
        "--search",
        "Button",
    ).json

    assert payload["mode"] == "search"
    assert any(component["name"] == "Button" for component in payload["types"])


DOCUMENTED_COMPONENT_TYPES: list[dict[str, str]] = [
    {
        "type": "1",
        "name": "Action Row",
        "description": "Container to display a row of interactive components",
        "style": "Layout",
        "usage": "Message",
    },
    {
        "type": "2",
        "name": "Button",
        "description": "Button object",
        "style": "Interactive",
        "usage": "Message",
    },
    {
        "type": "3",
        "name": "String Select",
        "description": "Select menu for picking from defined text options",
        "style": "Interactive",
        "usage": "Message, Modal",
    },
    {
        "type": "4",
        "name": "Text Input",
        "description": "Text input object",
        "style": "Interactive",
        "usage": "Modal",
    },
    {
        "type": "5",
        "name": "User Select",
        "description": "Select menu for users",
        "style": "Interactive",
        "usage": "Message, Modal",
    },
    {
        "type": "6",
        "name": "Role Select",
        "description": "Select menu for roles",
        "style": "Interactive",
        "usage": "Message, Modal",
    },
    {
        "type": "7",
        "name": "Mentionable Select",
        "description": "Select menu for mentionables (users and roles)",
        "style": "Interactive",
        "usage": "Message, Modal",
    },
    {
        "type": "8",
        "name": "Channel Select",
        "description": "Select menu for channels",
        "style": "Interactive",
        "usage": "Message, Modal",
    },
    {
        "type": "9",
        "name": "Section",
        "description": "Container to display text alongside an accessory component",
        "style": "Layout",
        "usage": "Message",
    },
    {
        "type": "10",
        "name": "Text Display",
        "description": "Markdown text",
        "style": "Content",
        "usage": "Message, Modal",
    },
    {
        "type": "11",
        "name": "Thumbnail",
        "description": "Small image that can be used as an accessory",
        "style": "Content",
        "usage": "Message",
    },
    {
        "type": "12",
        "name": "Media Gallery",
        "description": "Display images and other media",
        "style": "Content",
        "usage": "Message",
    },
    {
        "type": "13",
        "name": "File",
        "description": "Displays an attached file",
        "style": "Content",
        "usage": "Message",
    },
    {
        "type": "14",
        "name": "Separator",
        "description": "Component to add vertical padding between other components",
        "style": "Layout",
        "usage": "Message",
    },
    {
        "type": "17",
        "name": "Container",
        "description": "Container that visually groups a set of components",
        "style": "Layout",
        "usage": "Message",
    },
    {
        "type": "18",
        "name": "Label",
        "description": "Container associating a label and description with a component",
        "style": "Layout",
        "usage": "Modal",
    },
    {
        "type": "19",
        "name": "File Upload",
        "description": "Component for uploading files",
        "style": "Interactive",
        "usage": "Modal",
    },
    {
        "type": "21",
        "name": "Radio Group",
        "description": "Single-choice set of options",
        "style": "Interactive",
        "usage": "Modal",
    },
    {
        "type": "22",
        "name": "Checkbox Group",
        "description": "Multi-selectable group of checkboxes",
        "style": "Interactive",
        "usage": "Modal",
    },
    {
        "type": "23",
        "name": "Checkbox",
        "description": "Single checkbox for yes/no choice",
        "style": "Interactive",
        "usage": "Modal",
    },
]


def test_component_types_match_documented_values() -> None:
    assert component_types() == DOCUMENTED_COMPONENT_TYPES


def test_search_matches_the_name_column(cli) -> None:
    payload = cli("--json", "components", "--search", "section").json
    assert [entry["type"] for entry in payload["types"]] == ["9"]


def test_search_matches_the_usage_column(cli) -> None:
    payload = cli("--json", "components", "--search", "message, modal").json
    assert [entry["type"] for entry in payload["types"]] == ["3", "5", "6", "7", "8", "10"]
