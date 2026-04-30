from collections.abc import Callable, Hashable, Sequence
from typing import Any, Protocol, TypeAlias

DataItem: TypeAlias = dict[Hashable, Any] | list[Any] | tuple[Any, ...]
ContextData: TypeAlias = dict[str, Any] | None
ParsedDict: TypeAlias = dict[tuple[int, str], tuple[str, Any]]
IndentSpec: TypeAlias = int | tuple[int, int]
TableRow: TypeAlias = Sequence[Any]
TableData: TypeAlias = Sequence[TableRow]
CellConverter: TypeAlias = Callable[[Any], str]
ArgMethod: TypeAlias = Callable[..., Any]
EvalItemMethod: TypeAlias = Callable[..., Any]
EvalGroupMethod: TypeAlias = Callable[..., Any]
MatchMethodSingleArg: TypeAlias = Callable[..., bool]
MatchMethodWithArg: TypeAlias = Callable[..., bool]
MatchMethod: TypeAlias = Callable[..., bool]


class TypeMethod(Protocol):
    def __call__(self, value: Any = ..., /) -> Any: ...


__all__ = [
    "ArgMethod",
    "CellConverter",
    "ContextData",
    "DataItem",
    "EvalGroupMethod",
    "EvalItemMethod",
    "IndentSpec",
    "MatchMethod",
    "MatchMethodSingleArg",
    "MatchMethodWithArg",
    "ParsedDict",
    "TableData",
    "TableRow",
    "TypeMethod",
]
