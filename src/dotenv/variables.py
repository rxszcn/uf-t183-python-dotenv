import re
from abc import ABCMeta, abstractmethod
from typing import Iterator, Mapping, Optional, Pattern

_posix_variable: Pattern[str] = re.compile(
    r"""
    \$\{
        (?P<name>[^\}:]*)
        (?::-
            (?P<default>[^\}]*)
        )?
    \}
    """,
    re.VERBOSE,
)

# A run of backslashes immediately followed by a dollar sign.
_escaped_dollar: Pattern[str] = re.compile(r"\\+\$")


def _decode_escaped_dollars(value: str) -> str:
    r"""Decode backslash-escaped dollars in literal text.

    A backslash is special only where it directly precedes a `$`: each `\\`
    pair collapses to a single literal backslash, and an odd trailing
    backslash escapes the `$`, making it a literal dollar sign. Backslashes
    in any other position (e.g. in Windows paths) are left untouched.
    """

    def decode_match(match: "re.Match[str]") -> str:
        backslashes = len(match.group(0)) - 1
        return "\\" * (backslashes // 2) + "$"

    return _escaped_dollar.sub(decode_match, value)


class Atom(metaclass=ABCMeta):
    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    @abstractmethod
    def resolve(self, env: Mapping[str, Optional[str]]) -> str: ...


class Literal(Atom):
    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Literal(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash((self.__class__, self.value))

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        return self.value


class Variable(Atom):
    def __init__(self, name: str, default: Optional[str]) -> None:
        self.name = name
        self.default = default

    def __repr__(self) -> str:
        return f"Variable(name={self.name}, default={self.default})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.name, self.default) == (other.name, other.default)

    def __hash__(self) -> int:
        return hash((self.__class__, self.name, self.default))

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        default = self.default if self.default is not None else ""
        result = env.get(self.name, default)
        return result if result is not None else ""


def parse_variables(value: str) -> Iterator[Atom]:
    cursor = 0

    for match in _posix_variable.finditer(value):
        (start, end) = match.span()
        name = match["name"]
        default = match["default"]

        # Count the backslashes immediately preceding the `$`. An odd run
        # means the `$` itself is escaped, so the whole `${...}` is literal
        # text; an even run collapses to half as many literal backslashes and
        # the variable is interpolated as usual.
        backslashes = 0
        while (
            start - backslashes - 1 >= cursor
            and value[start - backslashes - 1] == "\\"
        ):
            backslashes += 1

        if start - backslashes > cursor:
            yield Literal(
                value=_decode_escaped_dollars(value[cursor : start - backslashes])
            )

        if backslashes % 2 == 1:
            yield Literal(
                value="\\" * (backslashes // 2) + "$" + match.group(0)[1:]
            )
        else:
            if backslashes:
                yield Literal(value="\\" * (backslashes // 2))
            yield Variable(name=name, default=default)
        cursor = end

    length = len(value)
    if cursor < length:
        yield Literal(value=_decode_escaped_dollars(value[cursor:length]))
