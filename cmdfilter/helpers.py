import inspect
import re
from collections.abc import Iterable
from types import GeneratorType
from typing import Any

from .inc import WARNINGS
from .typing_utils import CellConverter, IndentSpec, TableData

FFORMAT_ALIGN_LIST = ("<", ">", "^", "=")
FALSE_TABLE = frozenset(
    {
        "",
        "NONE",
        "FALSE",
        "NUL",
        "NULL",
        "-",
        "_",
        "N",
        "NO",
        "\u041d\u0415\u0422",
        "\u041d\u0406",
        "0",
        "0.0",
        "EMPTY",
    }
)

_LANG_YES_NO = {
    "ru": ("\u0414\u0430", "\u041d\u0435\u0442"),
    "ua": ("\u0422\u0430\u043a", "\u041d\u0456"),
}

_PATTERN_PARTS = {
    "?LAT": r"\w",
    "?CYR": r"\u0430-\u044f\u0410-\u042f\u0456\u0406\u0457\u0407\u0454\u0404\u0491\u0490",
}
_PATTERN_PARTS["?WRD"] = _PATTERN_PARTS["?LAT"] + _PATTERN_PARTS["?CYR"] + r"\-@#$&*\."
_PATTERN_PARTS["?TXT"] = _PATTERN_PARTS["?WRD"] + r"\s"
_PATTERN_PARTS["?BRA"] = r"<>{}()\[\]\u00ab\u00bb\"'"
_PATTERN_PARTS["?SYM"] = r"=_+\-!?@#\u2116$%\^&*~\/\\.,;|:"
_PATTERN_PARTS["?SYMWC"] = r"=+\-!?@#\u2116$%\^&*~\/\\.,;|"
_PATTERN_PARTS["?ALL"] = (
    _PATTERN_PARTS["?LAT"]
    + _PATTERN_PARTS["?CYR"]
    + _PATTERN_PARTS["?BRA"]
    + _PATTERN_PARTS["?SYM"]
    + r"\s"
)
_PATTERN_PARTS["?ALLWC"] = (
    _PATTERN_PARTS["?LAT"]
    + _PATTERN_PARTS["?CYR"]
    + _PATTERN_PARTS["?BRA"]
    + _PATTERN_PARTS["?SYMWC"]
    + r"\s"
)
_PATTERN_PARTS_SORTED = sorted(
    _PATTERN_PARTS.items(), key=lambda item: (len(item[0]), item[0]), reverse=True
)


def fformat(arg: Any, *, width: int | None = None, align: str | None = None) -> str:
    """Format scalar values with a compact, readable default style."""
    if align not in FFORMAT_ALIGN_LIST:
        align = FFORMAT_ALIGN_LIST[0]
    if not isinstance(width, int):
        width = 0

    if isinstance(arg, bool):
        return f"{str(arg):{align}{width}}"
    if isinstance(arg, int):
        return f"{arg:{align}{width},d}"
    if isinstance(arg, float):
        return f"{arg:{align}{width},.2f}"
    return f"{str(arg):{align}{width}}"


def to_repr(something: Any, *, lang: str = "ru", fmt: bool = False) -> str:
    """Return ``repr`` or a human-friendly formatted representation."""
    if not fmt:
        return repr(something)
    if isinstance(something, bool):
        return yes_no(something, lang=lang)
    if isinstance(something, float):
        return fformat(something)
    return repr(something)


def yes_no(logical: Any = False, lang: str = "ru") -> str:
    """Convert a truthy value to a localized yes/no string."""
    yes_value, no_value = _LANG_YES_NO.get(lang, ("Yes", "No"))
    return yes_value if to_bool(logical) else no_value


def to_bool(value: Any = False) -> bool:
    """Convert common textual and scalar values to ``bool``."""
    if isinstance(value, str):
        stripped = value.strip().upper()
        return bool(stripped) and stripped not in FALSE_TABLE
    return bool(value)


def to_any(value: Any = None) -> Any:
    """Identity conversion helper."""
    return value


def to_str(value: Any = "") -> str:
    """Convert value to stripped string, keeping ``None`` as empty string."""
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def to_int(value: Any = 0) -> int:
    """Convert value to ``int`` with warning fallback to ``0``."""
    if isinstance(value, int):
        return value
    if value is None or str(value).strip() == "":
        return 0
    try:
        return int(value)
    except ValueError:
        wrn(
            f"{inspect_name()}|{inspect_upper_name()}: Could not convert {value!r} to int. Setting result to zero."
        )
        return 0


def to_float(value: Any = 0.0) -> float:
    """Convert value to ``float`` with warning fallback to ``0.0``."""
    if isinstance(value, float):
        return value
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(value)
    except ValueError:
        wrn(
            f"{inspect_name()}: Could not convert {value!r} to float. Setting result to zero."
        )
        return 0.0


def re_pattern(pattern_str: str, compiler: bool = True) -> str | re.Pattern[str]:
    """Expand custom placeholder tokens in a regex pattern."""
    for name, pattern in _PATTERN_PARTS_SORTED:
        pattern_str = pattern_str.replace(name, pattern)
    return re.compile(pattern_str) if compiler else pattern_str


def is_re_match_of_str(match_obj: re.Match[str] | None) -> bool:
    """Return ``True`` when match exists and every capturing group is a string."""
    return match_obj is not None and all(
        isinstance(group, str) for group in match_obj.groups()
    )


def is_iter_of_str(
    str_iter: Any,
    nostr: bool = False,
    nonempty: bool = False,
    allempty: bool = False,
) -> bool:
    """Check whether an object is an iterable of strings."""
    if isinstance(str_iter, GeneratorType):
        raise TypeError(
            "Objects of generator type are not supported here because they are single-use iterables."
        )
    if isinstance(str_iter, str):
        return not nostr
    if not isinstance(str_iter, Iterable):
        return False

    items = list(str_iter)
    if nonempty:
        return all(isinstance(item, str) and item for item in items)
    if allempty:
        return all(isinstance(item, str) for item in items) and all(
            not item for item in items
        )
    return all(isinstance(item, str) for item in items)


def repr_type(var: Any) -> str:
    """Return compact type information for diagnostics."""
    return f"type({var!r})={var.__class__.__name__}"


def add_str(
    abouts: str, adds: str, strips: bool = False, endstr: bool = False
) -> tuple[str, int]:
    """Append line to a string accumulator and return new text plus line width."""
    add = adds.strip() if strips else adds
    result = abouts + add + ("" if endstr else "\n")
    return result, len(add)


def check_func_signature(func: Any, *, nargs: int) -> bool:
    """Return whether ``func`` can be called with ``nargs`` positional arguments."""
    try:
        inspect.signature(func).bind(*([object()] * nargs))
        return True
    except (TypeError, ValueError):
        return False


def accepts_keyword(func: Any, keyword: str) -> bool:
    """Return whether ``func`` accepts the named keyword argument."""
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False

    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            return True
        if parameter.name == keyword and parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            return True
    return False


def get_func_signature(func: Any) -> str:
    """Return printable function signature."""
    sig = inspect.signature(func)
    return f"{func.__name__}{sig}"


def inspect_name() -> str:
    """Return caller function name."""
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        return "<unknown>()"
    return frame.f_back.f_code.co_name + "()"


def inspect_upper_name() -> str:
    """Return caller-of-caller function name."""
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None or frame.f_back.f_back is None:
        return "<unknown>()"
    return frame.f_back.f_back.f_code.co_name + "()"


def dbg(*string: Any, loc: bool = True, mark: str = "") -> None:
    """Print debug message with optional location marker."""
    loc_str = inspect_upper_name() if loc else ""
    mark_str = f"[{mark}] " if mark else ""
    fil_str = " -> " if (mark or loc) else ""
    print(f"#dbg: {mark_str}{loc_str}{fil_str}", *string)


def format_table_to_llist(
    table: TableData,
    *,
    col_indent: int = 0,
    cvt: CellConverter = str,
) -> list[list[str]]:
    """Render a table into a 2D list of padded strings."""
    col_widths = get_list_of_cols_width(table, cvt=cvt)
    table_of_str: list[list[str]] = []

    for row in table:
        formatted_row: list[str] = []
        for index, item in enumerate(row):
            formatted_row.append(f"{cvt(item):<{col_widths[index] + col_indent}}")
        table_of_str.append(formatted_row)

    return table_of_str


def format_table_to_str(
    table: TableData,
    *,
    col_indent: int = 2,
    indent: IndentSpec = 0,
    cvt: CellConverter = str,
    header: bool = False,
) -> str:
    """Render a table as multiline string."""
    if isinstance(indent, tuple):
        first_indent, rest_indent = indent
    else:
        first_indent = rest_indent = indent

    lines: list[str] = []
    for index, row in enumerate(
        format_table_to_llist(table, col_indent=col_indent, cvt=cvt)
    ):
        current_indent = first_indent if index == 0 else rest_indent
        line = " " * current_indent + "".join(row)
        lines.append(line)
        if index == 0 and header:
            lines.append(re.sub(r"\S", "-", line))

    return "" if not lines else "\n".join(lines) + "\n"


def get_list_of_cols_width(llist: TableData, *, cvt: CellConverter = str) -> list[int]:
    """Return maximum rendered width for each column."""
    if not llist:
        return []

    max_len = max(len(row) for row in llist)
    widths = [0] * max_len
    for row in llist:
        for index, item in enumerate(row):
            widths[index] = max(widths[index], len(cvt(item)))
    return widths


def wrn(*msg: Any) -> None:
    """Print warning when warnings are enabled."""
    if WARNINGS:
        print("#Warning:", *msg)


__all__ = [
    "FALSE_TABLE",
    "FFORMAT_ALIGN_LIST",
    "add_str",
    "accepts_keyword",
    "check_func_signature",
    "dbg",
    "fformat",
    "format_table_to_llist",
    "format_table_to_str",
    "get_func_signature",
    "get_list_of_cols_width",
    "inspect_name",
    "inspect_upper_name",
    "is_iter_of_str",
    "is_re_match_of_str",
    "re_pattern",
    "repr_type",
    "to_any",
    "to_bool",
    "to_float",
    "to_int",
    "to_repr",
    "to_str",
    "wrn",
    "yes_no",
]
