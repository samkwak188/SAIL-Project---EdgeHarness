"""smoke_coding fixture test — verifies add and mul work correctly."""
from examples.fixtures.smoke_coding import add, mul


def test_add():
    assert add(2, 3) == 5


def test_mul():
    assert mul(2, 3) == 6
