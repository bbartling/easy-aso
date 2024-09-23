import pytest
from easy_aso import EasyASO


class IncompleteBot(EasyASO):
    async def on_start(self):
        pass


# The IncompleteBot class is missing on_step and on_stop, so it should raise a TypeError


def test_missing_abstract_methods():
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class IncompleteBot without an implementation for abstract methods 'on_step', 'on_stop'",
    ):
        bot = IncompleteBot()
