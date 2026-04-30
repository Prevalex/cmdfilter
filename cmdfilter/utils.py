import re
from collections.abc import Callable
from dataclasses import fields
from typing import Any, cast

from .classes import Grade, Layer, ParsedLayer
from .helpers import (
    format_table_to_str,
    get_func_signature,
    inspect_name,
    inspect_upper_name,
    re_pattern,
)
from .inc import DEBUG
from .typing_utils import DataItem

IMPLICIT_CMD_PATTERN = cast(
    re.Pattern[str], re_pattern(r"^\s*([?ALLWC]*?)\s([?WRD]+?:.*)$")
)
SINGLE_CMD_PATTERN = cast(re.Pattern[str], re_pattern(r"^\s*([?WRD]+)\:{1}(.*)$"))
MULTI_CMD_PATTERN = cast(
    re.Pattern[str], re_pattern(r"^\s*([?WRD]+)\:{1}(.*?)([?WRD]+?)?\:{1}(.*)$")
)
OPTION_PATTERN = cast(re.Pattern[str], re_pattern(r"(?P<option>[?WRD]+)\s*:"))


def parse_cmdline(cmdline: str) -> tuple[str | None, dict[str, str]]:
    """Parse free text and ``option:value`` chunks from a command line."""
    text = cmdline.strip()
    if not text:
        return None, {}

    matches = list(OPTION_PATTERN.finditer(text))
    if not matches:
        return text, {}

    implicit_prefix = text[: matches[0].start()].strip()
    implicit_arg = implicit_prefix or None
    commands: dict[str, str] = {}

    for index, match in enumerate(matches):
        option = match.group("option").strip()
        arg_start = match.end()
        arg_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        commands[option] = text[arg_start:arg_end].strip()

    return implicit_arg, commands


def repr_method(method: Callable[..., Any] | None) -> str:
    """Return readable callable representation."""
    if method is None:
        return "None"
    return (
        get_func_signature(method).replace(", /", "")
        if callable(method)
        else repr(method)
    )


def repr_grade(grade: Grade) -> str:
    """Return compact representation of a grade."""
    values: list[str] = []
    for field_info in fields(grade):
        item = getattr(grade, field_info.name)
        values.append(repr_method(item) if callable(item) else str(item))
    return ", ".join(values)


def repr_layers(layers_list: list[Layer]) -> str:
    """Render layers as a table."""
    rows: list[list[Any]] = [[field_info.name for field_info in fields(Layer)]]
    for layer in layers_list:
        row = [getattr(layer, field_info.name) for field_info in fields(Layer)]
        for index, item in enumerate(row):
            if isinstance(item, Grade):
                row[index] = repr_grade(item)
        rows.append(row)
    return format_table_to_str(rows, cvt=repr, header=True)


def match_layer(
    parsed_layer: ParsedLayer,
    data: DataItem,
    *,
    skip_key_err: bool = False,
    layer_index: int | None = None,
    context: Any = None,
) -> tuple[bool, Any]:
    """Evaluate one parsed layer against a single data item."""
    if not hasattr(data, "__getitem__"):
        raise ValueError(
            f"{inspect_upper_name()}|{inspect_name()}: data item does not support key/index access: {data!r}"
        )

    type_method = parsed_layer.grade.type_method
    eval_method = parsed_layer.grade.eval_method
    match_method = parsed_layer.grade.match_method
    type_sample = type_method()

    data_values: list[Any] = []
    for key in parsed_layer.keys:
        try:
            key_value = cast(Any, data)[key]
        except (KeyError, IndexError) as exc:
            if skip_key_err:
                key_value = type_sample
            else:
                raise KeyError(
                    f"{inspect_upper_name()}|{inspect_name()}: failed to read value by key/index {key!r}: {exc}"
                ) from exc
        data_values.append(key_value)

    typed_values = tuple(type_method(value) for value in data_values)
    if parsed_layer.grade.group_keys:
        if context is not None and parsed_layer.grade.eval_accepts_context:
            eval_result = eval_method(typed_values, parsed_layer.arg, context=context)
        else:
            eval_result = eval_method(typed_values, parsed_layer.arg)
        if context is not None and parsed_layer.grade.match_accepts_context:
            match_result = match_method(eval_result, parsed_layer.arg, context=context)
        else:
            match_result = match_method(eval_result, parsed_layer.arg)
    else:
        compare_arg = (
            True
            if isinstance(type_sample, bool) and not parsed_layer.arg
            else parsed_layer.arg
        )
        if context is not None and parsed_layer.grade.eval_accepts_context:
            eval_result = tuple(
                eval_method(value, compare_arg, context=context)
                for value in typed_values
            )
        else:
            eval_result = tuple(
                eval_method(value, compare_arg) for value in typed_values
            )
        if context is not None and parsed_layer.grade.match_accepts_context:
            match_result = match_method(eval_result, context=context)
        else:
            match_result = match_method(eval_result)
        if isinstance(type_sample, bool) and not parsed_layer.arg:
            match_result = not match_result

    if DEBUG:
        print(
            f" layer #{layer_index}: "
            f"eval_method({typed_values!r}, {parsed_layer.arg}) = {eval_result!r} => {match_result}"
        )
    return match_result, eval_result


__all__ = [
    "IMPLICIT_CMD_PATTERN",
    "MULTI_CMD_PATTERN",
    "OPTION_PATTERN",
    "SINGLE_CMD_PATTERN",
    "match_layer",
    "parse_cmdline",
    "repr_grade",
    "repr_layers",
    "repr_method",
]
