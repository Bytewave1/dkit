# Good first issues

Eight self-contained ideas, some already implemented and others still open.
Each one follows the pattern already in the codebase, so none of them require
redesigning anything.

Before starting one, read [CONTRIBUTING.md](../CONTRIBUTING.md): adding a
command means adding one file in `src/dkit/commands/` and one line in
`src/dkit/commands/__init__.py`, and every Discord constant belongs in a JSON
data file with a `source` and `last_verified` date.

---

## 1. `dkit channels` — look up channel types (done in #31)

**Status:** Done in #31.

**Labels:** `good first issue`, `enhancement`, `new command`

Channel types are the other integer lookup Discord developers hit constantly.
Is a forum channel `15` or `16`? What is type `13` again?

**What to build**

- A new data file `src/dkit/data/channel_types.json` holding each channel type
  with its integer value and description, sourced from
  `developers/resources/channel.mdx` ("Channel Types") in
  [discord/discord-api-docs](https://github.com/discord/discord-api-docs).
- A new command `src/dkit/commands/channels.py` supporting:
  - `dkit channels 15` → `GUILD_FORUM` plus its description.
  - `dkit channels GUILD_FORUM` → `15`.
  - `dkit channels` with no argument → list every type.

**Notes**

Channel types are a plain enum, not a bitfield, so `FlagSet` does not apply —
a small dict lookup is the right shape. Reuse `suggestion_hint()` from
`dkit.core.suggest` for unknown names, and `UsageError` for bad input.

**Done when** all three forms work, `--json` output includes the data file's
`source`, there are known-value and invalid-input tests, and the README has a
usage example.

---

## 2. `dkit timestamp` — Discord message timestamp formatting (done in #10)

**Status:** Done by @dbdefault in #10.

**Labels:** `good first issue`, `enhancement`, `new command`

Discord renders `<t:1462015105:F>` as a localised date in chat. Developers have
to build these by hand and remember which letter means what.

**What to build**

- `src/dkit/data/timestamp_styles.json` with the style characters (`t`, `T`,
  `d`, `D`, `f`, `F`, `R`), their names and an example rendering, sourced from
  `developers/reference.mdx` ("Message Formatting" → "Timestamp Styles").
- `src/dkit/commands/timestamp.py`:
  - `dkit timestamp 2026-10-20T08:30:00Z` → every style for that instant.
  - `dkit timestamp 2026-10-20T08:30:00Z --style R` → just `<t:1792485000:R>`.
  - `dkit timestamp --from-snowflake 175928847299117063` → styles for the
    instant that snowflake encodes.

**Notes**

Reuse `parse_datetime()` from `dkit.core.parse`, and
`dkit.commands.snowflake.decode()` for the `--from-snowflake` path — that cross
-command reuse is exactly what the shared core is for. Note that the timestamp
in the tag is in **seconds**, not milliseconds.

**Done when** each style is produced correctly, an unknown style gives a
`UsageError` with a suggestion, and tests cover a known instant plus the
snowflake path.

---

## 3. `dkit locales` — list Discord locales (done in #23)

**Status:** Done in #23.

**Labels:** `good first issue`, `enhancement`, `new command`, `data`

Localised command names and responses need exact locale codes, and `en-US` vs
`en_US` vs `en` is an easy mistake to make.

**What to build**

- `src/dkit/data/locales.json` with each locale code and its language name,
  sourced from `developers/reference.mdx` ("Locales").
- `src/dkit/commands/locales.py`:
  - `dkit locales` → the full table.
  - `dkit locales de` → the matching entry (or a suggestion).
  - `dkit locales --search portug` → case-insensitive search by language name.

**Notes**

Keep the output aligned and readable for ~30 rows; `Printer.field()` and
`Printer.line()` are enough. This is a good first contribution for someone who
wants to practise the data-file workflow without touching bit arithmetic.

**Done when** exact lookup, search and the full listing all work, with tests
for a known locale and an unknown one.

---

## 4. `dkit overwrites` — resolve permission overwrites

**Status:** Open in #4.

**Labels:** `good first issue`, `enhancement`, `new command`

This is the question that actually confuses people: the role says yes, the
channel overwrite says no, and the member still cannot type. Discord resolves
this with a documented algorithm that `dkit` could just run.

**What to build**

`src/dkit/commands/overwrites.py` that applies the documented order:

1. Start from `@everyone` role permissions.
2. If `ADMINISTRATOR` is set, everything is allowed — stop.
3. Apply the `@everyone` channel overwrite: clear `deny`, then set `allow`.
4. Union the member's role overwrites' `deny`, then their `allow`, and apply.
5. Apply the member-specific overwrite: `deny`, then `allow`.

Suggested interface:

```console
dkit overwrites --base 274878286912 \
  --everyone-deny SEND_MESSAGES \
  --role-allow SEND_MESSAGES \
  --member-deny ADD_REACTIONS
```

Output the effective permission set, and show each step so the user can see
where a permission was lost.

**Notes**

The algorithm is in `developers/topics/permissions.mdx` ("Permission
Overwrites") — follow it exactly rather than reasoning from first principles,
and keep the step-by-step logic in a pure function so it is easy to test.
`FlagSet.value_of()` parses each name list.

**Done when** the worked example from the official docs is a test, each step is
individually tested, and the `ADMINISTRATOR` short-circuit is covered.

---

## 5. `dkit update-data` — refresh the data files from the official docs

**Status:** Open in #5.

**Labels:** `enhancement`, `tooling`, `help wanted`

Updating a data file is currently a careful manual diff (see
[CONTRIBUTING.md](../CONTRIBUTING.md#updating-the-data-files)). A maintainer
command could do the fetching and parsing, while keeping the human in the loop.

**What to build**

An opt-in maintainer command that fetches the four `.mdx` sources from
[discord/discord-api-docs](https://github.com/discord/discord-api-docs), parses
the relevant tables, and reports differences:

- `dkit update-data --check` → exit `1` if a data file is out of date, printing
  a diff. Ideal for a scheduled CI job.
- `dkit update-data --write` → update the JSON files and bump `last_verified`.

**Important design constraint**

`dkit`'s promise is that it works entirely offline with no dependencies, and
this command must not break that:

- Use `urllib.request` only — no new dependencies.
- Import the networking lazily inside `run()`, so no other command can reach
  network code.
- Document it clearly as a maintainer tool, and consider gating it behind an
  extra such as `pip install "dkit-cli[maintainer]"`.
- Never fetch at runtime for a normal command.

**Done when** `--check` detects a deliberately stale value, `--write` produces
a clean diff, and the parsers are tested against committed sample `.mdx`
fixtures rather than live network calls.

---

## 6. Shell completion for bash, zsh and fish (done in #33)

**Status:** Done in #33.

**Labels:** `good first issue`, `enhancement`, `developer experience`

Permission names are long and `SEND_MESSAGES_IN_THREADS` is tedious to type.
Completion would make the tool noticeably nicer, and all the names are already
available from the data files.

**What to build**

- `dkit completion bash|zsh|fish` printing a completion script to stdout, so
  users can do `eval "$(dkit completion bash)"`.
- Complete subcommand names, flags, and — the valuable part — permission names
  for `perms --names`, intent names for `intents`, and scopes for
  `invite --scopes`.

**Notes**

A hidden helper such as `dkit completion --list-names perms` that prints one
name per line keeps the shell scripts trivial and keeps the name list in
Python, where the data lives. Standard library only; no `argcomplete`.

**Done when** all three shells complete subcommands and names, the README
documents the install line for each shell, and tests assert the generated
scripts are non-empty and mention the expected names.

---

## 7. Verify dkit on Windows, macOS and Linux (done in #9)

**Status:** Done by @Aaqibhafeezkhan in #9.

**Labels:** `good first issue`, `ci`, `help wanted`, `testing`

CI runs on `ubuntu-latest` only. `dkit` prints ANSI colors and box-drawing-free
aligned output, and Windows terminals historically disagree about both.

**What to build**

- Extend the `test` job in `.github/workflows/ci.yml` to a matrix over
  `ubuntu-latest`, `macos-latest` and `windows-latest`.
- Fix whatever that surfaces. Likely candidates:
  - ANSI escapes on older Windows consoles — `colors_enabled()` in
    `dkit/core/output.py` may need a Windows check, or to enable virtual
    terminal processing.
  - `PYTHONIOENCODING` / code-page issues if any output is not pure ASCII.
  - Line endings in the smoke-test step of the workflow.
- Add a test that output contains no ANSI escapes when stdout is not a TTY
  (this already holds — lock it in as a cross-platform guarantee).

**Notes**

Keep the matrix cheap: all four Python versions on Linux, and a single current
Python on macOS and Windows is plenty.

**Done when** CI is green on all three operating systems and the README states
which platforms are tested.

---

## 8. Broaden the test suite

**Status:** Partly done in #11, #22 and #32.

**Labels:** `good first issue`, `testing`

The suite covers the documented behaviour well, but there are worthwhile gaps
for someone who enjoys finding edge cases.

**What to build**

Pick any of these; each is a fine standalone pull request:

- **Coverage reporting.** CI measures coverage and reports it in the job
  summary (#32); a coverage badge remains an idea.
- **Property-based round trips.** Implemented with Hypothesis for permissions,
  intents and user flags (#22).
- **Snowflake boundaries.** Zero, the 64-bit limits and the epoch are tested;
  add a leap-second-adjacent timestamp.
- **Unicode and whitespace input.** Full-width digits, a non-breaking space
  inside a name list, and a trailing newline from `xargs` are tested (#11).
- **`--json` schema stability.** Exact key sets are tested for five commands
  (#11); extend coverage to the other commands.
- **Help text.** Example sections are checked for every registered command,
  and rendered examples for five commands (#11); extend the rendered-help
  checks to the other commands.

**Done when** the new tests pass and genuinely fail if the behaviour they
describe is broken — please verify that by temporarily breaking it.
