import re
from collections.abc import Callable, Hashable
from typing import Any

from .classes import SKIP_KEY_ERR, Grade, Layer
from .helpers import inspect_name, inspect_upper_name, repr_type


def _raise_type_error(message: str) -> None:
    raise TypeError(f"{inspect_upper_name()}|{inspect_name()}: {message}")


def _raise_value_error(message: str) -> None:
    raise ValueError(f"{inspect_upper_name()}|{inspect_name()}: {message}")


def _verified_grade(grade_obj: Grade, /) -> Grade:
    if not isinstance(grade_obj, Grade):
        _raise_type_error(
            f"grade must be an instance of {Grade.__name__}. Got {repr_type(grade_obj)}."
        )
    return grade_obj


def _verified_method(method: Callable[..., Any], name: str) -> Callable[..., Any]:
    if not callable(method):
        _raise_type_error(f"{name} must be callable. Got {method!r}.")
    return method


def _verified_help(help_text: str | None) -> str | None:
    return None if help_text is None else str(help_text).strip()


def _verified_keys(
    keys: tuple[Hashable, ...] | list[Hashable] | Hashable,
) -> tuple[Hashable, ...]:
    if isinstance(keys, (tuple, list)):
        if not keys:
            _raise_type_error(f"keys must not be empty. Got {keys!r}.")
        items = tuple(keys)
    elif isinstance(keys, Hashable):
        items = (keys,)
    else:
        _raise_type_error(
            "keys must be a hashable value or a tuple/list of hashable values. "
            f"Got {repr_type(keys)}."
        )

    normalized: list[Hashable] = []
    for key in items:
        if not isinstance(key, Hashable):
            _raise_type_error(
                f"all keys must be hashable. Got invalid key {key!r} in {items!r}."
            )
        if isinstance(key, str):
            key = key.strip()
            if not key:
                _raise_type_error(f"string keys must not be blank. Got {items!r}.")
        normalized.append(key)
    return tuple(normalized)


def _verified_bool(flag: bool, name: str) -> bool:
    if not isinstance(flag, bool):
        _raise_type_error(f"{name} must be bool. Got {repr_type(flag)}.")
    return flag


def _verified_options(options: str | tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if isinstance(options, str):
        raw_options: tuple[str, ...] = (options,)
    elif isinstance(options, (tuple, list)):
        raw_options = tuple(options)
    else:
        _raise_type_error(
            "options must be a string or a tuple/list of strings. "
            f"Got {repr_type(options)}."
        )

    normalized: list[str] = []
    for option in raw_options:
        if not isinstance(option, str):
            _raise_type_error(
                f"all options must be strings. Got invalid option {option!r}."
            )
        option = option.strip()
        if not option:
            _raise_type_error(f"options must not be blank. Got {raw_options!r}.")
        if re.search(r"\s", option):
            _raise_type_error(f"options must not contain whitespace. Got {option!r}.")
        normalized.append(option)

    return tuple(dict.fromkeys(normalized))


def _verified_default(default: Any, grade_obj: Grade) -> Any:
    _verified_grade(grade_obj)
    if default is None:
        return None
    try:
        return grade_obj.type_method(default)
    except (TypeError, ValueError) as exc:
        _raise_type_error(
            f"could not convert default={default!r} using grade.type_method."
        )
        raise AssertionError("unreachable") from exc


def _verified_cost(cost: int) -> int:
    if not isinstance(cost, int):
        _raise_type_error(f"cost must be int. Got {repr_type(cost)}.")
    return cost


def _verified_layer(layer: Layer) -> Layer:
    if not isinstance(layer, Layer):
        _raise_value_error(
            f"layer must be an instance of {Layer.__name__}. Got {repr_type(layer)}."
        )
    _verified_grade(layer.grade)
    _verified_options(layer.options)
    _verified_keys(layer.keys)
    _verified_bool(layer.skip_key_err, SKIP_KEY_ERR)
    return layer


def _verified_layers(layers: list[Layer] | tuple[Layer, ...]) -> list[Layer]:
    if not isinstance(layers, (list, tuple)):
        _raise_type_error(f"layers must be a list or tuple. Got {repr_type(layers)}.")
    if not layers:
        _raise_value_error("layers must not be empty.")
    return [_verified_layer(layer) for layer in layers]


def _verified_implicit_index(implicit_index: int, len_of_layers: int) -> int:
    if not isinstance(implicit_index, int):
        _raise_type_error(
            f"implicit_index must be int >= 0. Got {repr_type(implicit_index)}."
        )
    if not 0 <= implicit_index < len_of_layers:
        raise IndexError(
            f"{inspect_upper_name()}|{inspect_name()}: implicit_index must be within [0, {len_of_layers - 1}]. "
            f"Got {implicit_index!r}."
        )
    return implicit_index


def _verified_title(title: str, var_name: str, spaces: bool = True) -> str:
    if not isinstance(title, str):
        _raise_type_error(f"{var_name} must be str. Got {repr_type(title)}.")
    normalized = title.strip()
    if not normalized:
        _raise_type_error(f"{var_name} must not be blank.")
    if not spaces and re.search(r"\s", normalized):
        _raise_type_error(
            f"{var_name} must not contain whitespace. Got {normalized!r}."
        )
    return normalized


__all__ = [
    "_verified_bool",
    "_verified_cost",
    "_verified_default",
    "_verified_grade",
    "_verified_help",
    "_verified_implicit_index",
    "_verified_keys",
    "_verified_layer",
    "_verified_layers",
    "_verified_method",
    "_verified_options",
    "_verified_title",
]
