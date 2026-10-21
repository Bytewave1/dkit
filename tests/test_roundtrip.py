import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dkit.commands.intents import intent_flags
from dkit.commands.perms import permission_flags


@pytest.mark.parametrize(
    "make_flags",
    [permission_flags, intent_flags],
    ids=["permissions", "intents"],
)
@settings(deadline=None)
@given(value=st.integers(min_value=0, max_value=2**64 - 1))
def test_value_names_value_round_trip(make_flags, value):
    flags = make_flags()
    names = [flag.name for flag in flags.flags_in(value)]
    assert flags.value_of(names) == value & flags.mask
