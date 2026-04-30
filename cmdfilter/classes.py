from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Any

from .typing_utils import (
    ArgMethod,
    EvalGroupMethod,
    EvalItemMethod,
    MatchMethod,
    TypeMethod,
)

TYPE_METHOD = "type_method"
EVAL_METHOD = "eval_method"
MATCH_METHOD = "match_method"
ARG_METHOD = "arg_method"
COST = "cost"
GROUP_KEYS = "group_keys"
CONTEXT = "context"

TITLE = "title"
GRADE = "grade"
OPTIONS = "options"
KEYS = "keys"
SKIP_KEY_ERR = "skip_key_err"
DEFAULT = "default"
HELP = "help_text"


@dataclass(slots=True, frozen=True)
class Grade:
    type_method: TypeMethod
    eval_method: EvalItemMethod | EvalGroupMethod
    match_method: MatchMethod
    arg_method: ArgMethod | None = None
    cost: int = 100
    group_keys: bool = False
    context: tuple[str, ...] | None = None
    arg_accepts_context: bool = False
    eval_accepts_context: bool = False
    match_accepts_context: bool = False

    def sample_value(self) -> Any:
        return self.type_method()


@dataclass(slots=True, frozen=True)
class Layer:
    title: str
    grade: Grade
    options: tuple[str, ...]
    keys: tuple[Hashable, ...]
    skip_key_err: bool = True
    help_text: str | None = None
    default: Any = None

    @property
    def primary_option(self) -> str:
        return self.options[0]


@dataclass(slots=True, frozen=True)
class ParsedLayer:
    index: int
    layer: Layer
    option: str
    raw_arg: Any
    arg: Any

    @property
    def title(self) -> str:
        return self.layer.title

    @property
    def grade(self) -> Grade:
        return self.layer.grade

    @property
    def keys(self) -> tuple[Hashable, ...]:
        return self.layer.keys

    @property
    def skip_key_err(self) -> bool:
        return self.layer.skip_key_err


@dataclass(slots=True, frozen=True)
class ParsedCommand:
    command: str | dict[str, Any]
    parsed_layers: tuple[ParsedLayer, ...] = field(default_factory=tuple)
    ordered_parsed_layers: tuple[ParsedLayer, ...] = field(default_factory=tuple)
    unparsed: dict[str, Any] = field(default_factory=dict)
    context: Any = None

    @property
    def parsed_indices(self) -> tuple[int, ...]:
        return tuple(parsed_layer.index for parsed_layer in self.parsed_layers)

    @property
    def parsed_titles(self) -> tuple[str, ...]:
        return tuple(parsed_layer.title for parsed_layer in self.parsed_layers)

    def as_dict(self) -> dict[tuple[int, str], tuple[str, Any]]:
        result: dict[tuple[int, str], tuple[str, Any]] = {}
        for parsed_layer in self.parsed_layers:
            raw_arg = (
                parsed_layer.arg
                if isinstance(parsed_layer.arg, bool)
                else parsed_layer.raw_arg
            )
            result[(parsed_layer.index, parsed_layer.title)] = (
                parsed_layer.option,
                raw_arg,
            )
        return result


__all__ = [
    "ARG_METHOD",
    "COST",
    "CONTEXT",
    "DEFAULT",
    "EVAL_METHOD",
    "GRADE",
    "Grade",
    "GROUP_KEYS",
    "HELP",
    "KEYS",
    "Layer",
    "MATCH_METHOD",
    "OPTIONS",
    "ParsedCommand",
    "ParsedLayer",
    "SKIP_KEY_ERR",
    "TITLE",
    "TYPE_METHOD",
]
