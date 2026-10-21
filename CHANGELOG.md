# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Update the checkout and Python setup actions to releases that run on Node 24.

### Added

- Coverage reporting with `pytest-cov` in CI and full test coverage for core parsing and CLI invocation (#12).
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

- Renamed the repository from `discord-kit` to `dkit` and the PyPI distribution
  from `discord-kit-cli` to `dkit-cli` to follow Discord's developer terms of
  service.
- Permissions and intents bit tables updated to the current Discord documentation
  (verified 2026-10-20).

## [0.1.0] - 2026-10-20

### Added

- `dkit snowflake` - decode snowflake IDs, and build one from a date with `--from-date`.
- `dkit perms` - decode a permissions integer, or build one from names.
- `dkit intents` - decode gateway intents, or build one from names.
- `dkit invite` - generate bot invite URLs with permissions and scopes.
- Fully offline operation with no network calls and no dependencies.
