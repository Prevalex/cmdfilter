from collections.abc import Callable, Hashable, Sequence
from types import SimpleNamespace
from typing import Any

from .checkers import (
    _verified_bool,
    _verified_cost,
    _verified_default,
    _verified_grade,
    _verified_help,
    _verified_implicit_index,
    _verified_keys,
    _verified_layers,
    _verified_method,
    _verified_options,
    _verified_title,
)
from .classes import (
    ARG_METHOD,
    CONTEXT,
    COST,
    DEFAULT,
    EVAL_METHOD,
    GRADE,
    GROUP_KEYS,
    HELP,
    KEYS,
    MATCH_METHOD,
    OPTIONS,
    SKIP_KEY_ERR,
    TITLE,
    TYPE_METHOD,
    Grade,
    Layer,
    ParsedCommand,
    ParsedLayer,
)
from .helpers import (
    accepts_keyword,
    check_func_signature,
    get_func_signature,
    inspect_name,
    inspect_upper_name,
    is_iter_of_str,
    repr_type,
)
from .typing_utils import (
    ArgMethod,
    ContextData,
    DataItem,
    EvalGroupMethod,
    EvalItemMethod,
    MatchMethod,
    TypeMethod,
)
from .utils import match_layer, parse_cmdline, repr_layers, repr_method


class Selector:
    def __init__(
        self,
        layers: list[Layer],
        *,
        select: Callable[[list[bool]], bool] = all,
        stop: Callable[[bool], bool] | None = None,
        optimize: bool = True,
        implicit_index: int = 0,
    ) -> None:
        self._layers = tuple(_verified_layers(layers))
        self._select_method = _verified_method(select, "select")
        self._stop_method = _verified_method(stop, "stop") if stop is not None else None
        self._sort_layers = _verified_bool(optimize, "optimize")
        self._implicit_index = _verified_implicit_index(
            implicit_index, len(self._layers)
        )
        self._option_to_index = self._build_option_index()
        self._title_to_index = self._build_title_index()
        self._run_order = self._build_run_order()

    def _build_option_index(self) -> dict[str, int]:
        option_to_index: dict[str, int] = {}
        for index, layer in enumerate(self._layers):
            for option in layer.options:
                if option in option_to_index:
                    raise ValueError(
                        f"{inspect_upper_name()}|{inspect_name()}: duplicate option {option!r}."
                    )
                option_to_index[option] = index
        return option_to_index

    def _build_title_index(self) -> dict[str, int]:
        title_to_index: dict[str, int] = {}
        for index, layer in enumerate(self._layers):
            if layer.title in title_to_index:
                raise ValueError(
                    f"{inspect_upper_name()}|{inspect_name()}: duplicate layer title {layer.title!r}."
                )
            title_to_index[layer.title] = index
        return title_to_index

    def _build_run_order(self) -> tuple[int, ...]:
        order = [
            (layer.grade.cost, len(layer.keys), index)
            for index, layer in enumerate(self._layers)
        ]
        if self._sort_layers:
            order.sort()
        return tuple(index for _, _, index in order)

    @property
    def implicit_index(self) -> int:
        return self._implicit_index

    @property
    def implicit_title(self) -> str:
        return self._layers[self._implicit_index].title

    @property
    def layers(self) -> list[Layer]:
        return list(self._layers)

    def __len__(self) -> int:
        return len(self._layers)

    def __iter__(self):
        return iter(self._layers)

    def __getitem__(self, selector: int | slice) -> Layer | list[Layer]:
        if isinstance(selector, slice):
            return list(self._layers[selector])
        if isinstance(selector, int):
            return self.read_layer(selector)
        raise TypeError(
            f"{inspect_upper_name()}|{inspect_name()}: invalid layer selector {selector!r}. "
            "Supported selectors are int and slice."
        )

    def __repr__(self) -> str:
        return (
            f"Selector(select={repr_method(self._select_method)}, "
            f"stop={repr_method(self._stop_method)}, "
            f"implicit_index={self._implicit_index}, "
            f"optimize={self._sort_layers})"
        )

    def __str__(self) -> str:
        return (
            f"Selector\n"
            f"select={repr_method(self._select_method)}\n"
            f"stop={repr_method(self._stop_method)}\n"
            f"implicit_index={self._implicit_index}\n"
            f"run_order={self._run_order}\n"
            f"layers:\n{repr_layers(list(self._layers))}"
        )

    def read_layer(self, index: int) -> Layer:
        if not isinstance(index, int):
            raise TypeError(
                f"{inspect_upper_name()}|{inspect_name()}: layer index must be int. Got {repr_type(index)}"
            )
        try:
            return self._layers[index]
        except IndexError as exc:
            raise IndexError(
                f"{inspect_upper_name()}|{inspect_name()}: layer with index {index} does not exist."
            ) from exc

    def layer_index_by_title(self, title: str, exception: bool = True) -> int:
        index = self._title_to_index.get(title, -1)
        if index < 0 and exception:
            raise ValueError(
                f'{inspect_upper_name()}|{inspect_name()}: layer with title "{title}" not found'
            )
        return index

    def layer_title_by_index(self, index: int, exception: bool = True) -> str:
        try:
            return self._layers[index].title
        except IndexError as exc:
            if exception:
                raise IndexError(
                    f"{inspect_upper_name()}|{inspect_name()}: there is no layer with index {index}"
                ) from exc
            return ""

    def get_layer_index_by_options(
        self, options: str | tuple[str, ...], *, exception: bool = True
    ) -> int:
        normalized_options = _verified_options(options)
        index = self._option_to_index.get(normalized_options[0], -1)
        if index >= 0 and all(
            option in self._layers[index].options for option in normalized_options
        ):
            return index
        if exception:
            raise ValueError(
                f"{inspect_upper_name()}|{inspect_name()}: no layer found with options {normalized_options!r}"
            )
        return -1

    def about(self) -> str:
        lines: list[str] = []
        for layer in self._layers:
            arg_type = layer.grade.sample_value().__class__.__name__
            lines.append(
                f"[{'|'.join(layer.options)}]:<{arg_type}> - {layer.help_text}"
            )
        return "\n".join(lines)

    def _normalize_inject(self, inject: dict[Any, Any] | None) -> dict[str, Any]:
        if inject is None:
            return {}
        if not isinstance(inject, dict):
            raise TypeError(
                f"{inspect_upper_name()}|{inspect_name()}: inject must be dict or None. Got {type(inject)}"
            )

        normalized: dict[str, Any] = {}
        for key, value in inject.items():
            option = _verified_options(key)[0]
            normalized[option] = value
        return normalized

    def _normalize_context_map(self, context: dict[str, Any] | None) -> dict[str, Any]:
        if context is None:
            return {}
        if not isinstance(context, dict):
            raise TypeError(
                f"{inspect_upper_name()}|{inspect_name()}: context must be dict or None. Got {type(context)}"
            )
        return {str(key): value for key, value in context.items()}

    def _context_fields_from_layers(
        self, parsed_layers: Sequence[ParsedLayer]
    ) -> tuple[str, ...]:
        fields: list[str] = []
        seen: set[str] = set()
        for parsed_layer in parsed_layers:
            names = parsed_layer.grade.context or ()
            for name in names:
                if name not in seen:
                    seen.add(name)
                    fields.append(name)
        return tuple(fields)

    def _build_context_object_from_names(
        self,
        field_names: Sequence[str],
        context: dict[str, Any] | None,
    ) -> Any:
        context_key = tuple(field_names)
        if not context_key:
            return None

        source = self._normalize_context_map(context)
        values: dict[str, Any] = {}
        for name in context_key:
            if name in source:
                values[name] = source[name]
            else:
                values[name] = None
        return SimpleNamespace(**values)

    def _build_context_object(
        self,
        parsed_layers: Sequence[ParsedLayer],
        context: dict[str, Any] | None,
    ) -> Any:
        return self._build_context_object_from_names(
            self._context_fields_from_layers(parsed_layers),
            context,
        )

    def _build_layer_context(self, layer: Layer, context: dict[str, Any] | None) -> Any:
        return self._build_context_object_from_names(layer.grade.context or (), context)

    def _coerce_arg(self, layer: Layer, raw_arg: Any, *, context: Any = None) -> Any:
        arg = layer.grade.type_method(raw_arg)
        if layer.grade.arg_method is not None:
            if context is not None and layer.grade.arg_accepts_context:
                arg = layer.grade.arg_method(arg, context=context)
            else:
                arg = layer.grade.arg_method(arg)
        return arg

    def _parse_dict_command(
        self, command: dict[Any, Any], inject: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        command_map: dict[str, Any] = {}
        unparsed: dict[str, Any] = {}

        for raw_option, raw_arg in (dict(command) | inject).items():
            try:
                option = _verified_options(raw_option)[0]
            except TypeError:
                option = str(raw_option).strip()

            if option in self._option_to_index:
                command_map[option] = raw_arg
            else:
                unparsed[option] = raw_arg
        return command_map, unparsed

    def _parse_string_command(
        self, command: str, inject: dict[str, Any]
    ) -> tuple[str | None, dict[str, Any], dict[str, Any], str]:
        normalized_command = command.strip()
        implicit_arg, command_map = parse_cmdline(normalized_command)
        command_map |= inject
        unparsed = {
            option: raw_arg
            for option, raw_arg in command_map.items()
            if option not in self._option_to_index
        }
        parsed_map = {
            option: raw_arg
            for option, raw_arg in command_map.items()
            if option in self._option_to_index
        }
        return implicit_arg, parsed_map, unparsed, normalized_command

    def parse(
        self,
        command: str | dict[Any, Any],
        *,
        inject: dict[Any, Any] | None = None,
        context: ContextData = None,
    ) -> ParsedCommand:
        inject_map = self._normalize_inject(inject)
        parsed_layers_by_index: dict[int, ParsedLayer] = {}
        unparsed: dict[str, Any] = {}
        source_command: str | dict[str, Any]

        if isinstance(command, str):
            implicit_arg, command_map, unparsed, source_command = (
                self._parse_string_command(command, inject_map)
            )
        elif isinstance(command, dict):
            implicit_arg = None
            command_map, unparsed = self._parse_dict_command(command, inject_map)
            source_command = dict(command) | inject_map
        else:
            raise ValueError(
                f"{inspect_upper_name()}|{inspect_name()}: command container must be str or dict. "
                f"Got {repr_type(command)}"
            )

        for option, raw_arg in command_map.items():
            index = self._option_to_index[option]
            layer = self._layers[index]
            layer_context = self._build_layer_context(layer, context)
            parsed_layers_by_index[index] = ParsedLayer(
                index=index,
                layer=layer,
                option=option,
                raw_arg=raw_arg,
                arg=self._coerce_arg(layer, raw_arg, context=layer_context),
            )

        implicit_layer = self._layers[self._implicit_index]
        if self._implicit_index not in parsed_layers_by_index:
            default_raw_arg = (
                implicit_arg if implicit_arg is not None else implicit_layer.default
            )
            if default_raw_arg is not None:
                implicit_context = self._build_layer_context(implicit_layer, context)
                parsed_layers_by_index[self._implicit_index] = ParsedLayer(
                    index=self._implicit_index,
                    layer=implicit_layer,
                    option=implicit_layer.primary_option,
                    raw_arg=default_raw_arg,
                    arg=self._coerce_arg(
                        implicit_layer, default_raw_arg, context=implicit_context
                    ),
                )

        parsed_layers = tuple(
            parsed_layers_by_index[index] for index in sorted(parsed_layers_by_index)
        )
        ordered_parsed_layers = tuple(
            parsed_layers_by_index[index]
            for index in self._run_order
            if index in parsed_layers_by_index
        )
        context_obj = self._build_context_object(parsed_layers, context)
        return ParsedCommand(
            command=source_command,
            parsed_layers=parsed_layers,
            ordered_parsed_layers=ordered_parsed_layers,
            unparsed=unparsed,
            context=context_obj,
        )

    def parse_query(
        self,
        command: str | dict[Any, Any],
        *,
        inject: dict[Any, Any] | None = None,
        context: ContextData = None,
    ) -> ParsedCommand:
        return self.parse(command, inject=inject, context=context)

    def _ordered_parsed_layers(self, parsed: ParsedCommand) -> tuple[ParsedLayer, ...]:
        if parsed.ordered_parsed_layers:
            return parsed.ordered_parsed_layers
        by_index = {
            parsed_layer.index: parsed_layer for parsed_layer in parsed.parsed_layers
        }
        return tuple(by_index[index] for index in self._run_order if index in by_index)

    def match(
        self,
        parsed: ParsedCommand,
        data: DataItem,
        /,
    ) -> tuple[bool, Any]:
        matches: list[bool] = []
        implicit_value: Any = None
        context_obj = parsed.context

        for parsed_layer in self._ordered_parsed_layers(parsed):
            layer_match, eval_value = match_layer(
                parsed_layer,
                data,
                skip_key_err=parsed_layer.skip_key_err,
                layer_index=parsed_layer.index,
                context=context_obj,
            )
            if parsed_layer.index == self._implicit_index:
                implicit_value = eval_value
            matches.append(bool(layer_match))

            if self._stop_method is not None and self._stop_method(layer_match):
                break
            if layer_match and self._select_method is any:
                break
            if not layer_match and self._select_method is all:
                break

        return bool(self._select_method(matches)), implicit_value

    def match_parsed(
        self,
        parsed: ParsedCommand,
        data: DataItem,
        /,
    ) -> tuple[bool, Any]:
        return self.match(parsed, data)

    def match_many(
        self,
        parsed: ParsedCommand,
        list_of_objs: Sequence[DataItem],
    ) -> list[tuple[int, Any]]:
        if not isinstance(list_of_objs, Sequence) or isinstance(list_of_objs, str):
            raise TypeError(
                f"{inspect_upper_name()}|{inspect_name()}: list_of_objs expected Sequence but not str. "
                f"Got {repr_type(list_of_objs)}"
            )
        matches: list[tuple[int, Any]] = []
        for index, obj in enumerate(list_of_objs):
            match_result, value = self.match(parsed, obj)
            if match_result:
                matches.append((index, value))
        return matches

    def match_objs_in_list_parsed(
        self,
        parsed: ParsedCommand,
        list_of_objs: Sequence[DataItem],
    ) -> list[tuple[int, Any]]:
        return self.match_many(parsed, list_of_objs)


def grade(
    type_method: TypeMethod,
    eval_method: EvalItemMethod | EvalGroupMethod,
    match_method: MatchMethod,
    arg_method: ArgMethod | None = None,
    group_keys: bool = False,
    cost: int = 100,
    context: str | tuple[str, ...] | None = None,
) -> Grade:
    args: dict[str, Any] = {
        TYPE_METHOD: _verified_method(type_method, TYPE_METHOD),
        EVAL_METHOD: _verified_method(eval_method, EVAL_METHOD),
        MATCH_METHOD: _verified_method(match_method, MATCH_METHOD),
        GROUP_KEYS: _verified_bool(group_keys, GROUP_KEYS),
        COST: _verified_cost(cost),
        "arg_accepts_context": bool(
            arg_method is not None and accepts_keyword(arg_method, "context")
        ),
        "eval_accepts_context": accepts_keyword(eval_method, "context"),
        "match_accepts_context": accepts_keyword(match_method, "context"),
    }
    if arg_method is not None:
        args[ARG_METHOD] = _verified_method(arg_method, ARG_METHOD)
    if context is not None:
        args[CONTEXT] = _normalize_grade_context(context)

    expected_match_arity = 2 if group_keys else 1
    if not check_func_signature(match_method, nargs=expected_match_arity):
        raise ValueError(
            f"{inspect_upper_name()}|{inspect_name()}: match_method must accept {expected_match_arity} argument(s). "
            f"Got {get_func_signature(match_method)}"
        )
    return Grade(**args)


def _normalize_grade_context(context: str | tuple[str, ...]) -> tuple[str, ...]:
    context_names: tuple[str, ...]
    if isinstance(context, str):
        context_names = (context,)
    elif is_iter_of_str(context, nostr=True, nonempty=True):
        context_names = tuple(context)
    else:
        raise TypeError(
            f"{inspect_upper_name()}|{inspect_name()}: context must be str, tuple[str, ...] or None. "
            f"Got {repr_type(context)}"
        )

    invalid = [name for name in context_names if not name.isidentifier()]
    if invalid:
        raise ValueError(
            f"{inspect_upper_name()}|{inspect_name()}: context names must be valid identifiers. Got {invalid!r}"
        )
    return context_names


def layer(
    title: str,
    grade_obj: Grade,
    options: str | tuple[str, ...],
    *,
    keys: Hashable | tuple[Hashable, ...],
    default: Any = None,
    skip_key_err: bool = False,
    about: str | None = None,
) -> Layer:
    return Layer(
        **{
            TITLE: _verified_title(title, "title"),
            GRADE: _verified_grade(grade_obj),
            OPTIONS: _verified_options(options),
            KEYS: _verified_keys(keys),
            SKIP_KEY_ERR: _verified_bool(skip_key_err, SKIP_KEY_ERR),
            DEFAULT: _verified_default(default, grade_obj),
            HELP: _verified_help(about),
        }
    )


__all__ = [
    "Selector",
    "grade",
    "layer",
]
