"""Tests for the CLI shell itself: global flags, exit codes, registry wiring."""

from __future__ import annotations

import json
import runpy

import pytest

from dkit import __version__
from dkit.cli import build_parser, main
from dkit.commands import COMMANDS
from dkit.core.errors import EXIT_OK, EXIT_USAGE
from dkit.core.output import Printer, colors_enabled


def test_no_arguments_prints_help_and_succeeds(cli) -> None:
    result = cli()
    assert result.exit_code == EXIT_OK
    assert "An offline toolbox for Discord bot developers." in result.stdout
    for command in COMMANDS:
        assert command.name in result.stdout


def test_version_exits_zero(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == EXIT_OK
    assert __version__ in capsys.readouterr().out


def test_unknown_command_exits_with_code_2(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["definitely-not-a-command"])
    assert excinfo.value.code == EXIT_USAGE


def test_unknown_flag_exits_with_code_2(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["perms", "--definitely-not-a-flag"])
    assert excinfo.value.code == EXIT_USAGE


@pytest.mark.parametrize(
    "argv",
    [
        ("--json", "perms", "2048"),
        ("perms", "2048", "--json"),
    ],
    ids=["before-command", "after-command"],
)
def test_json_flag_works_on_either_side_of_the_command(cli, argv) -> None:
    """--json is a global flag and must work in both positions."""
    result = cli(*argv)
    assert result.exit_code == EXIT_OK
    assert json.loads(result.stdout)["value"] == "2048"


@pytest.mark.parametrize(
    "argv",
    [
        ("--no-color", "perms", "2048"),
        ("perms", "2048", "--no-color"),
    ],
    ids=["before-command", "after-command"],
)
def test_no_color_flag_works_on_either_side_of_the_command(cli, argv) -> None:
    result = cli(*argv)
    assert result.exit_code == EXIT_OK
    assert "\033[" not in result.stdout


def test_json_output_is_never_colored(cli) -> None:
    result = cli("--json", "intents", "MESSAGE_CONTENT")
    assert "\033[" not in result.stdout


def test_json_mode_keeps_warnings_out_of_stdout(cli) -> None:
    """Warnings belong in the payload, so stdout stays parseable."""
    result = cli("--json", "intents", "MESSAGE_CONTENT")
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["warnings"]


@pytest.mark.parametrize("command", [command.name for command in COMMANDS])
def test_every_command_has_help(capsys, command: str) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([command, "--help"])
    assert excinfo.value.code == EXIT_OK
    captured = capsys.readouterr().out
    assert command in captured
    assert "--json" in captured


def test_every_command_is_reachable_from_the_parser() -> None:
    parser = build_parser()
    choices = next(
        action.choices for action in parser._actions if action.dest == "command" and action.choices
    )
    assert set(choices) == {command.name for command in COMMANDS}


def test_registry_entries_are_well_formed() -> None:
    for command in COMMANDS:
        assert command.name and command.name.islower()
        assert command.help
        assert callable(command.add_arguments)
        assert callable(command.run)


def test_command_names_are_unique() -> None:
    names = [command.name for command in COMMANDS]
    assert len(set(names)) == len(names)


def test_help_mentions_that_everything_is_offline(cli) -> None:
    assert "offline" in cli().stdout.lower()


# --- output plumbing ----------------------------------------------------


def test_no_color_env_var_disables_colors(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")

    class FakeTty:
        def isatty(self) -> bool:
            return True

    assert colors_enabled(no_color=False, stream=FakeTty()) is False


def test_colors_are_disabled_when_not_a_tty(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)

    class NotATty:
        def isatty(self) -> bool:
            return False

    assert colors_enabled(no_color=False, stream=NotATty()) is False


def test_cli_output_has_no_ansi_escapes_when_stdout_is_not_a_tty(cli) -> None:
    """Captured/piped output must remain free of terminal control sequences."""
    result = cli("perms", "--names", "SEND_MESSAGES,MANAGE_ROLES")
    assert result.exit_code == EXIT_OK
    assert "\033[" not in result.stdout
    assert "\033[" not in result.stderr


def test_style_is_a_no_op_without_color() -> None:
    printer = Printer(color=False)
    assert printer.style("text", "red", "bold") == "text"


def test_style_wraps_text_when_color_is_enabled() -> None:
    printer = Printer(color=True)
    styled = printer.style("text", "red")
    assert styled.startswith("\033[31m")
    assert styled.endswith("\033[0m")


def test_text_helpers_are_silent_in_json_mode(capsys) -> None:
    printer = Printer(json_mode=True)
    printer.line("visible?")
    printer.heading("visible?")
    printer.field("key", "value")
    printer.note("note")
    printer.warnings(["warning"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# --- the offline guarantee ----------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ("snowflake", "175928847299117063"),
        ("snowflake", "--from-date", "2016-04-30T11:18:25Z"),
        ("perms", "274878286912"),
        ("perms", "--names", "SEND_MESSAGES,MANAGE_ROLES"),
        ("invite", "--client-id", "157730590492196864", "--perms", "2048"),
        ("intents", "GUILDS,GUILD_MESSAGES,MESSAGE_CONTENT"),
        ("intents", "33281"),
        ("locales",),
        ("locales", "de"),
        ("locales", "--search", "portug"),
    ],
)
def test_no_command_touches_the_network(cli, monkeypatch, argv) -> None:
    """dkit must work fully offline, so any socket use is a bug."""

    def forbidden(*args, **kwargs):
        raise AssertionError("dkit attempted to use the network")

    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)

    assert cli(*argv).exit_code == EXIT_OK


def test_no_command_prompts_for_input(cli, monkeypatch) -> None:
    """dkit must never ask for a bot token, or anything else, interactively."""

    def forbidden(*args, **kwargs):
        raise AssertionError("dkit attempted to read from stdin")

    monkeypatch.setattr("builtins.input", forbidden)
    monkeypatch.setattr("sys.stdin", None)

    for argv in (
        ("snowflake", "175928847299117063"),
        ("perms", "8"),
        ("intents", "33281"),
        ("invite", "--client-id", "157730590492196864"),
        ("locales", "de"),
    ):
        assert cli(*argv).exit_code == EXIT_OK


def test_python_dash_m_dkit_runs_the_cli(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["dkit", "--version"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("dkit", run_name="__main__")
    assert excinfo.value.code == EXIT_OK
    assert capsys.readouterr().out == f"dkit {__version__}\n"
