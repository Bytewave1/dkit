# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Update the checkout and Python setup actions to releases that run on Node 24.

### Added

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

[Unreleased]: https://github.com/Bytewave1/dkit/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Bytewave1/dkit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Bytewave1/dkit/releases/tag/v0.1.0
