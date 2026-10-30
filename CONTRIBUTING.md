# Contributing to dkit

Thanks for considering a contribution. `dkit` is small on purpose, and the aim
is to keep it that way: a fast, offline, dependency-free toolbox that gives
trustworthy answers.

## Ground rules

1. **No runtime dependencies.** Standard library only. Development dependencies
   (`pytest`, `ruff`) are fine.
2. **No network access at runtime.** `dkit` must never make a request, and must
   never ask for a bot token. Every answer comes from the bundled data files.
3. **No Discord constant in logic.** Bit positions, the epoch, scope lists and
   similar values belong in `src/dkit/data/*.json`, with a `source` and a
   `last_verified` date.
4. **Never guess a value.** If you cannot verify a number against the official
   documentation, say so in the pull request rather than shipping a guess.
5. **Big integers are real.** Permissions already exceed 32 bits. Use plain
   Python `int` arithmetic and emit permission values as JSON strings.

## Getting set up

```console
git clone https://github.com/Bytewave1/dkit
cd dkit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Then check everything is green:

```console
python -m pytest
ruff check .
ruff format --check .
```

CI runs exactly this on Python 3.10, 3.11, 3.12 and 3.13, plus a packaging
check that the data files end up inside the wheel.

## Project layout

```
dkit/
├─ src/dkit/                      the package
│  ├─ __init__.py                 package version (__version__)
│  ├─ __main__.py                 python -m dkit entry point
│  ├─ cli.py                      argparse root: global flags, dispatch, exit codes
│  ├─ py.typed                    PEP 561 marker for the inline type hints
│  ├─ commands/                   one module per command
│  │  ├─ __init__.py              COMMANDS - the registry you add your command to
│  │  ├─ channels.py              look up Discord channel types
│  │  ├─ color.py                 convert colors between decimal, hex and RGB
│  │  ├─ completion.py            print shell completion scripts and candidates
│  │  ├─ components.py            look up Discord component types
│  │  ├─ errors.py                look up Discord HTTP and JSON error codes
│  │  ├─ flags.py                 decode user flags (profile badges) into names
│  │  ├─ intents.py               translate gateway intent names and integers
│  │  ├─ invite.py                build or decode an OAuth2 bot invite URL
│  │  ├─ locales.py               look up the locale codes Discord accepts
│  │  ├─ perms.py                 translate permission integers and names
│  │  ├─ scheduled_events.py      look up Discord guild scheduled event types
│  │  ├─ scopes.py                look up Discord OAuth2 scopes
│  │  ├─ snowflake.py             decode snowflake IDs, or build one from a date
│  │  └─ timestamp.py             format a timestamp as a Discord <t:...> tag
│  ├─ core/                       shared building blocks
│  │  ├─ __init__.py              shared building blocks used by every command
│  │  ├─ bits.py                  Flag / FlagSet - the shared bitfield engine
│  │  ├─ data.py                  cached JSON data loading + provenance
│  │  ├─ errors.py                UsageError, exit codes
│  │  ├─ output.py                Printer: text vs --json, colors
│  │  ├─ parse.py                 integer, name-list and ISO-8601 parsing
│  │  ├─ registry.py              the Command record
│  │  └─ suggest.py               "did you mean ...?"
│  └─ data/                       the bundled JSON data files
│     ├─ channel_types.json       Discord channel types (value and description)
│     ├─ component_types.json     Discord message component types, styles and usage
│     ├─ error_codes.json         Discord HTTP and JSON error codes
│     ├─ intents.json             gateway intents and privileged flags
│     ├─ locales.json             accepted locale codes and language names
│     ├─ oauth2.json              OAuth2 authorize URL and scopes
│     ├─ permissions.json         bitwise permission flags
│     ├─ scheduled_event_types.json  scheduled event entity types, privacy levels and statuses
│     ├─ snowflake.json           Discord epoch and snowflake bit layout
│     ├─ timestamp_styles.json    <t:...> timestamp styles and examples
│     └─ user_flags.json          user flags (profile badges)
├─ tests/                         pytest suite, one test module per command
├─ docs/                          extra documentation
│  └─ ISSUES.md                   good-first-issue write-ups
├─ .github/                      GitHub configuration
│  ├─ dependabot.yml             keeps the GitHub Actions versions up to date
│  └─ workflows/                 continuous integration
│     └─ ci.yml                  the CI matrix (lint, tests, packaging)
├─ pyproject.toml                 packaging, dev extras, ruff and pytest config
├─ MANIFEST.in                    extra files that ship in the sdist
├─ CONTRIBUTING.md                this guide
├─ README.md                      user-facing documentation
├─ CHANGELOG.md                   release history
└─ LICENSE                        MIT license
```

When you add a command or a data file, update this tree in the same pull request
so it stays an accurate map of where everything lives.

## How to add a new command

Adding a command means **writing one file and adding one line**. Say you want
`dkit stickers`.

### 1. Create `src/dkit/commands/stickers.py`

A command module exposes a `COMMAND` object. The two functions it points at are
`add_arguments` (register flags) and `run` (do the work, return the JSON
payload).

```python
"""``dkit stickers`` - look up Discord sticker formats."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.registry import Command


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit stickers``."""
    parser.add_argument("value", metavar="FORMAT", nargs="?", help="a sticker format")


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit stickers``. The return value is the --json payload."""
    if args.value is None:
        raise UsageError("no sticker format given", hint="example: dkit stickers png")

    # Text output. These calls are no-ops when --json is in effect, so you
    # never have to branch on the output mode yourself.
    out.heading("Sticker format")
    out.field("Name", "PNG")

    return {"name": "PNG", "value": 1, "source": data.provenance("sticker_formats")}


COMMAND = Command(
    name="stickers",
    help="look up Discord sticker formats",
    description="Longer text shown by 'dkit stickers --help'.",
    add_arguments=add_arguments,
    run=run,
    epilog="examples:\n  dkit stickers png\n",
)
```

### 2. Register it in `src/dkit/commands/__init__.py`

```python
from dkit.commands import ..., stickers  # stickers is only an example

COMMANDS: tuple[Command, ...] = (
    ...,
    stickers.COMMAND,  # <- add your command here
)
```

That is all the wiring. Global flags, `--json`, colors, error handling and exit
codes are applied by `cli.py` for every registered command.

### 3. Add `tests/test_stickers.py`

Use the `cli` fixture from `tests/conftest.py`, which runs the CLI in-process
and captures stdout, stderr and the exit code:

```python
def test_cli_json(cli) -> None:
    payload = cli("--json", "stickers", "png").json
    assert payload["name"] == "PNG"


def test_invalid_input_exits_with_code_2(cli) -> None:
    result = cli("stickers")
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")
```

Please cover at least: a known value, a round trip if the command converts in
both directions, invalid input, and the exit code.

### Conventions worth following

- Raise `UsageError(message, hint=...)` for anything the user can fix. It exits
  with code `2` and prints the hint underneath.
- Use `FlagSet` from `dkit.core.bits` for anything that is "a name per bit";
  you get name resolution, "did you mean ...?" and unknown-bit reporting free.
- Put warnings in the payload's `warnings` list *and* pass them to
  `out.warnings(...)`, which writes to stderr so stdout stays pipeable.
- Include `data.provenance("<dataset>")` in the payload under `source`.

## Updating the data files

Data files go stale when Discord ships a new permission or intent. A refresh is
a welcome pull request. The symptom users see is a non-empty `unknown_bits` in
the output.

### Where the values come from

| File | Official source file |
|---|---|
| `permissions.json` | `developers/topics/permissions.mdx` → "Bitwise Permission Flags" |
| `intents.json` | `developers/events/gateway.mdx` → "List of Intents" |
| `snowflake.json` | `developers/reference.mdx` → "Snowflakes" |
| `oauth2.json` | `developers/topics/oauth2.mdx` → "OAuth2 Scopes" |

All four live in [`discord/discord-api-docs`](https://github.com/discord/discord-api-docs),
which is the authoritative, diffable source. The rendered pages at
<https://discord.com/developers/docs> show the same tables.

### The procedure

1. Open the relevant source file for the table above, for example
   <https://github.com/discord/discord-api-docs/blob/main/developers/topics/permissions.mdx>.
2. Compare it against the JSON file, field by field. Copy values across; never
   type a bit position from memory.
3. Keep **bit positions** as the source of truth. `dkit` derives each value as
   `1 << bit`, and `hex` is a redundant cross-check that the tests verify.
4. If the official table skips a bit, skip it too. Bit 47 of the permissions is
   unassigned, as are intent bits 17–19 and 22–23. Do not fill gaps in.
5. Update `last_verified` to the date you checked, in `YYYY-MM-DD` form.
6. Add the new flag to the spot-check lists in `tests/test_data.py` and run the
   suite. `test_every_dataset_declares_provenance` will catch a malformed date,
   and `test_permission_hex_matches_bit` will catch a mismatched `hex`.
7. Note in the pull request which upstream commit or date you verified against.

Automating this is a tracked idea — see the `dkit update-data` item in
[docs/ISSUES.md](docs/ISSUES.md).

## Pull requests

- One logical change per pull request.
- Make sure `python -m pytest`, `ruff check .` and `ruff format --check .` pass.
- Update the README if you changed user-visible behaviour, and add a line under
  `## [Unreleased]` in `CHANGELOG.md`.
- New commands need a usage example in the README.
- Comment on an issue before you start, so it can be assigned to you. This avoids two people building the same thing.
- AI-assisted contributions are welcome. Please say so in the pull request description, and make sure you understand, have tested and can explain every change in review.
- New tests should fail when the behaviour they describe is broken. Please verify that by temporarily breaking it.

## Reporting bugs

Please include the `dkit` version (`dkit --version`), your Python version, the
exact command, and what you expected. `--json` output is ideal, because it
carries the `source` and `last_verified` of the data used.

If you believe a value in a data file is wrong, link the official documentation
that shows the correct value — that makes the fix a two-minute review.
