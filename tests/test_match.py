from dataclasses import FrozenInstanceError
from functools import reduce
from operator import mul

import pytest
from rapidfuzz import fuzz

from cmdfilter import (
    IS_ANY_BOOL_EQ,
    IS_ANY_FLOAT_GE,
    IS_ANY_FLOAT_LE,
    IS_ANY_STR_EQ,
    Selector,
    grade,
    layer,
    to_float,
    to_str,
)

BOXES = [
    {
        "title": "Mobi",
        "color": "white",
        "price": 3.0,
        "width": 20,
        "depth": 30,
        "height": 20,
        "stock": True,
        "transit": 0,
    },
    {
        "title": "Fore",
        "color": "white",
        "price": 4.0,
        "width": 25,
        "depth": 40,
        "height": 20,
        "stock": True,
        "transit": 0,
    },
    {
        "title": "Peer",
        "color": "yellow",
        "price": 5.0,
        "width": 30,
        "depth": 30,
        "height": 30,
        "stock": True,
        "transit": 0,
    },
    {
        "title": "Core",
        "color": "grey",
        "price": 6.0,
        "width": 30,
        "depth": 40,
        "height": 25,
        "stock": False,
        "transit": 1,
    },
    {
        "title": "Rift",
        "color": "yellow",
        "price": 7.0,
        "width": 35,
        "depth": 40,
        "height": 30,
        "stock": False,
        "transit": 1,
    },
    {
        "title": "Bulk",
        "color": "gray",
        "price": 8.0,
        "width": 30,
        "depth": 50,
        "height": 30,
        "stock": False,
        "transit": 0,
    },
    {
        "title": "Cube",
        "color": "white",
        "price": 9.0,
        "width": 40,
        "depth": 40,
        "height": 40,
        "stock": False,
        "transit": 1,
    },
]


def evaluator(key_data: tuple[str, ...], arg: str) -> float:
    joined_key_data = " ".join(part.lower() for part in key_data)
    return fuzz.ratio(joined_key_data, arg.lower().strip())


def matcher(eval_result: float, arg: str) -> bool:
    _ = arg
    return eval_result >= 80


@pytest.fixture()
def selector() -> Selector:
    is_volume_above = grade(
        type_method=to_float,
        eval_method=lambda value_tuple, arg: reduce(mul, value_tuple) / 1000,
        match_method=lambda volume, arg: volume >= arg,
        group_keys=True,
        cost=10,
    )
    is_similar_str = grade(
        type_method=to_str,
        eval_method=evaluator,
        match_method=matcher,
        group_keys=True,
        cost=50,
    )

    layers = [
        layer("by_text", is_similar_str, ("find", "f"), keys=("title", "color")),
        layer("by_title", IS_ANY_STR_EQ, "t", keys="title"),
        layer(
            "volume_above",
            is_volume_above,
            ("vol_above", "va"),
            keys=("width", "depth", "height"),
        ),
        layer("price_below", IS_ANY_FLOAT_LE, ("price_below", "pb"), keys="price"),
        layer("price_above", IS_ANY_FLOAT_GE, ("price_above", "pa"), keys="price"),
        layer(
            "availability", IS_ANY_BOOL_EQ, ("stock", "s"), keys=("stock", "transit")
        ),
    ]
    return Selector(layers)


def test_parse_and_match_backwards_compatible(selector: Selector) -> None:
    parsed = selector.parse("t:Core")

    assert parsed.unparsed == {}
    assert parsed.as_dict() == {(1, "by_title"): ("t", "Core")}
    assert selector.match_many(parsed, BOXES) == [(3, None)]


def test_invalid_keys_are_rejected() -> None:
    with pytest.raises(TypeError):
        layer("broken", IS_ANY_STR_EQ, "x", keys=[])


def test_invalid_match_signature_is_rejected() -> None:
    with pytest.raises(ValueError):
        grade(
            type_method=to_str,
            eval_method=lambda value, arg: value,
            match_method=lambda a, b, c: True,
            group_keys=False,
        )


def test_getitem_returns_immutable_layer(selector: Selector) -> None:
    copied_layer = selector[1]

    with pytest.raises(FrozenInstanceError):
        copied_layer.title = "mutated"


def test_parse_query_is_reentrant(selector: Selector) -> None:
    parsed = selector.parse_query("Rift yellow s:yes")
    assert parsed.unparsed == {}
    assert selector.match(parsed, BOXES[4]) == (True, 100.0)
    assert selector.match_many(parsed, BOXES) == [(4, 100.0)]


def test_parse_query_does_not_clobber_previous_state(selector: Selector) -> None:
    previous = selector.parse("t:Core")

    parsed = selector.parse_query("pb:6.5")

    assert previous.as_dict() == {(1, "by_title"): ("t", "Core")}
    assert parsed.as_dict() == {(3, "price_below"): ("pb", "6.5")}


def test_parse_collects_unparsed_options(selector: Selector) -> None:
    parsed = selector.parse("t:Core unknown:value")

    assert parsed.as_dict() == {(1, "by_title"): ("t", "Core")}
    assert parsed.unparsed == {"unknown": "value"}


def test_parse_keeps_implicit_text_before_first_option(selector: Selector) -> None:
    parsed = selector.parse("Rift yellow pb:7.5")

    assert parsed.as_dict() == {
        (0, "by_text"): ("find", "Rift yellow"),
        (3, "price_below"): ("pb", "7.5"),
    }
    assert parsed.unparsed == {}


def test_parse_last_duplicate_option_wins(selector: Selector) -> None:
    parsed = selector.parse("pb:8 pb:6.5")

    assert parsed.as_dict() == {(3, "price_below"): ("pb", "6.5")}


def test_parse_tracks_unknown_options_with_spaces(selector: Selector) -> None:
    parsed = selector.parse("t:Core unknown : spaced value")

    assert parsed.as_dict() == {(1, "by_title"): ("t", "Core")}
    assert parsed.unparsed == {"unknown": "spaced value"}


def test_parse_supports_inject(selector: Selector) -> None:
    parsed = selector.parse("t:Core", inject={"pb": 6.5})

    assert parsed.as_dict() == {
        (1, "by_title"): ("t", "Core"),
        (3, "price_below"): ("pb", 6.5),
    }
    assert selector.match_many(parsed, BOXES) == [(3, None)]


def test_parse_accepts_dict_command_and_tracks_unknown_keys(selector: Selector) -> None:
    parsed = selector.parse({"t": "Core", "pb": 6.5, "unknown": "leftover"})

    assert parsed.as_dict() == {
        (1, "by_title"): ("t", "Core"),
        (3, "price_below"): ("pb", 6.5),
    }
    assert parsed.unparsed == {"unknown": "leftover"}


def test_parse_builds_context_for_selected_layers() -> None:
    contextual_grade = grade(
        type_method=to_str,
        eval_method=lambda value, arg, *, context=None: (
            value if context is None or context.case else value.lower()
        ),
        match_method=lambda values, *, context=None: any(
            item == ("RIFT" if context and context.case else "rift") for item in values
        ),
        context="case",
    )
    contextual_selector = Selector(
        [layer("title", contextual_grade, ("title", "t"), keys="title")]
    )

    parsed = contextual_selector.parse("t:RIFT", context={"case": True})

    assert parsed.context is not None
    assert parsed.context.case is True
    assert contextual_selector.match(parsed, BOXES[4]) == (False, ("Rift",))


def test_parse_context_controls_match_behavior() -> None:
    contextual_grade = grade(
        type_method=to_str,
        eval_method=lambda value, arg, *, context=None: (
            value if context and context.case else value.lower()
        ),
        match_method=lambda values, *, context=None: any(
            item == ("RIFT" if context and context.case else "rift") for item in values
        ),
        context="case",
    )
    contextual_selector = Selector(
        [layer("title", contextual_grade, ("title", "t"), keys="title")]
    )
    parsed_case_off = contextual_selector.parse("t:RIFT", context={"case": False})
    parsed_case_on = contextual_selector.parse("t:RIFT", context={"case": True})

    assert contextual_selector.match(parsed_case_off, BOXES[4]) == (True, ("rift",))
    assert contextual_selector.match(parsed_case_on, BOXES[4]) == (False, ("Rift",))


def test_parse_reuses_context_type_for_same_field_set() -> None:
    contextual_grade = grade(
        type_method=to_str,
        eval_method=lambda value, arg, *, context=None: value,
        match_method=lambda values, *, context=None: any(values),
        context="case",
    )
    contextual_selector = Selector(
        [layer("title", contextual_grade, ("title", "t"), keys="title")]
    )

    parsed_one = contextual_selector.parse("t:RIFT", context={"case": False})
    parsed_two = contextual_selector.parse("t:Core", context={"case": True})

    assert parsed_one.context is not None
    assert parsed_two.context is not None
    assert parsed_one.context.__class__ is parsed_two.context.__class__


def test_match_rejects_runtime_context_override() -> None:
    contextual_grade = grade(
        type_method=to_str,
        eval_method=lambda value, arg, *, context=None: (
            value if context and context.case else value.lower()
        ),
        match_method=lambda values, *, context=None: any(
            item == ("RIFT" if context and context.case else "rift") for item in values
        ),
        context="case",
    )
    contextual_selector = Selector(
        [layer("title", contextual_grade, ("title", "t"), keys="title")]
    )
    parsed = contextual_selector.parse("t:RIFT", context={"case": False})

    with pytest.raises(TypeError):
        contextual_selector.match(parsed, BOXES[4], context={"case": True})


def test_arg_method_receives_context_during_parse() -> None:
    contextual_grade = grade(
        type_method=to_str,
        arg_method=lambda arg, *, context=None: (
            arg if context and context.case else arg.lower()
        ),
        eval_method=lambda value, arg: value.lower() == arg,
        match_method=any,
        context="case",
    )
    contextual_selector = Selector(
        [layer("title", contextual_grade, ("title", "t"), keys="title")]
    )

    parsed = contextual_selector.parse("t:RIFT", context={"case": False})

    assert parsed.parsed_layers[0].arg == "rift"
    assert parsed.context is not None
    assert parsed.context.case is False
    assert contextual_selector.match(parsed, BOXES[4]) == (True, (True,))


def test_arg_method_receives_context_for_implicit_layer() -> None:
    contextual_grade = grade(
        type_method=to_str,
        arg_method=lambda arg, *, context=None: (
            arg if context and context.keep_case else arg.lower()
        ),
        eval_method=lambda value, arg: value.lower() == arg,
        match_method=any,
        context="keep_case",
    )
    contextual_selector = Selector(
        [layer("title", contextual_grade, ("title", "t"), keys="title")]
    )

    parsed = contextual_selector.parse("RIFT", context={"keep_case": False})

    assert parsed.as_dict() == {(0, "title"): ("title", "RIFT")}
    assert parsed.parsed_layers[0].arg == "rift"
    assert parsed.context is not None
    assert parsed.context.keep_case is False
    assert contextual_selector.match(parsed, BOXES[4]) == (True, (True,))


def test_about_renders_help_lines(selector: Selector) -> None:
    described = Selector(
        [
            layer(
                "title",
                IS_ANY_STR_EQ,
                ("title", "t"),
                keys="title",
                about="Exact title match",
            ),
            layer(
                "stock",
                IS_ANY_BOOL_EQ,
                ("stock", "s"),
                keys=("stock", "transit"),
                about="Availability filter",
            ),
        ]
    )

    about_text = described.about()

    assert "[title|t]:<str> - Exact title match" in about_text
    assert "[stock|s]:<bool> - Availability filter" in about_text


def test_parse_precomputes_ordered_layers(selector: Selector) -> None:
    parsed = selector.parse("pb:6.5 t:Core")

    assert tuple(layer.title for layer in parsed.parsed_layers) == (
        "by_title",
        "price_below",
    )
    assert tuple(layer.title for layer in parsed.ordered_parsed_layers) == (
        "price_below",
        "by_title",
    )


def test_selector_rejects_duplicate_options() -> None:
    with pytest.raises(ValueError, match="duplicate option"):
        Selector(
            [
                layer("title", IS_ANY_STR_EQ, ("title", "t"), keys="title"),
                layer("alias", IS_ANY_STR_EQ, ("t", "alias"), keys="color"),
            ]
        )


def test_selector_rejects_duplicate_titles() -> None:
    with pytest.raises(ValueError, match="duplicate layer title"):
        Selector(
            [
                layer("title", IS_ANY_STR_EQ, ("title", "t"), keys="title"),
                layer("title", IS_ANY_STR_EQ, ("color", "c"), keys="color"),
            ]
        )


def test_selector_layer_lookup_helpers(selector: Selector) -> None:
    assert selector.layer_index_by_title("price_below") == 3
    assert selector.layer_title_by_index(3) == "price_below"
    assert selector.get_layer_index_by_options(("price_below", "pb")) == 3


def test_match_raises_on_missing_key_when_skip_key_err_is_false() -> None:
    strict_selector = Selector(
        [
            layer(
                "title",
                IS_ANY_STR_EQ,
                ("title", "t"),
                keys="missing",
                skip_key_err=False,
            )
        ]
    )
    parsed = strict_selector.parse("t:Rift")

    with pytest.raises(KeyError, match="failed to read value by key/index 'missing'"):
        strict_selector.match(parsed, BOXES[4])


def test_match_uses_type_default_when_skip_key_err_is_true() -> None:
    tolerant_selector = Selector(
        [
            layer(
                "title",
                IS_ANY_STR_EQ,
                ("title", "t"),
                keys="missing",
                skip_key_err=True,
            )
        ]
    )
    parsed = tolerant_selector.parse("t:Rift")

    assert tolerant_selector.match(parsed, BOXES[4]) == (False, (False,))
