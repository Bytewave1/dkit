"""Offline completion uses current parser metadata and bundled datasets."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from dkit.commands.completion import candidates


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (["per"], "perms"),
        (["--json", "per"], "perms"),
        (["perms", "--n"], "--names"),
        (["perms", "--names", "SEND_MESSAGES_IN"], "SEND_MESSAGES_IN_THREADS"),
        (["perms", "--names=SEND_MESSAGES_IN"], "--names=SEND_MESSAGES_IN_THREADS"),
        (["perms", "--names", "=", "SEND_MESSAGES_IN"], "SEND_MESSAGES_IN_THREADS"),
        (["perms", "--names", "VIEW_CHANNEL,SEND_M"], "VIEW_CHANNEL,SEND_MESSAGES"),
        (["intents", "GUILDS,GUILD_M"], "GUILDS,GUILD_MESSAGES"),
        (["invite", "--scopes", "applications.comm"], "applications.commands"),
        (["invite", "--scopes=bot,applications.comm"], "--scopes=bot,applications.commands"),
        (["invite", "--perms", "SEND_M"], "SEND_MESSAGES"),
        (["completion", "z"], "zsh"),
    ],
)
def test_candidate_context(words, expected):
    assert expected in candidates(words)


def test_no_match_and_hidden_protocol():
    assert candidates(["perms", "--names", "NOT_REAL"]) == []
    assert candidates(["invite", "--client-id=12"]) == []
    assert "--complete" not in candidates(["completion", "--"])


def test_empty_word_keeps_names_context():
    assert "bot" in candidates(["invite", "--scopes", ""])
    assert "intents" in candidates([])


def test_candidates_read_current_data(monkeypatch):
    from dkit.commands import completion

    monkeypatch.setattr(completion.data, "load", lambda _: {"permissions": [{"name": "NEW_FLAG"}]})
    assert candidates(["perms", "--names", "NEW"]) == ["NEW_FLAG"]


def test_helper_output_and_json(cli):
    result = cli("completion", "--complete", "perms", "--names", "SEND_MESSAGES_IN")
    assert result.exit_code == 0
    assert result.stdout == "SEND_MESSAGES_IN_THREADS\n"
    payload = cli("--json", "completion", "--complete", "intents", "GUILD_MESSAGES").json
    assert "GUILD_MESSAGES" in payload["candidates"]


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_script_stdout_and_json(cli, shell):
    result = cli("completion", shell)
    assert result.exit_code == 0
    assert "dkit completion --complete" in result.stdout
    assert "\x1b" not in result.stdout
    assert cli("--json", "completion", shell).json["script"] == result.stdout


def test_missing_shell_is_usage_error(cli):
    assert cli("completion").exit_code == 2
    assert cli("completion", "bash", "--complete", "perms").exit_code == 2


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (["dkit", "per"], "perms"),
        (["dkit", "perms", "--n"], "--names"),
        (["dkit", "perms", "--names", "SEND_MESSAGES_IN"], "SEND_MESSAGES_IN_THREADS"),
        (["dkit", "intents", "GUILDS,GUILD_M"], "GUILDS,GUILD_MESSAGES"),
        (["dkit", "invite", "--scopes", ""], "bot"),
        (
            ["dkit", "invite", "--scopes=bot,applications.comm"],
            "--scopes=bot,applications.commands",
        ),
    ],
)
def test_generated_shell_calls_real_helper(cli, tmp_path, shell, words, expected):
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} unavailable")
    script = tmp_path / "completion.sh"
    script.write_text(cli("completion", shell).stdout)
    shell_words = shlex.join(words)
    if shell == "bash":
        harness = (
            'source "$1"; '
            f"COMP_WORDS=({shell_words}); "
            f"COMP_CWORD={len(words) - 1}; "
            "_dkit_complete; "
            'printf "%s\\n" "${COMPREPLY[@]}"'
        )
    elif shell == "zsh":
        harness = (
            "compdef() { :; "
            "}; "
            "compadd() { shift 2; "
            'printf "%s\\n" "$@"; '
            "}; "
            'source "$1"; '
            f"words=({shell_words}); "
            f"CURRENT={len(words)}; "
            "_dkit_complete"
        )
    else:
        commandline = " ".join(words)
        harness = 'source "$argv[2]"; complete -C ' + shlex.quote(commandline)
    env = {
        **os.environ,
        "PATH": str(Path(os.sys.executable).parent) + os.pathsep + os.environ["PATH"],
    }
    env.update(
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
        }
    )
    result = subprocess.run(
        [executable, "-c", harness, "test", str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout.splitlines()
