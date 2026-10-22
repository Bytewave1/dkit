# dkit

**An offline toolbox for Discord bot developers.**

`dkit` decodes snowflake IDs, translates permission and gateway-intent bitfields
in both directions, and builds OAuth2 invite URLs — from your terminal, with no
network access and no bot token.

[![CI](https://github.com/Bytewave1/dkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Bytewave1/dkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dkit-cli.svg)](https://pypi.org/project/dkit-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/dkit-cli.svg)](https://pypi.org/project/dkit-cli/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

```console
$ dkit snowflake 175928847299117063
175928847299117063
  Created      2016-04-30T11:18:25.796Z
  Unix ms      1462015105796
  Discord ms   41944705796
  Worker ID    1
  Process ID   0
  Increment    7
```

---

## Why dkit?

Every Discord bot developer hits the same small, annoying questions. When was
this user created? Which permissions are in `274878286912`? What integer do I
pass for these three intents? Why is the gateway closing my connection with
`4014`?

The usual answers are a random web calculator, a REPL session with a bitshift
you half-remember, or a scroll through the docs. `dkit` answers them in one
command instead, and it does so:

- **Entirely offline.** No network calls, ever. `dkit` never asks for a bot
  token, so you can safely run it on a shared machine or paste its output into
  an issue.
- **Honestly sourced.** Every bit position lives in a JSON data file that
  records the official documentation URL it came from and the date it was last
  verified. Nothing is remembered from folklore — see
  [Data and provenance](#data-and-provenance).
- **Dependency-free.** Standard library only, so `pip install dkit-cli` pulls in
  nothing else and nothing breaks next year.
- **Scriptable.** `--json` on any command gives you machine-readable output
  with stable keys, and exit codes you can branch on.
- **Correct about big numbers.** Permissions already exceed 32 bits and are
  approaching 64. `dkit` uses Python's arbitrary-precision integers throughout
  and emits permission values as JSON *strings*, exactly as the Discord API
  does, so nothing is silently truncated by a 53-bit float somewhere downstream.

## Install

Requires Python 3.10 or newer.

```console
pip install dkit-cli
```

From a checkout:

```console
git clone https://github.com/Bytewave1/dkit
cd dkit
pip install .
```

Both give you a `dkit` command. You can also run it as `python -m dkit`.

### Troubleshooting: `dkit` is not recognized

If installation succeeds but your shell cannot find `dkit`, run it through
Python instead. This does not require changing `PATH`:

```console
python -m dkit --version
```

To find the scripts directory for a user install, run:

```console
python -c "import sysconfig; print(sysconfig.get_path('scripts', sysconfig.get_preferred_scheme('user')))"
```

Add the printed directory to your `PATH`, then open a new terminal.

Alternatively, [`pipx`](https://pipx.pypa.io/) installs command-line tools in
isolated environments and makes their commands available on `PATH`:

```console
pipx install dkit-cli
```

To confirm which release is installed, use either of these commands:

```console
dkit --version
python -m pip show dkit-cli
```

## Usage

```console
$ dkit --help
usage: dkit [-h] [--json] [--no-color] [--version] <command> ...

An offline toolbox for Discord bot developers.

positional arguments:
  <command>
    snowflake  decode snowflake IDs, or build one from a date
    perms      decode a permissions integer, or build one from names
    invite     build an OAuth2 invite URL for your bot
    intents    convert gateway intent names to the integer and back
    timestamp  format a timestamp as a Discord <t:...> tag
    locales    look up Discord locale codes

options:
  -h, --help   show this help message and exit
  --version    print the version and exit

global options:
  --json       print machine-readable JSON instead of text
  --no-color   disable ANSI colors (also honours the NO_COLOR environment
               variable)

Every command works entirely offline: dkit never performs network requests
and never asks for a bot token.

run 'dkit <command> --help' for the options of a single command
```

### Global flags

| Flag | Effect |
|---|---|
| `--json` | Print machine-readable JSON instead of text |
| `--no-color` | Disable ANSI colors (`NO_COLOR` is honoured too) |
| `--version` | Print the version and exit |

Global flags work on either side of the command name: `dkit --json perms 8` and
`dkit perms 8 --json` are equivalent.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `2` | Usage error or invalid input |

Warnings (privileged intents, `ADMINISTRATOR`, unrecognised bits) go to
**stderr** in text mode and into the `warnings` array in `--json` mode, so
stdout always stays parseable.

---

### `dkit snowflake` — decode IDs, or build one from a date

```console
$ dkit snowflake 175928847299117063
175928847299117063
  Created      2016-04-30T11:18:25.796Z
  Unix ms      1462015105796
  Discord ms   41944705796
  Worker ID    1
  Process ID   0
  Increment    7
```

Several IDs at once, and hexadecimal input, both work:

```console
$ dkit snowflake 175928847299117063 80351110224678912
```

IDs can also be read from stdin when piped or by passing `-`:

```console
$ cat ids.txt | dkit snowflake
$ dkit snowflake - < ids.txt
```

The reverse direction gives you the lowest snowflake for a point in time, which
is what you want for `before`/`after` pagination:

```console
$ dkit snowflake --from-date 2016-04-30T11:18:25Z
2016-04-30T11:18:25.000Z
  Snowflake    175928843960320000
  Unix ms      1462015105000
  Discord ms   41944705000

  lowest snowflake for this millisecond (worker, process and increment are all zero)
```

Timestamps are ISO-8601. A trailing `Z` is accepted, an explicit offset such as
`+02:00` is respected, and a timestamp without an offset is read as UTC.

### `dkit perms` — permissions integer ↔ names

```console
$ dkit perms 274878286912
Permissions 274878286912
  hex 0x000000400005cc40  (8 of 52 known permissions)

  ADD_REACTIONS                        0x0000000000000040  [T/V/S]
  VIEW_CHANNEL                         0x0000000000000400  [T/V/S]
  SEND_MESSAGES                        0x0000000000000800  [T/V/S]
  EMBED_LINKS                          0x0000000000004000  [T/V/S]
  ATTACH_FILES                         0x0000000000008000  [T/V/S]
  READ_MESSAGE_HISTORY                 0x0000000000010000  [T/V/S]
  USE_EXTERNAL_EMOJIS                  0x0000000000040000  [T/V/S]
  SEND_MESSAGES_IN_THREADS             0x0000004000000000  [T]
```

`[T/V/S]` are the channel types the permission applies to (Text, Voice, Stage);
`[2FA]` marks permissions that require the server owner to have two-factor
authentication enabled when server-wide 2FA is on.

And the other way around:

```console
$ dkit perms --names SEND_MESSAGES,MANAGE_ROLES
Permissions 268437504
  hex 0x0000000010000800

  SEND_MESSAGES                        0x0000000000000800  [T/V/S]
  MANAGE_ROLES                         0x0000000010000000  [2FA, T/V/S]
```

Names are case-insensitive, and typos get a suggestion rather than a shrug:

```console
$ dkit perms --names SEND_MESSAGE
error: unknown permission name: 'SEND_MESSAGE'
  did you mean SEND_MESSAGES, SEND_TTS_MESSAGES or SEND_VOICE_MESSAGES?
$ echo $?
2
```

### Compare two permission values with `--diff`

`--diff` compares the number with a second one and sorts the bits into three
groups: only in the first value (**removed**), only in the second (**added**),
and in both (**unchanged**, shown as a count).

```console
$ dkit perms 268437504 --diff 274878286912
Permissions 268437504 -> 274878286912
  hex 0x0000000010000800 -> 0x000000400005cc40

Removed (1)
  MANAGE_ROLES                         0x0000000010000000  [2FA, T/V/S]

Added (7)
  ADD_REACTIONS                        0x0000000000000040  [T/V/S]
  VIEW_CHANNEL                         0x0000000000000400  [T/V/S]
  EMBED_LINKS                          0x0000000000004000  [T/V/S]
  ATTACH_FILES                         0x0000000000008000  [T/V/S]
  READ_MESSAGE_HISTORY                 0x0000000000010000  [T/V/S]
  USE_EXTERNAL_EMOJIS                  0x0000000000040000  [T/V/S]
  SEND_MESSAGES_IN_THREADS             0x0000004000000000  [T]

Unchanged (1)
```

Both values accept the same formats as the plain decode (`2048`, `0x800`).
Identical values are reported as such. Bits `dkit` has no name for are listed as
`unknown bits` inside the group they fall in, with a warning on stderr, rather
than being dropped. `--diff` cannot be combined with `--names`, and invalid
input exits with code 2.

### List every known permission with `--list`

`--list` prints every permission from the bundled dataset in bit order, with its
bit position, name, 64-bit hex value and decimal value:

```console
$ dkit perms --list
$ dkit perms --list --json
```

### `dkit invite` — build an OAuth2 invite URL

```console
$ dkit invite --client-id 157730590492196864 \
    --perms SEND_MESSAGES,EMBED_LINKS,READ_MESSAGE_HISTORY
Invite URL
  https://discord.com/oauth2/authorize?client_id=157730590492196864&scope=bot%20applications.commands&permissions=83968

  Client ID    157730590492196864
  Scopes       bot, applications.commands
  Permissions  83968
    - SEND_MESSAGES
    - EMBED_LINKS
    - READ_MESSAGE_HISTORY
```

- The client ID must be numeric; anything else is rejected before a URL is built.
- `--perms` takes names *or* an integer.
- `--scopes` defaults to `bot,applications.commands` and is validated against
  the official scope list, with suggestions for near-misses.
- Scopes are joined with `%20`, matching the documented encoding.

### `dkit intents` — intent names ↔ integer, with privileged warnings

```console
$ dkit intents GUILDS,GUILD_MESSAGES,MESSAGE_CONTENT
Intents 33281
  hex 0x8201  (3 of 21 known intents)

  GUILDS                           1 << 0    21 events
  GUILD_MESSAGES                   1 << 9    4 events
  MESSAGE_CONTENT                  1 << 15   no events  [privileged]

Privileged intents in this value:
  - MESSAGE_CONTENT

  These must be enabled for your application in the Discord Developer Portal
  (https://discord.com/developers/applications) under Bot -> Privileged Gateway Intents
  before they can be passed in IDENTIFY. Passing one that is not enabled
  closes the gateway connection with close code 4014.
  Apps above 10,000 users additionally need approval to keep using them.
```

The same command decodes an integer — it detects which direction you meant:

```console
$ dkit intents 33281
```

The three privileged intents are `GUILD_MEMBERS`, `GUILD_PRESENCES` and
`MESSAGE_CONTENT`. `MESSAGE_CONTENT` is listed with "no events" because it
gates message content across the API rather than mapping to gateway events.

### `dkit timestamp` — Discord message timestamp tags

```console
$ dkit timestamp 2026-10-20T08:30:00Z
Timestamp 2026-10-20T08:30:00.000Z
  Unix         1792485000

  <t:1792485000:t>   Short Time  16:20
  <t:1792485000:T>   Medium Time  16:20:30
  <t:1792485000:d>   Short Date  20/04/2021
  <t:1792485000:D>   Long Date  April 20, 2021
  <t:1792485000:f>   Long Date, Short Time  April 20, 2021 at 16:20
  <t:1792485000:F>   Full Date, Short Time  Tuesday, April 20, 2021 at 16:20
  <t:1792485000:s>   Short Date, Short Time  20/04/2021, 16:20
  <t:1792485000:S>   Short Date, Medium Time  20/04/2021, 16:20:30
  <t:1792485000:R>   Relative Time  4 years ago

  Discord renders these tags in the viewer's locale and timezone.
  Examples come from the official table (verified 2026-10-21).
```

Style letters are case-sensitive (`t` is not `T`), and an unknown one gets a
suggestion. `--style` prints just that tag, and `--from-snowflake` uses the
creation time of an ID instead of a timestamp:

```console
$ dkit timestamp 2026-10-20T08:30:00Z --style R
$ dkit timestamp --from-snowflake 175928847299117063
$ dkit timestamp now
$ dkit timestamp now --style R
```

Pass `now` (case-insensitive) to format the current UTC time, truncated to whole
seconds.

### `dkit locales` — Discord locale codes

```console
$ dkit locales de
Locale
  Code         de
  Language     German

  Codes are exact and case-sensitive: en-US, not en_US or en.
  Data comes from the official table (verified 2026-10-21).
```

With no argument it lists every locale. `--search` matches the language name,
ignoring case, and a code that does not exist gets a suggestion:

```console
$ dkit locales --search portug
Locales matching 'portug' (1)
  pt-BR  Portuguese, Brazilian

  Codes are exact and case-sensitive: en-US, not en_US or en.
  Data comes from the official table (verified 2026-10-21).
$ dkit locales en_US
error: unknown locale: 'en_US'
  did you mean en-US?
```

### `dkit channels` — Discord channel types

Look up Discord channel types by integer value or name, or list every type:

```console
$ dkit channels 15
Channel type
  Name         GUILD_FORUM
  Value        15
  Description  Channel that can only contain threads

$ dkit channels GUILD_FORUM
Channel type
  Name         GUILD_FORUM
  Value        15
  Description  Channel that can only contain threads
```

Running `dkit channels` without arguments lists every known channel type:

```console
$ dkit channels
Channel types (13)
   0  GUILD_TEXT            A text channel within a server
   1  DM                    A direct message between users
   2  GUILD_VOICE           A voice channel within a server
   ...
```

### JSON output

```console
$ dkit --json perms --names SEND_MESSAGES,MANAGE_ROLES
{
  "value": "268437504",
  "hex": "0x0000000010000800",
  "bit_count": 2,
  "permissions": [
    {
      "name": "SEND_MESSAGES",
      "bit": 11,
      "value": "2048",
      "hex": "0x0000000000000800",
      "description": "Allows for sending messages in a channel and creating threads in a forum (does not allow sending messages in threads)",
      "channel_types": ["T", "V", "S"]
    },
    {
      "name": "MANAGE_ROLES",
      "bit": 28,
      "value": "268435456",
      "hex": "0x0000000010000000",
      "description": "Allows management and editing of roles",
      "channel_types": ["T", "V", "S"],
      "requires_2fa": true
    }
  ],
  "names": ["SEND_MESSAGES", "MANAGE_ROLES"],
  "unknown_bits": [],
  "warnings": [],
  "source": {
    "source": "https://github.com/discord/discord-api-docs/blob/main/developers/topics/permissions.mdx",
    "source_rendered": "https://discord.com/developers/docs/topics/permissions",
    "last_verified": "2026-10-20"
  }
}
```

`--diff` has its own payload. Each group (`removed`, `added`, `unchanged`)
carries the same fields as a decode, and every permission integer is a string:

```console
$ dkit --json perms 5 --diff 6
{
  "first": {
    "value": "5",
    "hex": "0x0000000000000005"
  },
  "second": {
    "value": "6",
    "hex": "0x0000000000000006"
  },
  "identical": false,
  "removed": {
    "value": "1",
    "hex": "0x0000000000000001",
    "bit_count": 1,
    "permissions": [
      {
        "name": "CREATE_INSTANT_INVITE",
        "bit": 0,
        "value": "1",
        "hex": "0x0000000000000001",
        "description": "Allows creation of instant invites",
        "channel_types": ["T", "V", "S"]
      }
    ],
    "names": ["CREATE_INSTANT_INVITE"],
    "unknown_bits": []
  },
  "added": {
    "value": "2",
    "hex": "0x0000000000000002",
    "bit_count": 1,
    "permissions": [
      {
        "name": "KICK_MEMBERS",
        "bit": 1,
        "value": "2",
        "hex": "0x0000000000000002",
        "description": "Allows kicking members",
        "requires_2fa": true
      }
    ],
    "names": ["KICK_MEMBERS"],
    "unknown_bits": []
  },
  "unchanged": {
    "value": "4",
    "hex": "0x0000000000000004",
    "bit_count": 1,
    "permissions": [
      {
        "name": "BAN_MEMBERS",
        "bit": 2,
        "value": "4",
        "hex": "0x0000000000000004",
        "description": "Allows banning members",
        "requires_2fa": true
      }
    ],
    "names": ["BAN_MEMBERS"],
    "unknown_bits": []
  },
  "warnings": [],
  "source": {
    "source": "https://github.com/discord/discord-api-docs/blob/main/developers/topics/permissions.mdx",
    "source_rendered": "https://discord.com/developers/docs/topics/permissions",
    "last_verified": "2026-10-20"
  }
}
```

Every payload carries the `source` of the data it used, so output pasted into a
bug report says where its numbers came from. `unknown_bits` is non-empty when a
value contains a bit `dkit` has no name for yet — a good sign the data file
needs refreshing.

## Data and provenance

No Discord constant is hard-coded in logic. They all live in
[`src/dkit/data/`](src/dkit/data/):

| File | Contents | Official source |
|---|---|---|
| `permissions.json` | 52 permission flags, bits 0–52 | [topics/permissions](https://discord.com/developers/docs/topics/permissions) |
| `intents.json` | 21 gateway intents, privileged flags, associated events | [events/gateway](https://discord.com/developers/docs/events/gateway#list-of-intents) |
| `snowflake.json` | Discord epoch and the snowflake bit layout | [reference#snowflakes](https://discord.com/developers/docs/reference#snowflakes) |
| `oauth2.json` | Authorization URL and the 29 OAuth2 scopes | [topics/oauth2](https://discord.com/developers/docs/topics/oauth2) |
| `timestamp_styles.json` | The nine `<t:...>` timestamp styles and their examples | [reference#message-formatting-timestamp-styles](https://discord.com/developers/docs/reference#message-formatting-timestamp-styles) |
| `locales.json` | The 32 locale codes and their language names | [reference#locales](https://discord.com/developers/docs/reference#locales) |
| `channel_types.json` | The 13 channel types, integer values and descriptions | [resources/channel#channel-object-channel-types](https://discord.com/developers/docs/resources/channel#channel-object-channel-types) |

Each file records a `source` URL and a `last_verified` date. Two details worth
knowing, both faithful to the official tables:

- Permission bit **47 is unassigned** and is intentionally absent.
- Intent bits **17–19 and 22–23 are unassigned** and are intentionally absent.

Values are stored as *bit positions*; `dkit` derives each value as `1 << bit`,
and the test suite asserts that the `hex` field in each file agrees with its
bit. See [CONTRIBUTING.md](CONTRIBUTING.md#updating-the-data-files) for how to
refresh them.

## Platform support

CI tests Linux on Python 3.10, 3.11, 3.12 and 3.13, plus macOS and Windows
on Python 3.13. The CLI disables ANSI color codes when output is redirected or
piped, keeping captured output suitable for scripts across platforms.

## Contributing

Contributions are very welcome, and the project is deliberately easy to extend:
**adding a command means adding one file and registering it in one place.**

```console
git clone https://github.com/Bytewave1/dkit
cd dkit
pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

CI measures line and branch coverage with `pytest-cov` and fails if it drops
below the `fail_under` threshold in `pyproject.toml`, which is currently 100%.
The per-file report, with the missing lines, is printed on every run and
published to the job summary. The same command works locally:

```console
python -m pytest -q --cov
```

- [CONTRIBUTING.md](CONTRIBUTING.md) walks through adding a command and
  updating the data files.
- [docs/ISSUES.md](docs/ISSUES.md) has eight ready-to-file "good first issue"
  ideas if you want somewhere to start.

Please keep the two ground rules: **no runtime dependencies**, and **no network
access at runtime**.

## License

[MIT](LICENSE).

`dkit` is an unofficial tool and is not affiliated with or endorsed by Discord.
"Discord" is a trademark of Discord Inc.
