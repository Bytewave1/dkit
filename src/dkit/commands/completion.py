"""Print shell completion scripts and offline completion candidates."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command

SHELLS = ("bash", "zsh", "fish")
SCRIPTS = {
    "bash": """_dkit_complete() {
    local candidate
    COMPREPLY=()
    while IFS= read -r candidate; do
        COMPREPLY+=("$candidate")
    done < <(command dkit completion --complete -- "${COMP_WORDS[@]:1:COMP_CWORD}")
}
complete -F _dkit_complete dkit
""",
    "zsh": """#compdef dkit
_dkit_complete() {
    local -a candidates
    candidates=("${(@f)$(command dkit completion --complete -- "${words[@]:1:$((CURRENT-1))}")}")
    (( ${#candidates} )) && compadd -Q -- "${candidates[@]}"
}
compdef _dkit_complete dkit
""",
    "fish": """function __dkit_complete
    set -l words (commandline -opc)
    set -l current (commandline -ct)
    command dkit completion --complete -- $words[2..-1] "$current"
end
complete -c dkit -f -a '(__dkit_complete)'
""",
}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register shell selection and the hidden shell-to-Python protocol."""
    parser.add_argument("shell", nargs="?", choices=SHELLS, help="shell to generate a script for")
    parser.add_argument("--complete", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)


def candidates(words: list[str]) -> list[str]:
    """Complete the last word; preceding words are arguments, never commands to execute."""
    from dkit.cli import build_parser

    parser = build_parser()
    subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    commands = subparsers.choices
    current = words[-1] if words else ""
    previous = words[-2] if len(words) > 1 else ""
    command = next((word for word in words[:-1] if word in commands), None)
    selected = commands[command] if command else parser
    options = [
        option
        for action in selected._actions
        if action.help != argparse.SUPPRESS
        for option in action.option_strings
    ]
    prefix = ""
    if current.startswith("--") and "=" in current:
        previous, current = current.split("=", 1)
        prefix = previous + "="
    elif previous == "=" and len(words) > 2:
        previous = words[-3]

    names: list[str] | None = None
    if command == "perms" and previous == "--names":
        names = [entry["name"] for entry in data.load("permissions")["permissions"]]
    elif command == "invite" and previous == "--scopes":
        names = [entry["name"] for entry in data.load("oauth2")["scopes"]]
    elif command == "invite" and previous == "--perms":
        names = [entry["name"] for entry in data.load("permissions")["permissions"]]
    elif command == "intents" and not current.startswith("-"):
        names = [entry["name"] for entry in data.load("intents")["intents"]]

    if names is not None:
        leading, comma, fragment = current.rpartition(",")
        if comma:
            prefix += leading + comma
            current = fragment
        return [prefix + name for name in names if name.startswith(current)]
    if prefix:
        return []
    if command is None:
        return [name for name in [*commands, *options] if name.startswith(current)]
    if command == "completion" and not current.startswith("-"):
        return [shell for shell in SHELLS if shell.startswith(current)]
    return [option for option in options if option.startswith(current)]


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Emit a script or candidate lines, with a JSON equivalent when requested."""
    if args.complete is not None:
        if args.shell is not None:
            raise UsageError("choose a shell or request candidates, not both")
        result = candidates(args.complete)
        for item in result:
            out.line(item)
        return {"candidates": result}
    if args.shell is None:
        raise UsageError("choose a shell", hint="example: dkit completion bash")
    script = SCRIPTS[args.shell]
    out.line(script.rstrip("\n"))
    return {"shell": args.shell, "script": script}


COMMAND = Command(
    name="completion",
    help="print an offline shell completion script",
    add_arguments=add_arguments,
    run=run,
    epilog="examples:\n  dkit completion bash\n  dkit completion zsh\n  dkit completion fish\n",
)
