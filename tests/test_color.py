"""Tests for ``dkit color``."""

from __future__ import annotations

import argparse
import io

import pytest

from dkit.commands.color import run
from dkit.commands.completion import candidates
from dkit.core.output import Printer

BLURPLE = {"integer": 5793266, "hex": "#5865F2", "rgb": {"r": 88, "g": 101, "b": 242}}


@pytest.mark.parametrize(
    "text",
    ["#5865F2", "#5865f2", "5865F2", "5865f2", "0x5865F2", "0X5865f2", "5793266", "  #5865F2  "],
)
def test_every_accepted_form_resolves_to_blurple(cli, text: str) -> None:
    result = cli("--json", "color", text)
    assert result.exit_code == 0
    assert result.json == BLURPLE


def test_shorthand_expands_each_digit(cli) -> None:
    payload = cli("--json", "color", "#F0A").json
    assert payload == {
        "integer": 16711850,
        "hex": "#FF00AA",
        "rgb": {"r": 255, "g": 0, "b": 170},
    }


def test_bare_digits_are_decimal_and_prefixed_digits_are_hex(cli) -> None:
    decimal = cli("--json", "color", "123456").json
    assert decimal == {"integer": 123456, "hex": "#01E240", "rgb": {"r": 1, "g": 226, "b": 64}}
    assert cli("--json", "color", "#123456").json["integer"] == 1193046
    assert cli("--json", "color", "0x123456").json["integer"] == 1193046


@pytest.mark.parametrize(
    ("text", "integer", "hex_text"),
    [("0", 0, "#000000"), ("15", 15, "#00000F"), ("16777215", 16777215, "#FFFFFF")],
)
def test_boundaries_and_zero_padding(cli, text: str, integer: int, hex_text: str) -> None:
    payload = cli("--json", "color", text).json
    assert payload["integer"] == integer
    assert payload["hex"] == hex_text


@pytest.mark.parametrize(
    ("rgb", "integer", "hex_text"),
    [
        ("255,0,0", 16711680, "#FF0000"),
        ("0,255,0", 65280, "#00FF00"),
        ("0,0,255", 255, "#0000FF"),
        ("88,101,242", 5793266, "#5865F2"),
        ("242,101,88", 15885656, "#F26558"),
        (" 88 , 101 , 242 ", 5793266, "#5865F2"),
        ("0,0,0", 0, "#000000"),
        ("255,255,255", 16777215, "#FFFFFF"),
    ],
)
def test_rgb_input_keeps_channel_order(cli, rgb: str, integer: int, hex_text: str) -> None:
    payload = cli("--json", "color", "--rgb", rgb).json
    assert payload["integer"] == integer
    assert payload["hex"] == hex_text


@pytest.mark.parametrize(
    ("integer", "rgb"),
    [
        ("16711680", {"r": 255, "g": 0, "b": 0}),
        ("65280", {"r": 0, "g": 255, "b": 0}),
        ("255", {"r": 0, "g": 0, "b": 255}),
        ("15885656", {"r": 242, "g": 101, "b": 88}),
    ],
)
def test_integer_input_splits_into_the_right_channels(cli, integer: str, rgb: dict) -> None:
    assert cli("--json", "color", integer).json["rgb"] == rgb


def test_text_output_lists_every_form_without_ansi(cli) -> None:
    result = cli("color", "#5865F2")
    assert result.exit_code == 0
    for expected in ("5793266", "#5865F2", "88, 101, 242"):
        assert expected in result.stdout
    assert "\x1b" not in result.stdout
    assert result.stderr == ""


def test_swatch_uses_the_true_color_of_the_input() -> None:
    stream = io.StringIO()
    run(argparse.Namespace(value=None, rgb="88,101,242"), Printer(color=True, stream=stream))
    assert "\x1b[48;2;88;101;242m" in stream.getvalue()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "-1",
        "16777216",
        "99999999999999999999",
        "0x1000000",
        "#12",
        "#12345",
        "#1234567",
        "#GGGGGG",
        "0x",
        "0xZZZZZZ",
        "ABC",
        "5865F",
        "12345G",
        "hello",
    ],
)
def test_invalid_color_exits_with_code_2(cli, text: str) -> None:
    result = cli("color", text)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error:")


def test_range_and_sign_errors_say_what_is_wrong(cli) -> None:
    assert "0xFFFFFF" in cli("color", "16777216").stderr
    assert "0xFFFFFF" in cli("color", "0x1000000").stderr
    assert "negative" in cli("color", "-1").stderr


@pytest.mark.parametrize(
    "rgb",
    ["1,2", "1,2,3,4", "", "a,b,c", "1.5,0,0", "1,,3", "256,0,0", "0,256,0", "0,0,256", "-1,0,0"],
)
def test_invalid_rgb_exits_with_code_2(cli, rgb: str) -> None:
    result = cli("color", f"--rgb={rgb}")
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("error:")


@pytest.mark.parametrize(
    ("rgb", "channel"),
    [
        ("256,0,0", "red"),
        ("0,256,0", "green"),
        ("0,0,256", "blue"),
        ("-1,0,0", "red"),
        ("0,-1,0", "green"),
        ("0,0,-1", "blue"),
    ],
)
def test_out_of_range_names_the_channel(cli, rgb: str, channel: str) -> None:
    result = cli("color", f"--rgb={rgb}")
    assert result.exit_code == 2
    assert f"{channel} component out of range" in result.stderr


def test_color_and_rgb_cannot_be_combined(cli) -> None:
    result = cli("color", "#5865F2", "--rgb", "1,2,3")
    assert result.exit_code == 2
    assert "cannot be combined" in result.stderr


def test_no_input_is_a_usage_error(cli) -> None:
    result = cli("color")
    assert result.exit_code == 2
    assert result.stderr.startswith("error: no color given")


def test_completion_knows_the_command_and_its_flags() -> None:
    assert "color" in candidates(["col"])
    assert "--rgb" in candidates(["color", "--r"])
