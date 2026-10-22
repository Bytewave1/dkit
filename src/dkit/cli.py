"""The ``dkit`` command line entry point.

Exit codes:
    0  success
    2  usage error or invalid input
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dkit import __version__
from dkit.commands import COMMANDS
from dkit.core.errors import EXIT_OK, DkitError
from dkit.core.output import Printer, colors_enabled

PROG = "dkit"
DESCRIPTION = "An offline toolbox for Discord bot developers."
EPILOG = """\
Every command works entirely offline: dkit never performs network requests
and never asks for a bot token.

run 'dkit <command> --help' for the options of a single command
"""


def _global_options() -> argparse.ArgumentParser:
    """Flags accepted both before and after the command name.

    A fresh parser is returned on every call: ``parents=`` shares action
    objects between parsers, so reusing one instance would let a later
    ``set_defaults`` leak across parsers.

    The defaults are ``SUPPRESS`` so that a flag given before the command
    (``dkit --json perms 8``) is not overwritten when the subparser fills in
    its own defaults. Callers therefore read these with ``getattr``.
    """
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_argument_group("global options")
    group.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print machine-readable JSON instead of text",
    )
    group.add_argument(
        "--no-color",
        action="store_true",
        default=argparse.SUPPRESS,
        help="disable ANSI colors (also honours the NO_COLOR environment variable)",
    )
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Build the full argument parser from the command registry."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=DESCRIPTION,
        epilog=EPILOG,
        parents=[_global_options()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
        help="print the version and exit",
    )
    parser.set_defaults(command=None)

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for command in COMMANDS:
        subparser = subparsers.add_parser(
            command.name,
            help=command.help,
            description=command.description or command.help,
            epilog=command.epilog,
            parents=[_global_options()],
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command.add_arguments(subparser)
        subparser.set_defaults(_run=command.run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    parser = build_parser()
    words = list(sys.argv[1:] if argv is None else argv)
    # Completion words are opaque data, including argparse's special "--".
    # Parse only the protocol prefix so argparse cannot consume candidate words.
    command_index = next(
        (i for i, word in enumerate(words) if word not in ("--json", "--no-color")),
        None,
    )
    if (
        command_index is not None
        and words[command_index] == "completion"
        and "--complete" in words[command_index + 1 :]
        and "--" not in words[: words.index("--complete")]
    ):
        split = words.index("--complete") + 1
        args = parser.parse_args(words[:split])
        complete = words[split:]
        args.complete = complete[1:] if complete[:1] == ["--"] else complete
    else:
        args = parser.parse_args(words)

    # These use argparse.SUPPRESS defaults so that they work on either side
    # of the command name, which means they may be absent entirely.
    json_mode = getattr(args, "json", False)
    no_color = getattr(args, "no_color", False)

    out = Printer(
        json_mode=json_mode,
        color=colors_enabled(no_color=no_color, stream=sys.stdout),
    )

    if args.command is None:
        parser.print_help()
        return EXIT_OK

    try:
        payload = args._run(args, out)
    except DkitError as error:
        out.error(str(error), hint=getattr(error, "hint", None))
        return error.exit_code

    out.emit_json(payload)
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
