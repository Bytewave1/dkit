# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `dkit scheduled-events` - look up Discord guild scheduled event entity types,
  privacy levels and statuses by name or number, list or search a group, and
  show the valid status transitions with `--transitions`, with `--json` support
  (#71).

### Changed

- Make `dkit errors --search` case-insensitive (#73).
- CI now also tests on Python 3.14, and the package metadata lists the 3.14
  classifier (#75).

### Fixed

- Exit quietly with status 141 instead of printing a traceback when the output
  pipe is closed, e.g. `dkit errors | head -1` (#51).

## [0.3.0] - 2026-10-28

### Added

- `dkit perms --add` / `--remove` — modify an existing permissions integer by
  name (add first, then remove), preserving unknown bits, with `--json` support
  (#36).
- `dkit errors` - look up a Discord JSON error code or an HTTP status code, or search all codes by text, with `--json` support (#62).
- `dkit perms --list --channel-type T|V|S` - filter listed permissions by text,
  voice or stage channel applicability. (#59)
- `dkit invite --decode URL` - read an existing OAuth2 invite URL back into its
  client ID, scopes and permissions (names and unknown bits), with `--json`
  support (#35).
- `dkit intents --list` - print every known gateway intent with its bit position,
  name, hex and decimal value in bit order, with privileged intents marked and
  `--json` support (#34).
- `dkit intents --add` / `--remove`: modify an existing intents integer by
  name (add first, then remove), preserving unknown bits, with `--json` support
  (#41).
- `dkit flags` - decode a user's public_flags / flags integer into the profile
  badge names it contains (or combine names back into the integer), with
  unknown bits reported, `0x`/`0b` input and `--json` support (#40).
- `dkit color` - convert a color between the decimal integer of an embed
  `color` field, hex and RGB. Accepts `#RRGGBB`, `RRGGBB`, `0xRRGGBB`, `#RGB`
  and decimal input (bare digits are decimal), or `--rgb R,G,B`, with `--json`
  support (@arvindkumar-ship-it, #52).
- `dkit scopes` - list and look up Discord OAuth2 scopes, with descriptions
  copied from the official table, approval-gated scopes marked, `--search`,
  "did you mean" help and `--json` support (#43).
- `dkit snowflake` — accept user, channel and role mentions (`<@ID>`, `<@!ID>`,
  `<#ID>`, `<@&ID>`) and Discord message links, labelling every decoded ID with
  what the input named; plain-ID text and `--json` output is unchanged (#42).

## [0.2.0] - 2026-10-22

### Changed

- Update the checkout and Python setup actions to releases that run on Node 24.
- Measure line and branch coverage in CI with `pytest-cov`, a dev-only
  dependency, and fail the build if it drops below 100%. The report is published
  to the job summary. Also cover the remaining untested lines: empty `--perms`
  and timestamp input, and `python -m dkit` (@arvindkumar-ship-it, #12).

### Added

- `dkit perms --list` — print every known permission with its bit position,
  name, hex and decimal value in bit order, with `--json` support (#25).
- `dkit timestamp now` — format the current UTC time truncated to whole seconds,
  case-insensitively, with `--style` and `--json` support (#26).
- `dkit channels` — look up Discord channel types by integer value or name, or list all types with `--json` support (#1).
- `dkit completion bash|zsh|fish` for offline command, flag and bundled-name completion (#6).
- `dkit snowflake` — read IDs from stdin when piped or when `-` is passed (#24).
- `dkit locales` — list Discord locale codes, look one up exactly with a
  "did you mean" suggestion, or search by language name, with `--json` support
  (@arvindkumar-ship-it, #3).
- `dkit perms --diff` — compare two permission integers and list what was removed,
  added and left unchanged, with unknown bits reported and `--json` support
  (@arvindkumar-ship-it, #15).
- Add property-based round-trip tests for `FlagSet` (permissions and intents)
  using Hypothesis, a dev-only dependency (@Samyakjain-07, #22).

## [0.1.1] - 2026-10-21

### Added

- `dkit timestamp` — format a timestamp, or a snowflake's creation time, as the
  documented Discord `<t:...>` tags, with `--style` and `--from-snowflake`
  (@dbdefault, #10).

### Changed

- Run the test suite on Linux, macOS and Windows, with the full Python-version
  matrix on Linux (@Aaqibhafeezkhan, #9).
- Document the tested platform matrix and cover ANSI-free output when stdout is
  not a TTY.

### Documentation

- Update `docs/ISSUES.md`: replace old package name `dkit` with `dkit-cli` in
  install commands, and mark issues #2 and #7 as done.

## [0.1.0] - 2026-10-20

### Added

- `dkit snowflake` - decode snowflake IDs, and build one from a date with `--from-date`.
- `dkit perms` - decode a permissions integer, or build one from names.
- `dkit invite` - build an OAuth2 invite URL with validated client ID and scopes.
- `dkit intents` - convert gateway intent names to the integer and back, with
  privileged intent warnings.
- Global `--json`, `--version` and `--no-color` flags.
- Discord constants in `dkit/data/*.json`, each with a `source` URL and a
  `last_verified` date.

[Unreleased]: https://github.com/Bytewave1/dkit/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Bytewave1/dkit/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Bytewave1/dkit/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/Bytewave1/dkit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Bytewave1/dkit/releases/tag/v0.1.0
