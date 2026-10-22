"""The command registry.

To add a command, drop a module next to this one that exposes a
``COMMAND`` object (see :mod:`dkit.core.registry`) and add it to
:data:`COMMANDS` below. Nothing else needs to change.
"""

from __future__ import annotations

from dkit.commands import (
    channels,
    color,
    completion,
    flags,
    intents,
    invite,
    locales,
    perms,
    scopes,
    snowflake,
    timestamp,
)
from dkit.core.registry import Command

#: Every command the CLI exposes, in the order they appear in ``--help``.
COMMANDS: tuple[Command, ...] = (
    snowflake.COMMAND,
    perms.COMMAND,
    invite.COMMAND,
    intents.COMMAND,
    timestamp.COMMAND,
    locales.COMMAND,
    channels.COMMAND,
    color.COMMAND,
    scopes.COMMAND,
    completion.COMMAND,
    flags.COMMAND,
)

__all__ = ["COMMANDS"]
