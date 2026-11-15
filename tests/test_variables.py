import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", []),
        ("a", [Literal(value="a")]),
        ("${a}", [Variable(name="a", default=None)]),
        ("${a:-b}", [Variable(name="a", default="b")]),
        (
            "${a}${b}",
            [
                Variable(name="a", default=None),
                Variable(name="b", default=None),
            ],
        ),
        (
            "a${b}c${d}e",
            [
                Literal(value="a"),
                Variable(name="b", default=None),
                Literal(value="c"),
                Variable(name="d", default=None),
                Literal(value="e"),
            ],
        ),
    ],
)
def test_parse_variables(value, expected):
    result = parse_variables(value)

    assert list(result) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        # A backslash directly before a `$` escapes it, so no interpolation
        # happens and the pair decodes to a literal dollar sign.
        ("\\$", [Literal(value="$")]),
        ("a\\$b", [Literal(value="a$b")]),
        ("\\${a}", [Literal(value="${a}")]),
        # An even run of backslashes collapses to half as many literal
        # backslashes and the variable is interpolated as usual.
        ("\\\\${a}", [Literal(value="\\"), Variable(name="a", default=None)]),
        ("\\\\$", [Literal(value="\\$")]),
        # An odd run collapses the pairs and escapes the dollar.
        ("\\\\\\${a}", [Literal(value="\\${a}")]),
        # Escaped dollars and live variables mix freely.
        (
            "x\\${a}y${b}z",
            [
                Literal(value="x"),
                Literal(value="${a}"),
                Literal(value="y"),
                Variable(name="b", default=None),
                Literal(value="z"),
            ],
        ),
        # A backslash not directly before a `$` is left untouched, so
        # Windows paths and UNC paths pass through unchanged.
        ("C:\\Users", [Literal(value="C:\\Users")]),
        ("\\\\server\\share", [Literal(value="\\\\server\\share")]),
    ],
)
def test_parse_variables_escaped_dollars(value, expected):
    result = parse_variables(value)

    assert list(result) == expected
